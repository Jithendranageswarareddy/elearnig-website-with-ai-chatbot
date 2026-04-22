import logging
import re
from difflib import SequenceMatcher

from django.db.models import Q

from courses.models import Lesson

from ..models import PDFPageChunk, ReferencePDF
from .embedding_service import cosine_similarity, embed_query, embedding_map_for_chunk_ids
from .faiss_service import search_index
from ..utils.query_utils import normalize_query_for_search, normalize_scope, query_terms, tokenize_text


logger = logging.getLogger(__name__)

# Retrieval tuning constants (behavior intentionally unchanged)
MAX_RESULTS = 5
MAX_DYNAMIC_TOP_K = 5
MIN_SCORE_THRESHOLD = 0.55
MAX_SCORE_THRESHOLD = 0.55
SEMANTIC_ONLY_THRESHOLD = 0.80  # Very high semantic score can bypass keyword requirement
NO_RESULT_MESSAGE = "This topic is not available in the selected syllabus."
MIN_OVERLAP_THRESHOLD = 0.08

SUBJECT_INTENT_MAP = {
    "process scheduling": "Operating Systems",
    "deadlock": "Operating Systems",
    "stack": "Data Structures",
    "queue": "Data Structures",
    "transport layer": "Computer Networks",
    "tcp": "Computer Networks",
    "udp": "Computer Networks",
    "cloud": "Cloud Computing",
    "machine learning": "Machine Learning",
    "encryption": "Cryptography",
    "network": "Computer Networks",
}

INTENT_MAP = {
    "oops": "object oriented programming",
    "oop": "object oriented programming",
    "os": "operating system",
    "ds": "data structures",
    "ml": "machine learning",
}

VERB_HINT_PATTERN = re.compile(
    r"(?i)\b("
    r"is|are|was|were|be|being|been|has|have|had|"
    r"do|does|did|can|could|will|would|shall|should|may|might|must|"
    r"allocate|allocates|allocated|allocating|"
    r"schedule|schedules|scheduled|scheduling|"
    r"manage|manages|managed|managing|"
    r"execute|executes|executed|executing|"
    r"process|processes|processed|processing|"
    r"run|runs|running|"
    r"determine|determines|determined|determining|"
    r"provide|provides|provided|providing|"
    r"use|uses|used|using|"
    r"perform|performs|performed|performing|"
    r"(?:[A-Za-z]{4,}(?:ed|ing))"
    r")\b"
)


def _looks_like_fragment(text):
    line = str(text or "").strip()
    if not line:
        return True
    if len(line.split()) < 5:
        return True
    if not VERB_HINT_PATTERN.search(line):
        return True
    return False


def _tokenize(text):
    return tokenize_text(text)


def _query_terms(text):
    return query_terms(text, max_terms=8)


def _normalize_intent_query(query):
    # Keep normalization lightweight and deterministic before retrieval.
    text = str(query or "")
    if not text.strip():
        return ""
    normalized = normalize_query_for_search(text)
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_scope(scope):
    return normalize_scope(scope)


def _word_boundary_match(term, text):
    """
    Match term as a whole word only (with word boundaries).
    Prevents "ipl" from matching "implementation"
    """
    pattern = r'\b' + re.escape(term) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _term_hits(terms, text):
    source = str(text or "")
    if not source:
        return 0
    return sum(1 for term in terms if _word_boundary_match(term, source))


def _token_jaccard_similarity(query, text):
    q_tokens = set(_tokenize(query))
    t_tokens = set(_tokenize(text))
    if not q_tokens or not t_tokens:
        return 0.0
    union = q_tokens | t_tokens
    if not union:
        return 0.0
    return float(len(q_tokens & t_tokens)) / float(len(union))


def _sequence_similarity(query, text):
    q = " ".join(str(query or "").lower().split())
    t = " ".join(str(text or "").lower().split())
    if not q or not t:
        return 0.0
    # Keep lightweight: compare against prefix window to avoid heavy CPU on huge chunks
    return float(SequenceMatcher(None, q[:500], t[:1000]).ratio())


def _semantic_similarity(query, text, embedding_semantic):
    token_sim = _token_jaccard_similarity(query, text)
    seq_sim = _sequence_similarity(query, text)
    # Lightweight hybrid semantic signal (embedding + lexical + sequence)
    return (
        (float(embedding_semantic) * 0.50)
        + (float(token_sim) * 0.30)
        + (float(seq_sim) * 0.20)
    )


def _normalize_subject_label(text):
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _predict_subject_for_query(query, rows, requested_subject_id=None):
    # Subject selection priority:
    # 1) explicit request id, 2) intent-map hints, 3) direct subject-name mention in query.
    query_l = str(query or "").lower()

    if requested_subject_id:
        for row in rows or []:
            if int(row.get("reference_pdf__subject_id") or 0) == int(requested_subject_id):
                return str(row.get("reference_pdf__subject__name") or "").strip() or None

    for key_phrase, subject_name in SUBJECT_INTENT_MAP.items():
        if key_phrase in query_l:
            return subject_name

    subject_names = []
    for row in rows or []:
        name = str(row.get("reference_pdf__subject__name") or "").strip()
        if name and name not in subject_names:
            subject_names.append(name)

    # direct subject-name mention in query
    for subject_name in subject_names:
        if _normalize_subject_label(subject_name) in query_l:
            return subject_name

    return None


def _clean_chunk_text_for_answer(text):
    raw = str(text or "").replace("\u00ad", "")
    raw = re.sub(r"(?i)^\s*[^.]{0,140}\s-\s[^.]{0,140}\.\s*", "", raw)
    raw = re.sub(r"(?i)\bis a syllabus concept in which\b", "is", raw)
    raw = re.sub(r"(?i)\bthis unit covers\b", "", raw)
    raw = re.sub(r"(?i)\bthis unit focuses on\b", "", raw)
    raw = re.sub(r"(?i)\bseed\s+content\b", "", raw)
    raw = re.sub(r"(?i)\bseed\s+minimal\s+content\b", "", raw)
    raw = re.sub(r"(?i)\bdetailed\s+explanation\b", "", raw)
    raw = re.sub(r"(?i)\bunit\s+content\s+dump\b", "", raw)
    raw = re.sub(r"-\s*\n\s*", "", raw)
    lines = [line.strip() for line in raw.splitlines()]
    cleaned_lines = []
    seen = set()
    for line in lines:
        if not line:
            continue
        # mandatory hard-clean: remove short/fragment lines
        if _looks_like_fragment(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        if any(token in key for token in ["seed minimal content", "detailed explanation", "unit content dump"]):
            continue
        seen.add(key)
        cleaned_lines.append(line)
    cleaned = " ".join(cleaned_lines) if cleaned_lines else " ".join(raw.split())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _overlap_ratio(terms, text):
    if not terms:
        return 0.0
    return float(_term_hits(terms, text)) / float(len(terms))


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
        semester_value = getattr(semester, "id", semester)
        semester_token = str(semester_value).strip()
        if semester_token.isdigit():
            semester_number_or_id = int(semester_token)
            qs = qs.filter(
                Q(reference_pdf__subject__semester_id=semester_number_or_id)
                | Q(reference_pdf__subject__semester__number=semester_number_or_id)
            )

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
            "reference_pdf__subject_id",
            "reference_pdf__subject__name",
            "reference_pdf__unit__title",
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
            "reference_pdf__subject_id",
            "reference_pdf__subject__name",
            "reference_pdf__unit__title",
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
    """Strict single-source retrieval with hard rejection for weak matches."""
    normalized_query = _normalize_intent_query(query)
    if not normalized_query.strip():
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
    faiss_rows = _faiss_rows(qs, normalized_query, top_k=10)
    candidate_rows = _candidate_rows(qs, normalized_query)
    rows = _union_rows(faiss_rows, candidate_rows)
    if not rows:
        logger.info(f"[SEARCH] Query='{query[:60]}' | Chunks=0 | Score=0.0 | Result=REJECTED (no candidates)")
        return []

    semantic_map = _semantic_scores(rows, normalized_query)
    normalized_scope = _normalize_scope(scope)
    requested_unit_id = int(unit_id) if str(unit_id or "").isdigit() else None
    requested_subject_id = int(subject_id) if str(subject_id or "").isdigit() else None
    predicted_subject = _predict_subject_for_query(normalized_query, rows, requested_subject_id=requested_subject_id)
    predicted_subject_l = _normalize_subject_label(predicted_subject)
    terms = _query_terms(normalized_query)

    if predicted_subject_l:
        rows = [
            row
            for row in rows
            if _normalize_subject_label(row.get("reference_pdf__subject__name") or "") == predicted_subject_l
        ]
        if not rows:
            logger.info(f"[SEARCH] Query='{normalized_query[:60]}' | Result=REJECTED (predicted subject filter removed all candidates)")
            return []

    ranked = []

    # HYBRID RANKING (required):
    # final_score = (0.5 * semantic_similarity)
    #             + (0.3 * keyword_match)
    #             + (0.2 * subject_unit_match)
    for row in rows:
        keyword_hits = int(row.get("keyword_score", 0.0) or 0.0)
        keyword_ratio = _overlap_ratio(terms, row.get("text_content", ""))
        unit_title = row.get("reference_pdf__unit__title") or ""
        subject_name = row.get("reference_pdf__subject__name") or ""
        subject_name_l = _normalize_subject_label(subject_name)
        unit_title_hits = _term_hits(terms, unit_title)
        subject_hits = _term_hits(terms, subject_name)

        unit_title_ratio = _overlap_ratio(terms, unit_title)
        subject_ratio = _overlap_ratio(terms, subject_name)
        embedding_semantic = float(semantic_map.get(row["id"], row.get("faiss_score", 0.0)))
        semantic_similarity = _semantic_similarity(normalized_query, row.get("text_content", ""), embedding_semantic)

        unit_boost = 0.0
        subject_boost = 0.0
        row_unit_id = row.get("reference_pdf__unit_id")
        row_subject_id = row.get("reference_pdf__subject_id")
        if normalized_scope == "unit" and requested_unit_id and row_unit_id == requested_unit_id:
            unit_boost = 0.08
        # Context-aware boosts even in global scope when request carries explicit IDs
        if requested_unit_id and row_unit_id == requested_unit_id:
            unit_boost = max(unit_boost, 0.18)
        if requested_subject_id and row_subject_id == requested_subject_id:
            subject_boost = 0.12

        subject_unit_match = min(1.0, ((unit_title_ratio + subject_ratio) * 0.5) + unit_boost + subject_boost)

        final_score = (
            (semantic_similarity * 0.50)
            + (keyword_ratio * 0.30)
            + (subject_unit_match * 0.20)
        )

        # Mandatory subject control: boost matched subject, penalize mismatched subject
        if predicted_subject_l:
            if subject_name_l == predicted_subject_l:
                final_score += 0.30
            else:
                final_score -= 0.40

        # Strict acceptance: require strong score and a meaningful syllabus signal
        is_acceptable = (
            final_score >= MIN_SCORE_THRESHOLD
            and (
                semantic_similarity >= SEMANTIC_ONLY_THRESHOLD
                or keyword_hits > 0
                or unit_title_hits > 0
                or subject_hits > 0
            )
        )
        if is_acceptable and requested_unit_id and requested_subject_id:
            is_acceptable = bool(row_unit_id == requested_unit_id or row_subject_id == requested_subject_id)
        elif is_acceptable and requested_unit_id:
            is_acceptable = bool(row_unit_id == requested_unit_id or semantic_similarity >= 0.35)
        elif is_acceptable and requested_subject_id:
            is_acceptable = bool(row_subject_id == requested_subject_id or semantic_similarity >= 0.35)
        if is_acceptable:
            ranked.append(
                (
                    int(row["id"]),
                    float(final_score),
                    float(keyword_ratio),
                    float(unit_title_ratio),
                    float(subject_ratio),
                    int(keyword_hits),
                    int(unit_title_hits),
                    int(subject_hits),
                    float(semantic_similarity),
                    float(final_score),
                    row.get("reference_pdf__subject__name") or "Unknown subject",
                    row.get("reference_pdf__unit__title") or "Unknown unit",
                )
            )

    if not ranked:
        logger.info(
            f"[SEARCH] Query='{query[:60]}' | Chunks={len(rows)} candidates | Result=REJECTED (no strong match)"
        )
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
                    "rejection_reason": "no_strong_match",
                },
            }
        ]

    max_score = max((item[1] for item in ranked), default=0.0)
    if max_score < MAX_SCORE_THRESHOLD:
        logger.info(
            f"[SEARCH] Query='{query[:60]}' | Chunks={len(rows)} candidates | MaxScore={max_score:.3f} | Result=REJECTED (below threshold)"
        )
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
                    "rejection_reason": "below_threshold",
                },
            }
        ]

    ranked.sort(
        key=lambda item: (
            -item[1],  # weighted_score
            -item[2],  # keyword_ratio
            -item[3],  # unit_title_ratio
            -item[4],  # subject_ratio
            -item[5],  # keyword_hits
            -item[6],  # unit_title_hits
            -item[7],  # subject_hits
            -item[8],  # semantic_score
            -item[9],  # confidence
            item[0],
        )
    )

    # Mandatory hard subject filter before final selection.
    ranked_for_select = ranked
    if predicted_subject_l:
        subject_locked = [item for item in ranked if _normalize_subject_label(item[10]) == predicted_subject_l]
        if subject_locked:
            ranked_for_select = subject_locked
        else:
            # Fallback to top semantic result if no predicted-subject candidate exists.
            ranked_for_select = [max(ranked, key=lambda item: (item[8], item[1]))]

    # FINAL precision mode: select only the single best chunk.
    selected_ranked = ranked_for_select[:1]

    # Strict rule: one subject per answer (no multi-subject mix)
    if selected_ranked:
        anchor_subject_l = _normalize_subject_label(selected_ranked[0][10])
        selected_ranked = [item for item in selected_ranked if _normalize_subject_label(item[10]) == anchor_subject_l]

    selected_ids = [item[0] for item in selected_ranked]
    chunk_map = {
        item.id: item
        for item in PDFPageChunk.objects.select_related(
            "reference_pdf",
            "reference_pdf__subject",
            "reference_pdf__unit",
        ).filter(id__in=selected_ids)
    }

    ordered = []

    def _candidate_viable(candidate):
        (
            candidate_chunk_id,
            candidate_score,
            candidate_keyword_ratio,
            candidate_unit_ratio,
            candidate_subject_ratio,
            candidate_keyword_hits,
            candidate_unit_hits,
            candidate_subject_hits,
            candidate_semantic_score,
            candidate_confidence,
            candidate_subject_name,
            candidate_unit_name,
        ) = candidate
        candidate_chunk = chunk_map.get(candidate_chunk_id)
        if not candidate_chunk:
            return None
        overlap = _overlap_ratio(terms, candidate_chunk.text_content)
        if overlap < MIN_OVERLAP_THRESHOLD:
            return None
        return (
            candidate_chunk,
            overlap,
            candidate_score,
            candidate_keyword_ratio,
            candidate_unit_ratio,
            candidate_subject_ratio,
            candidate_keyword_hits,
            candidate_unit_hits,
            candidate_subject_hits,
            candidate_semantic_score,
            candidate_confidence,
            candidate_subject_name,
            candidate_unit_name,
        )

    viable = []
    for candidate in selected_ranked:
        row = _candidate_viable(candidate)
        if row:
            viable.append(row)

    if not viable:
        logger.info(
            f"[SEARCH] Query='{query[:60]}' | Result=REJECTED (no viable candidate)"
        )
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
                    "rejection_reason": "low_overlap",
                },
            }
        ]

    viable.sort(key=lambda item: (-item[2], -item[1], -item[3], -item[4], -item[5]))
    best_chunk, best_overlap, best_confidence, best_keyword_ratio, best_unit_ratio, best_subject_ratio, best_keyword_hits, best_unit_hits, best_subject_hits, best_semantic_score, best_confidence_gate, best_subject_name, best_unit_name = viable[0]

    logger.debug(
        "[SEARCH_MATCH] question='%s' matched_subject='%s' matched_unit='%s' confidence=%.4f",
        query[:120],
        best_subject_name,
        best_unit_name,
        float(best_confidence),
    )

    ordered = []
    for chunk_data in viable[:1]:
        (
            candidate_chunk,
            candidate_overlap,
            candidate_confidence,
            candidate_keyword_ratio,
            candidate_unit_ratio,
            candidate_subject_ratio,
            candidate_keyword_hits,
            candidate_unit_hits,
            candidate_subject_hits,
            candidate_semantic_score,
            candidate_confidence_gate,
            candidate_subject_name,
            candidate_unit_name,
        ) = chunk_data

        candidate_chunk.text_content = _clean_chunk_text_for_answer(candidate_chunk.text_content)

        candidate_chunk.retrieval_metadata = {
            "candidate_source": "FAISS/DB",
            "score": float(candidate_confidence),
            "final_score": float(candidate_confidence),
            "semantic_score": float(candidate_semantic_score),
            "confidence_gate": float(candidate_confidence_gate),
            "keyword_score": float(candidate_keyword_hits),
            "keyword_overlap": float(candidate_keyword_ratio),
            "unit_title_match": float(candidate_unit_hits),
            "unit_overlap": float(candidate_unit_ratio),
            "subject_match": float(candidate_subject_hits),
            "subject_overlap": float(candidate_subject_ratio),
            "overlap": float(candidate_overlap),
            "subject_name": candidate_subject_name,
            "unit_title": candidate_unit_name,
            "reference_pdf_subject_name": candidate_subject_name,
            "reference_pdf_unit_title": candidate_unit_name,
            "reference_pdf_title": getattr(getattr(candidate_chunk, "reference_pdf", None), "title", "Unknown PDF"),
        }
        ordered.append(candidate_chunk)

    if semester and ordered:
        semester_value = getattr(semester, "id", semester)
        semester_token = str(semester_value).strip()
        if semester_token.isdigit():
            requested = int(semester_token)
            ordered = [
                chunk
                for chunk in ordered
                if (
                    getattr(chunk.reference_pdf, "subject", None)
                    and (
                        chunk.reference_pdf.subject.semester_id == requested
                        or getattr(chunk.reference_pdf.subject.semester, "number", None) == requested
                    )
                )
            ]

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

    logger.info(
        f"[SEARCH] Query='{query[:60]}' | Chunks={len(ordered)} | Score={best_confidence:.3f} | Result=ACCEPTED"
    )
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
