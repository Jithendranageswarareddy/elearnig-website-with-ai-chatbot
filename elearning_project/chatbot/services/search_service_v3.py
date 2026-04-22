import logging
import re

from django.db.models import Q

from courses.models import Lesson

from ..models import PDFPageChunk, ReferencePDF
from .embedding_service import cosine_similarity, embed_query, embedding_map_for_chunk_ids
from .faiss_service import search_index
from ..utils.query_utils import normalize_scope, query_terms, tokenize_text


logger = logging.getLogger(__name__)

MAX_RESULTS = 5
MAX_DYNAMIC_TOP_K = 5
MIN_SCORE_THRESHOLD = 0.4
MAX_SCORE_THRESHOLD = 0.55  # STRICT: Increased to 0.55
SEMANTIC_ONLY_THRESHOLD = 0.80  # Very high semantic score can bypass keyword requirement
NO_RESULT_MESSAGE = "No relevant content found in PDFs"


def _tokenize(text):
    return tokenize_text(text)


def _query_terms(text):
    return query_terms(text, max_terms=8)


def _normalize_scope(scope):
    return normalize_scope(scope)


def _word_boundary_match(term, text):
    """
    Match term as a whole word only (with word boundaries).
    Prevents "ipl" from matching "implementation"
    """
    pattern = r'\b' + re.escape(term) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _base_queryset(
    subject=None,
    reference_pdf=None,
    scope="global",
    subject_id=None,
    lesson_id=None,
    unit_id=None,
    regulation=None,
    branch=None,
    semester=None,
):
    qs = PDFPageChunk.objects.select_related("reference_pdf").filter(
        reference_pdf__is_active=True,
        reference_pdf__status=ReferencePDF.Status.APPROVED,
        reference_pdf__is_syllabus_reference=True,
        reference_pdf__subject__is_active=True,
        reference_pdf__subject__semester__is_active=True,
    )

    if regulation:
        qs = qs.filter(reference_pdf__subject__semester__regulation=regulation)

    if branch:
        qs = qs.filter(reference_pdf__subject__branch=branch)

    if semester:
        qs = qs.filter(reference_pdf__subject__semester_id=semester)

    normalized_scope = _normalize_scope(scope)
    scoped_subject_id = subject_id or (getattr(subject, "id", None) if subject is not None else None)

    if normalized_scope == "unit" and unit_id:
        qs = qs.filter(reference_pdf__unit_id=unit_id)
    elif normalized_scope == "lesson" and lesson_id:
        qs = qs.filter(reference_pdf__lesson_id=lesson_id)
    elif normalized_scope == "subject" and scoped_subject_id:
        qs = qs.filter(reference_pdf__subject_id=scoped_subject_id)
    elif reference_pdf is not None:
        qs = qs.filter(reference_pdf=reference_pdf)
    elif subject is not None:
        qs = qs.filter(reference_pdf__subject=subject)
    return qs


def _candidate_rows(qs, query):
    terms = _query_terms(query)
    if not terms:
        return []
    # Use substring matching for DB filtering (fast)
    term_filter = Q()
    for term in terms:
        term_filter |= Q(text_content__icontains=term)
    rows = list(
        qs.filter(term_filter).values(
            "id",
            "reference_pdf_id",
            "reference_pdf__unit_id",
            "page_number",
            "chunk_index",
            "text_content",
        )
    )
    # But use word-boundary matching for scoring (accurate)
    for row in rows:
        text = (row.get("text_content") or "").lower()
        # Count exact word matches only
        row["keyword_score"] = sum(1 for term in terms if _word_boundary_match(term, text))
    rows.sort(key=lambda item: (-item["keyword_score"], item["page_number"], item["chunk_index"], item["id"]))
    return rows


def _semantic_scores(rows, query):
    if not rows:
        return {}
    query_vector = embed_query(query)
    embedding_map = embedding_map_for_chunk_ids([row["id"] for row in rows])
    scored = {}
    for row in rows:
        vector = embedding_map.get(row["id"])
        if not vector:
            continue
        sim = cosine_similarity(query_vector, vector)
        scored[row["id"]] = max(0.0, (sim + 1.0) / 2.0)
    return scored


def _faiss_rows(qs, query, top_k=10):
    query_vector = embed_query(query)
    hits = search_index(query_vector, top_k=top_k)
    if not hits:
        return []
    score_map = {int(item["chunk_id"]): float(item["score"]) for item in hits}
    rows = list(
        qs.filter(id__in=list(score_map.keys())).values(
            "id",
            "reference_pdf_id",
            "reference_pdf__unit_id",
            "page_number",
            "chunk_index",
            "text_content",
        )
    )
    for row in rows:
        row["faiss_score"] = float(score_map.get(int(row["id"]), 0.0))
    rows.sort(key=lambda item: (-item.get("faiss_score", 0.0), item["page_number"], item["chunk_index"], item["id"]))
    return rows


def _union_rows(faiss_rows, candidate_rows):
    merged = {}
    for row in list(faiss_rows or []) + list(candidate_rows or []):
        chunk_id = int(row["id"])
        if chunk_id not in merged:
            merged[chunk_id] = dict(row)
            merged[chunk_id]["faiss_score"] = float(merged[chunk_id].get("faiss_score", 0.0) or 0.0)
            merged[chunk_id]["keyword_score"] = float(merged[chunk_id].get("keyword_score", 0.0) or 0.0)
            continue

        existing = merged[chunk_id]
        existing["faiss_score"] = max(float(existing.get("faiss_score", 0.0) or 0.0), float(row.get("faiss_score", 0.0) or 0.0))
        existing["keyword_score"] = max(float(existing.get("keyword_score", 0.0) or 0.0), float(row.get("keyword_score", 0.0) or 0.0))
        if not existing.get("text_content") and row.get("text_content"):
            existing["text_content"] = row.get("text_content")
    return list(merged.values())


def search_chunks(
    query,
    subject=None,
    reference_pdf=None,
    limit=MAX_RESULTS,
    scope="global",
    subject_id=None,
    lesson_id=None,
    unit_id=None,
    regulation=None,
    branch=None,
    semester=None,
):
    """
    Search for relevant PDF chunks with STRICT content relevance filtering.
    
    HALLUCINATION PREVENTION (v3):
    1. Uses word-boundary matching for keywords (no "ipl" matching "implementation")
    2. Requires combined semantic + keyword relevance
    3. Rejects if: final_score < 0.55 OR (no keywords AND semantic < 0.80)
    """
    if not (query or "").strip():
        return []

    qs = _base_queryset(
        subject=subject,
        reference_pdf=reference_pdf,
        scope=scope,
        subject_id=subject_id,
        lesson_id=lesson_id,
        unit_id=unit_id,
        regulation=regulation,
        branch=branch,
        semester=semester,
    )
    faiss_rows = _faiss_rows(qs, query, top_k=10)
    candidate_rows = _candidate_rows(qs, query)
    rows = _union_rows(faiss_rows, candidate_rows)
    if not rows:
        logger.info(f"[SEARCH] Query='{query[:60]}' | Chunks=0 | Score=0.0 | Result=REJECTED (no candidates)")
        return []

    semantic_map = _semantic_scores(rows, query)
    normalized_scope = _normalize_scope(scope)
    requested_unit_id = int(unit_id) if str(unit_id or "").isdigit() else None
    ranked = []
    best_keyword_row = None
    
    # Calculate scores for all rows with STRICT filtering
    for row in rows:
        keyword_score = float(row.get("keyword_score", 0.0))
        semantic_score = float(semantic_map.get(row["id"], row.get("faiss_score", 0.0)))
        
        unit_boost = 0.0
        row_unit_id = row.get("reference_pdf__unit_id")
        if normalized_scope == "unit" and requested_unit_id and row_unit_id == requested_unit_id:
            unit_boost = 0.08
        final_score = (semantic_score * 0.65) + (keyword_score * 0.35) + unit_boost
        
        # STRICT FILTERING: Require either:
        # - Final score >= 0.55, OR
        # - Semantic score >= 0.80 AND has at least one keyword match
        is_acceptable = (final_score >= MAX_SCORE_THRESHOLD) or (semantic_score >= SEMANTIC_ONLY_THRESHOLD and keyword_score > 0)
        
        if is_acceptable:
            if best_keyword_row is None or keyword_score > best_keyword_row[1]:
                best_keyword_row = (int(row["id"]), float(keyword_score), float(semantic_score), float(final_score))
            ranked.append((int(row["id"]), float(final_score), float(semantic_score), float(keyword_score)))

    # Calculate max score from ranked (acceptable) chunks
    max_score = max((item[1] for item in ranked), default=0.0)
    
    # CRITICAL CHECK: Reject if no acceptable chunks found
    if not ranked or max_score < MAX_SCORE_THRESHOLD:
        rejection_reason = ""
        if not ranked:
            rejection_reason = f"no chunks passed strict filters (word-boundary keywords)"
        else:
            rejection_reason = f"max_score {max_score:.3f} < threshold {MAX_SCORE_THRESHOLD}"
        
        logger.info(f"[SEARCH] Query='{query[:60]}' | Chunks={len(rows)} candidates, {len(ranked)} ranked | MaxScore={max_score:.3f} | Result=REJECTED ({rejection_reason})")
        return [
            {
                "text_content": NO_RESULT_MESSAGE,
                "reference_pdf_id": None,
                "page_number": None,
                "chunk_index": None,
                "retrieval_metadata": {
                    "candidate_source": "NONE",
                    "score": 0.0,
                    "empty_result": True,
                    "rejection_reason": rejection_reason,
                },
            }
        ]

    ranked.sort(key=lambda item: (-item[1], -item[2], -item[3], item[0]))
    dynamic_top_k = max(1, min(MAX_DYNAMIC_TOP_K, len(ranked)))
    top_window = ranked[:dynamic_top_k]
    top_has_keyword = any(item[3] > 0 for item in top_window)
    
    # Only inject fallback keywords if max_score is above threshold AND we have keyword coverage
    if (not top_has_keyword) and best_keyword_row and best_keyword_row[1] > 0 and max_score >= MAX_SCORE_THRESHOLD:
        inject_id = best_keyword_row[0]
        if not any(item[0] == inject_id for item in ranked):
            ranked.append((inject_id, best_keyword_row[3], best_keyword_row[2], best_keyword_row[1]))

    if not ranked:
        logger.info(f"[SEARCH] Query='{query[:60]}' | Chunks=0 | Score=0.0 | Result=REJECTED (no ranked chunks after filters)")
        return [
            {
                "text_content": NO_RESULT_MESSAGE,
                "reference_pdf_id": None,
                "page_number": None,
                "chunk_index": None,
                "retrieval_metadata": {
                    "candidate_source": "NONE",
                    "score": 0.0,
                    "empty_result": True,
                },
            }
        ]

    ranked.sort(key=lambda item: (-item[1], -item[2], -item[3], item[0]))
    dynamic_top_k = max(1, min(MAX_DYNAMIC_TOP_K, len(ranked)))
    ranked_by_id = {item[0]: (item[1], item[2], item[3]) for item in ranked}
    selected_ids = [item[0] for item in ranked]
    chunk_map = {
        item.id: item
        for item in PDFPageChunk.objects.select_related("reference_pdf").filter(id__in=selected_ids)
    }

    ordered = []
    seen_signatures = set()
    for chunk_id in selected_ids:
        chunk = chunk_map.get(chunk_id)
        if not chunk:
            continue
        signature = " ".join((chunk.text_content or "").lower().split()[:20])
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        final_score, semantic_score, keyword_score = ranked_by_id.get(chunk_id, (0.0, 0.0, 0.0))
        chunk.retrieval_metadata = {
            "candidate_source": "FAISS/DB",
            "score": float(final_score),
            "final_score": float(final_score),
            "semantic_score": float(semantic_score),
            "keyword_score": float(keyword_score),
        }
        ordered.append(chunk)
        if len(ordered) >= dynamic_top_k:
            break

    if not ordered:
        logger.info(f"[SEARCH] Query='{query[:60]}' | Chunks=0 | Score=0.0 | Result=REJECTED (no ordered chunks)")
        return [
            {
                "text_content": NO_RESULT_MESSAGE,
                "reference_pdf_id": None,
                "page_number": None,
                "chunk_index": None,
                "retrieval_metadata": {
                    "candidate_source": "NONE",
                    "score": 0.0,
                    "empty_result": True,
                },
            }
        ]

    # Log successful search
    logger.info(f"[SEARCH] Query='{query[:60]}' | Chunks={len(ordered)} | MaxScore={max_score:.3f} | Result=ACCEPTED")
    return ordered


def search_related_lessons(query, limit=3):
    terms = set(_query_terms(query))
    if not terms:
        return []

    term_filter = Q()
    for term in terms:
        term_filter |= (
            Q(title__icontains=term)
            | Q(content__icontains=term)
            | Q(subject__name__icontains=term)
        )

    qs = Lesson.objects.filter(
        is_active=True,
        subject__is_active=True,
        subject__semester__is_active=True,
    ).filter(term_filter).select_related("subject").distinct().order_by("id")

    return list(qs[: max(1, int(limit))])
