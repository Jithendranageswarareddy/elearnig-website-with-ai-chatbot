import os
import json
import re
from pathlib import Path

import fitz
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Prefetch, Q
from django.http import (
    FileResponse,
    Http404,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseNotAllowed,
    JsonResponse,
    StreamingHttpResponse,
)
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.audit import log_system_event
from accounts.decorators import faculty_required, principal_required
from accounts.views import principal_dashboard_metrics
from courses.models import Lesson, Semester, Subject, Unit

from .models import ChatQuery, PDFPageChunk, ReferencePDF
from .services.answer_service import NO_RESULT_MESSAGE, generate_answer
from .services.chunk_service import create_chunks_for_pdf
from .services.embedding_service import get_embedding_backend_name
from .services.embedding_service import store_chunk_embeddings
from .services.faiss_service import upsert_index_for_chunk_ids
from .services.pdf_processor import process_pdf
from .services.search_service import search_chunks, search_related_lessons
from .utils.query_utils import normalize_query_for_search, normalize_scope, tokenize_text
from .tasks import CELERY_AVAILABLE, process_reference_pdf_task


ARCHITECTURE_DIAGRAM = "Text extraction -> chunking -> embeddings -> FAISS retrieval -> answer generation"


def detect_query_type(question):
    lowered = (question or "").lower()
    if any(token in lowered for token in ["example", "sample", "instance"]):
        return "example"
    if any(token in lowered for token in ["compare", "difference", "vs", "versus"]):
        return "comparison"
    if any(token in lowered for token in ["how to", "steps", "procedure", "perform"]):
        return "procedure"
    if any(token in lowered for token in ["what is", "define", "meaning"]):
        return "definition"
    return "explanation"


def is_chat_rate_limited(request):
    return False


def ndjson_line(payload):
    return json.dumps(payload, ensure_ascii=False) + "\n"


def markdown_chunks(markdown_text, chunk_size=44):
    text = markdown_text or ""
    for index in range(0, len(text), max(1, int(chunk_size))):
        yield text[index : index + max(1, int(chunk_size))]


def _format_chatbot_markdown(markdown_text):
    text = (markdown_text or "").strip()
    if not text:
        return text

    if text == NO_RESULT_MESSAGE:
        return text

    lowered = text.lower()
    if "## definition" in lowered and "## explanation" in lowered and "## example" in lowered:
        return text
    if "definition:" in lowered and "explanation:" in lowered and "example:" in lowered:
        return text

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    definition = sentences[0] if sentences else text
    explanation = " ".join(sentences[1:]) if len(sentences) > 1 else text

    example = sentences[2] if len(sentences) > 2 else "For example, this concept can be applied in a practical academic scenario."
    return (
        f"## Definition\n{definition}\n\n"
        f"## Explanation\n{explanation}\n\n"
        f"## Example\n{example}"
    )


def _chunk_reference_pdf_id(chunk):
    if isinstance(chunk, dict):
        return chunk.get("reference_pdf_id")
    return getattr(chunk, "reference_pdf_id", None)


def _result_reference_ids(chunks):
    unique_ids = []
    for chunk in chunks or []:
        reference_id = _chunk_reference_pdf_id(chunk)
        if reference_id is None or reference_id in unique_ids:
            continue
        unique_ids.append(reference_id)
    return unique_ids


def build_stream_done_payload(payload):
    return payload


def synthesize_answer(question, chunks, recent_queries=None, allow_fallback=True):
    return generate_answer(question, chunks)


def stream_synthesize_answer(question, chunks, recent_queries=None, allow_fallback=True):
    payload = synthesize_answer(
        question,
        chunks,
        recent_queries=recent_queries,
        allow_fallback=allow_fallback,
    )
    markdown = payload.get("markdown") or ""
    if markdown:
        yield markdown
    return payload


def set_reference_pdf_status(reference_pdf, status, *, is_syllabus_reference=None):
    reference_pdf.status = status
    if is_syllabus_reference is not None:
        reference_pdf.is_syllabus_reference = bool(is_syllabus_reference)
    reference_pdf.save(update_fields=["status", "is_syllabus_reference"] if is_syllabus_reference is not None else ["status"])


def delete_reference_pdf(reference_pdf):
    reference_pdf.delete()


def _post_process_pdf(reference_pdf, replace_existing=True):
    process_pdf(reference_pdf, replace_existing=replace_existing)
    chunks = create_chunks_for_pdf(reference_pdf, reference_pdf.extracted_text or "")
    stored = store_chunk_embeddings(chunks)
    upsert_index_for_chunk_ids([chunk.id for chunk in chunks])
    reference_pdf.chunk_count = len(chunks)
    reference_pdf.save(update_fields=["chunk_count"])
    return {"chunk_count": len(chunks), "stored_embeddings": stored}


def queue_reference_pdf_processing(reference_pdf, replace_existing=True):
    if CELERY_AVAILABLE:
        try:
            process_reference_pdf_task.delay(reference_pdf.id, replace_existing=replace_existing)
            return {"queued": True}
        except Exception as e:
            print("ERROR:", str(e))
            pass
    _post_process_pdf(reference_pdf, replace_existing=replace_existing)
    return {"queued": False}


def _visible_subjects_with_pdfs():
    approved_pdf_qs = ReferencePDF.objects.filter(
        is_active=True,
        status=ReferencePDF.Status.APPROVED,
        is_syllabus_reference=True,
    ).order_by("title")
    return Subject.objects.filter(
        is_active=True,
        semester__is_active=True,
    ).prefetch_related(
        Prefetch("reference_pdfs", queryset=approved_pdf_qs)
    )


def _user_can_manage_pdf(user, reference_pdf):
    return user.is_principal or reference_pdf.uploaded_by_id == user.id


def _user_can_view_pdf(user, reference_pdf):
    if user.is_principal:
        return True

    is_student_safe = (
        reference_pdf.is_active
        and reference_pdf.status == ReferencePDF.Status.APPROVED
        and reference_pdf.is_syllabus_reference
        and reference_pdf.subject.is_active
        and reference_pdf.subject.semester.is_active
    )
    if user.is_student:
        return is_student_safe

    return reference_pdf.uploaded_by_id == user.id or is_student_safe


def _resolve_subject_and_pdf(subject_id, pdf_id):
    selected_subject = None
    selected_pdf = None
    if subject_id:
        try:
            selected_subject = Subject.objects.get(
                id=int(subject_id),
                is_active=True,
                semester__is_active=True,
            )
        except (Subject.DoesNotExist, ValueError):
            selected_subject = None
    if pdf_id:
        try:
            selected_pdf = ReferencePDF.objects.filter(is_active=True).get(
                id=int(pdf_id),
                status=ReferencePDF.Status.APPROVED,
                is_syllabus_reference=True,
            )
        except (ReferencePDF.DoesNotExist, ValueError):
            selected_pdf = None
    return selected_subject, selected_pdf


def _resolve_lesson(lesson_id):
    if not lesson_id:
        return None
    try:
        return Lesson.objects.get(
            id=int(lesson_id),
            is_active=True,
            subject__is_active=True,
            subject__semester__is_active=True,
        )
    except (Lesson.DoesNotExist, ValueError):
        return None


def _resolve_unit(unit_id):
    if not unit_id:
        return None
    try:
        return Unit.objects.get(
            id=int(unit_id),
            is_active=True,
            subject__is_active=True,
            subject__semester__is_active=True,
        )
    except (Unit.DoesNotExist, ValueError):
        return None


def _related_lessons_payload(related_lessons):
    return [
        {
            "id": lesson.id,
            "title": lesson.title,
            "url": reverse("read_lesson", args=[lesson.id]),
        }
        for lesson in related_lessons
    ]


def _chat_title_from_question(question):
    words = [
        token
        for token in tokenize_text(question or "")
        if token not in {"what", "is", "are", "the", "explain", "define", "about"}
    ]
    chosen = words[:6] if words else tokenize_text(question or "")[:6]
    if not chosen:
        return "New Chat"
    return " ".join(word.capitalize() for word in chosen)


def _safe_positive_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_pdf_display_text(text):
    cleaned = str(text or "")
    cleaned = re.sub(r"(?i)lovely\s+professional\s+university", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*(?:page\s*\d+|p\.\s*\d+)\s*$", "", cleaned)
    cleaned = cleaned.replace("\uf06c", " ").replace("", " ")
    cleaned = re.sub(r"[^\S\r\n]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    lines = [line.strip() for line in cleaned.splitlines()]
    deduped = []
    seen = set()
    for line in lines:
        lowered = line.lower()
        if not line or lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(line)
    return "\n".join(deduped).strip()


def _clean_unit_content_text(text):
    cleaned = str(text or "")
    cleaned = re.sub(r"[^\S\r\n]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _deactivate_existing_duplicate_pdfs():
    seen_keys = set()
    duplicate_ids = []
    for pdf in ReferencePDF.objects.filter(is_active=True).order_by("-uploaded_at"):
        file_name = Path(getattr(pdf.file, "name", "")).name.lower().strip()
        if not file_name:
            continue
        key = (pdf.subject_id, file_name)
        if key in seen_keys:
            duplicate_ids.append(pdf.id)
        else:
            seen_keys.add(key)
    if not duplicate_ids:
        return 0
    return ReferencePDF.objects.filter(id__in=duplicate_ids, is_active=True).update(is_active=False)


def _recent_conversation_context(user, limit=3):
    if not user or not getattr(user, "is_authenticated", False):
        return []
    return list(
        ChatQuery.objects.filter(user=user)
        .order_by("-created_at")[:limit]
    )


def _build_chat_cache_key(prepared):
    question = (prepared.get("question") or "").strip().lower()
    scope = prepared.get("scope") or "global"
    subject_id = prepared.get("selected_subject").id if prepared.get("selected_subject") else ""
    unit_id = prepared.get("selected_unit").id if prepared.get("selected_unit") else ""
    lesson_id = prepared.get("selected_lesson").id if prepared.get("selected_lesson") else ""
    pdf_id = prepared.get("selected_pdf").id if prepared.get("selected_pdf") else ""
    return f"chat:response:v3:{scope}:{subject_id}:{unit_id}:{lesson_id}:{pdf_id}:{question}"


def _needs_history_context(question):
    lowered = str(question or "").strip().lower()
    compact = re.sub(r"\s+", " ", lowered)
    if not compact:
        return False
    cues = {
        "what about",
        "and advantages",
        "and disadvantages",
        "advantages",
        "disadvantages",
        "explain more",
        "tell more",
        "continue",
    }
    return compact in cues or any(compact.startswith(prefix) for prefix in cues)


def _prepare_chat_query(
    request,
    question,
    subject_id=None,
    pdf_id=None,
    lesson_id=None,
    unit_id=None,
    scope="global",
    strict_mode=True,
    regulation=None,
    branch=None,
    semester=None,
):
    normalized_question = (question or "").strip()
    requested_scope = normalize_scope(scope)
    selected_lesson = _resolve_lesson(lesson_id)
    selected_unit = _resolve_unit(unit_id)

    if not normalized_question:
        return {
            "status": 400,
            "question": "",
            "bot_response": "Please enter a question.",
            "strict_mode": True if request.user.is_student else bool(strict_mode),
            "selected_subject": None,
            "selected_pdf": None,
            "selected_lesson": None,
            "selected_unit": None,
            "scope": requested_scope,
            "query_type": detect_query_type(normalized_question),
            "cache_hit": False,
            "cached_payload": None,
            "chunks": [],
            "related_lessons": [],
            "search_query": "",
            "detected_concepts": [],
            "expanded_question": "",
            "question_type": "new question",
            "recent_queries": [],
        }

    recent_queries = _recent_conversation_context(request.user, limit=5)
    
    # Clean query for improved retrieval (remove stopwords, handle multi-question)
    cleaned_search_query = normalize_query_for_search(normalized_question)
    
    contextual_question = normalized_question
    if _needs_history_context(normalized_question) and recent_queries:
        parent_question = (recent_queries[0].question or "").strip()
        if parent_question:
            contextual_question = f"{parent_question}. Follow-up: {normalized_question}"

    query_understanding = {
        "search_query": cleaned_search_query,  # Use cleaned version for retrieval
        "expanded_question": contextual_question,
        "detected_concepts": [],
        "question_type": "new question",
    }

    cache_expanded_question = query_understanding["expanded_question"]
    if recent_queries:
        previous_question = (recent_queries[0].question or "").strip().lower()
        if previous_question == normalized_question.lower():
            cache_expanded_question = normalized_question

    strict_mode = True if request.user.is_student else bool(strict_mode)
    query_type = detect_query_type(normalized_question)
    selected_subject, selected_pdf = _resolve_subject_and_pdf(subject_id, pdf_id)

    effective_scope = requested_scope
    if requested_scope == "unit" and not selected_unit:
        effective_scope = "global"
    elif requested_scope == "lesson" and not selected_lesson:
        effective_scope = "global"
    elif requested_scope == "subject" and not selected_subject:
        effective_scope = "global"
    elif requested_scope == "pdf" and not selected_pdf:
        effective_scope = "global"

    if selected_lesson is not None and selected_unit is None and selected_lesson.unit_id:
        selected_unit = selected_lesson.unit

    if selected_lesson is not None and selected_subject is None:
        selected_subject = selected_lesson.subject

    if selected_unit is not None and selected_subject is None:
        selected_subject = selected_unit.subject

    if selected_pdf is not None and selected_pdf.lesson_id and getattr(selected_pdf.lesson, "unit_id", None):
        lesson_unit_id = selected_pdf.lesson.unit_id
        if selected_pdf.unit_id != lesson_unit_id:
            selected_pdf.unit_id = lesson_unit_id
            selected_pdf.save(update_fields=["unit"])

    if is_chat_rate_limited(request):
        bot_response = "Chat rate limit reached. Please wait a minute before sending another question."
        log_system_event(
            user=request.user,
            action_type="CHAT_QUERY",
            object_type="ChatQuery",
            metadata={
                "question": normalized_question[:250],
                "event": "rate_limited",
                "query_type": query_type,
            },
        )
        return {
            "status": 429,
            "question": normalized_question,
            "bot_response": bot_response,
            "strict_mode": strict_mode,
            "selected_subject": selected_subject,
            "selected_pdf": selected_pdf,
            "selected_lesson": selected_lesson,
            "selected_unit": selected_unit,
            "scope": effective_scope,
            "query_type": query_type,
            "cache_hit": False,
            "cached_payload": None,
            "chunks": [],
            "related_lessons": [],
            "search_query": query_understanding["search_query"],
            "detected_concepts": query_understanding["detected_concepts"],
        }

    chunks = []
    related_lessons = []
    unit_context_text = ""

    if effective_scope == "unit" and selected_unit and selected_unit.content:
        unit_context_text = _clean_unit_content_text(selected_unit.content)

    search_query = query_understanding["search_query"] or normalized_question
    if effective_scope == "pdf" and selected_pdf is not None:
        pdf_enrichment_tokens = [
            selected_pdf.title or "",
            getattr(getattr(selected_pdf, "subject", None), "name", "") or "",
            getattr(getattr(selected_pdf, "unit", None), "title", "") or "",
        ]
        search_query = " ".join(part for part in [search_query] + pdf_enrichment_tokens if part).strip()

    chunks = search_chunks(
        search_query,
        subject=selected_subject,
        reference_pdf=selected_pdf,
        scope=effective_scope,
        subject_id=(selected_subject.id if selected_subject else None),
        lesson_id=(selected_lesson.id if selected_lesson else None),
        unit_id=(selected_unit.id if selected_unit else None),
        regulation=regulation,
        branch=branch,
        semester=semester,
        limit=5,
    )

    if unit_context_text:
        unit_context_chunk = {
            "text_content": unit_context_text,
            "reference_pdf_id": None,
            "reference_pdf_title": f"Unit {selected_unit.unit_number}: {selected_unit.title}",
            "page_number": None,
            "chunk_index": -1,
            "retrieval_metadata": {
                "candidate_source": "UNIT_CONTENT",
                "score": 1.0,
                "final_score": 1.0,
                "semantic_score": 1.0,
                "keyword_score": 1.0,
            },
        }
        chunks = [unit_context_chunk] + list(chunks or [])

    if not chunks:
        related_lessons = search_related_lessons(normalized_question)

    return {
        "status": 200,
        "question": normalized_question,
        "strict_mode": strict_mode,
        "selected_subject": selected_subject,
        "selected_pdf": selected_pdf,
        "selected_lesson": selected_lesson,
        "selected_unit": selected_unit,
        "scope": effective_scope,
        "query_type": query_type,
        "cache_hit": False,
        "cached_payload": None,
        "chunks": chunks,
        "related_lessons": related_lessons,
        "search_query": search_query,
        "detected_concepts": query_understanding["detected_concepts"],
        "expanded_question": cache_expanded_question,
        "question_type": query_understanding["question_type"],
        "recent_queries": recent_queries,
    }


def _finalize_chat_query(
    request,
    prepared,
    *,
    bot_response,
    structured_response,
    related_concepts,
    result_reference_ids,
    extra_payload=None,
    related_lessons=None,
):
    related_lessons = prepared["related_lessons"] if related_lessons is None else related_lessons
    formatted_bot_response = _format_chatbot_markdown(bot_response)
    extra_payload = extra_payload or {}

    log_system_event(
        user=request.user,
        action_type="CHAT_QUERY",
        object_type="ChatQuery",
        metadata={
            "question": prepared["question"][:250],
            "expanded_question": (prepared["expanded_question"] or prepared["question"])[:250],
            "subject_id": prepared["selected_subject"].id if prepared["selected_subject"] else None,
            "reference_pdf_id": prepared["selected_pdf"].id if prepared["selected_pdf"] else None,
            "lesson_id": prepared["selected_lesson"].id if prepared.get("selected_lesson") else None,
            "unit_id": prepared["selected_unit"].id if prepared.get("selected_unit") else None,
            "scope": prepared.get("scope", "global"),
            "strict_mode": prepared["strict_mode"],
            "query_type": prepared["query_type"],
            "cache_hit": prepared["cache_hit"],
            "question_type": prepared.get("question_type", "new question"),
            "result_chunks": len(prepared["chunks"]),
        },
    )

    ChatQuery.objects.create(
        user=request.user,
        subject=prepared["selected_subject"],
        reference_pdf=prepared["selected_pdf"],
        question=prepared["question"][:500],
        normalized_question=" ".join(tokenize_text(prepared["question"]))[:500],
        strict_mode=prepared["strict_mode"],
        result_count=len(prepared["chunks"]),
        result_reference_ids=result_reference_ids,
        related_concepts=related_concepts,
        response_text=formatted_bot_response or "",
    )

    return {
        "status": 200,
        "question": prepared["question"],
        "bot_response": formatted_bot_response or "",
        "structured_response": structured_response,
        "related_lessons": _related_lessons_payload(related_lessons),
        "strict_mode": prepared["strict_mode"],
        "scope": prepared.get("scope", "global"),
        "subject_id": prepared["selected_subject"].id if prepared["selected_subject"] else None,
        "lesson_id": prepared["selected_lesson"].id if prepared.get("selected_lesson") else None,
        "unit_id": prepared["selected_unit"].id if prepared.get("selected_unit") else None,
        "pdf_id": prepared["selected_pdf"].id if prepared["selected_pdf"] else None,
        "related_concepts": related_concepts,
        "result_reference_ids": result_reference_ids,
        "timestamp": timezone.now().isoformat(),
        "search_query": prepared.get("search_query", prepared["question"]),
        "expanded_question": prepared.get("expanded_question", prepared["question"]),
        "question_type": prepared.get("question_type", "new question"),
        **extra_payload,
    }


def _run_chat_query(
    request,
    question,
    subject_id=None,
    pdf_id=None,
    lesson_id=None,
    unit_id=None,
    scope="global",
    strict_mode=True,
    regulation=None,
    branch=None,
    semester=None,
):
    normalized_question = (question or "").strip()
    normalized_scope = normalize_scope(scope)
    if not normalized_question:
        return {
            "status": 400,
            "question": "",
            "bot_response": "Please enter a question.",
            "structured_response": [],
            "related_lessons": [],
            "strict_mode": True if request.user.is_student else bool(strict_mode),
            "scope": normalized_scope,
            "subject_id": None,
            "lesson_id": None,
            "unit_id": None,
            "pdf_id": None,
            "related_concepts": [],
            "result_reference_ids": [],
        }

    prepared = _prepare_chat_query(
        request,
        question,
        subject_id=subject_id,
        pdf_id=pdf_id,
        lesson_id=lesson_id,
        unit_id=unit_id,
        scope=normalized_scope,
        strict_mode=strict_mode,
        regulation=regulation,
        branch=branch,
        semester=semester,
    )
    if prepared["status"] >= 400:
        return {
            "status": prepared["status"],
            "question": prepared["question"],
            "bot_response": prepared["bot_response"],
            "structured_response": [],
            "related_lessons": [],
            "strict_mode": prepared["strict_mode"],
            "scope": prepared.get("scope", normalized_scope),
            "subject_id": prepared["selected_subject"].id if prepared["selected_subject"] else None,
            "lesson_id": prepared["selected_lesson"].id if prepared.get("selected_lesson") else None,
            "unit_id": prepared["selected_unit"].id if prepared.get("selected_unit") else None,
            "pdf_id": prepared["selected_pdf"].id if prepared["selected_pdf"] else None,
            "related_concepts": [],
            "result_reference_ids": [],
        }

    try:
        cache_key = _build_chat_cache_key(prepared)
        cached_payload = cache.get(cache_key)
        if cached_payload:
            synthesized = dict(cached_payload)
            synthesized.setdefault("generation_mode", "cache_hit")
        else:
            synthesized = generate_answer(
                prepared.get("expanded_question") or prepared["question"],
                prepared.get("chunks", []),
                recent_questions=[item.question for item in prepared.get("recent_queries", []) if item.question],
            )
            cache.set(
                cache_key,
                synthesized,
                int(getattr(settings, "CHAT_RESPONSE_CACHE_TTL", 600) or 600),
            )
    except Exception as e:
        synthesized = {
            "markdown": NO_RESULT_MESSAGE,
            "structured_response": [],
            "related_concepts": [],
            "follow_up_suggestions": [],
            "retrieval_previews": [],
            "confidence_score": 0.2,
            "confidence_label": "Low",
            "generation_mode": "safe_fallback",
            "llm_model_used": None,
            "candidate_source": "FAISS/DB",
            "retrieved_chunk_count": len(prepared.get("chunks", [])),
            "final_model": "fallback",
            "improvement_trace": {},
            "related_concept_links": [],
            "reference_previews": [],
            "diagrams": [],
            "next_topics": [],
            "insufficient_context": True,
        }
    return _finalize_chat_query(
        request,
        prepared,
        bot_response=synthesized.get("markdown", ""),
        structured_response=synthesized.get("structured_response", []),
        related_concepts=synthesized.get("related_concepts", []),
        result_reference_ids=_result_reference_ids(prepared["chunks"]),
        extra_payload={
            "follow_up_suggestions": synthesized.get("follow_up_suggestions", []),
            "retrieval_previews": synthesized.get("retrieval_previews", []),
            "confidence_score": synthesized.get("confidence_score", 0.35),
            "confidence_label": synthesized.get("confidence_label", "Low"),
            "generation_mode": synthesized.get("generation_mode", "ollama"),
            "llm_model_used": synthesized.get("llm_model_used"),
            "candidate_source": synthesized.get("candidate_source", "DB"),
            "retrieved_chunk_count": synthesized.get("retrieved_chunk_count", 0),
            "final_model": synthesized.get("final_model", "unknown"),
            "improvement_trace": synthesized.get("improvement_trace", {}),
            "related_concept_links": synthesized.get("related_concept_links", []),
            "reference_previews": synthesized.get("reference_previews", []),
            "diagrams": synthesized.get("diagrams", []),
            "next_topics": synthesized.get("next_topics", []),
            "insufficient_context": synthesized.get("insufficient_context", False),
            "answer_from": synthesized.get("answer_from", "Not available"),
        },
        related_lessons=prepared["related_lessons"],
    )


def _stream_generated_chat_payload(request, prepared):
    try:
        generated_payload = generate_answer(
            prepared.get("expanded_question") or prepared["question"],
            prepared.get("chunks", []),
            recent_questions=[item.question for item in prepared.get("recent_queries", []) if item.question],
        )
        for token in markdown_chunks(generated_payload.get("markdown", "")):
            yield ndjson_line({"type": "token", "token": token})
    except Exception as e:
        print("ERROR:", str(e))
        fallback_payload = {
            "markdown": NO_RESULT_MESSAGE,
            "structured_response": [],
            "related_concepts": [],
            "follow_up_suggestions": [],
            "retrieval_previews": [],
            "confidence_score": 0.2,
            "confidence_label": "Low",
            "generation_mode": "fast_fallback",
            "llm_model_used": None,
            "candidate_source": "FAISS/DB",
            "retrieved_chunk_count": len(prepared.get("chunks", [])),
            "final_model": "fallback",
            "improvement_trace": {},
            "related_concept_links": [],
            "reference_previews": [],
            "diagrams": [],
            "next_topics": [],
            "insufficient_context": True,
        }
        for token in markdown_chunks(fallback_payload["markdown"]):
            yield ndjson_line({"type": "token", "token": token})
        generated_payload = fallback_payload

    return _finalize_chat_query(
        request,
        prepared,
        bot_response=generated_payload.get("markdown", ""),
        structured_response=generated_payload.get("structured_response", []),
        related_concepts=generated_payload.get("related_concepts", []),
        result_reference_ids=_result_reference_ids(prepared["chunks"]),
        extra_payload={
            "follow_up_suggestions": generated_payload.get("follow_up_suggestions", []),
            "retrieval_previews": generated_payload.get("retrieval_previews", []),
            "confidence_score": generated_payload.get("confidence_score", 0.35),
            "confidence_label": generated_payload.get("confidence_label", "Low"),
            "generation_mode": generated_payload.get("generation_mode", "deterministic"),
            "llm_model_used": generated_payload.get("llm_model_used"),
            "candidate_source": generated_payload.get("candidate_source", "DB"),
            "retrieved_chunk_count": generated_payload.get("retrieved_chunk_count", 0),
            "final_model": generated_payload.get("final_model", "unknown"),
            "improvement_trace": generated_payload.get("improvement_trace", {}),
            "related_concept_links": generated_payload.get("related_concept_links", []),
            "reference_previews": generated_payload.get("reference_previews", []),
            "diagrams": generated_payload.get("diagrams", []),
            "next_topics": generated_payload.get("next_topics", []),
            "insufficient_context": generated_payload.get("insufficient_context", False),
            "answer_from": generated_payload.get("answer_from", "Not available"),
        },
        related_lessons=prepared["related_lessons"],
    )


@login_required(login_url="user_login")
@require_POST
def curriculum_chat_stream(request):
    question = (request.POST.get("question") or "").strip()
    if not question:
        def _empty_stream_lines():
            payload = {
                "status": 400,
                "question": "",
                "bot_response": "Please enter a question.",
                "structured_response": [],
                "related_lessons": [],
                "strict_mode": True if request.user.is_student else request.POST.get("strict_mode") == "on",
                "subject_id": None,
                "pdf_id": None,
                "related_concepts": [],
                "result_reference_ids": [],
            }
            yield ndjson_line({"type": "error", "message": payload["bot_response"]})
            yield ndjson_line({"type": "done", "payload": build_stream_done_payload(payload)})

        response = StreamingHttpResponse(_empty_stream_lines(), content_type="application/x-ndjson")
        response["Cache-Control"] = "no-cache"
        return response

    scope = normalize_scope(request.GET.get("scope", "global"))
    regulation = request.POST.get("regulation") or request.GET.get("regulation")
    branch = request.POST.get("branch") or request.GET.get("branch")
    semester = request.POST.get("semester") or request.GET.get("semester")
    subject_id = request.POST.get("subject_id") or request.GET.get("subject_id")
    pdf_id = request.POST.get("pdf_id")
    lesson_id = request.POST.get("lesson_id") or request.GET.get("lesson_id")
    unit_id = request.POST.get("unit_id") or request.GET.get("unit_id")
    strict_mode = True if request.user.is_student else request.POST.get("strict_mode") == "on"

    prepared = _prepare_chat_query(
        request,
        question,
        scope=scope,
        subject_id=subject_id,
        pdf_id=pdf_id,
        lesson_id=lesson_id,
        unit_id=unit_id,
        strict_mode=strict_mode,
        regulation=regulation,
        branch=branch,
        semester=semester,
    )

    def _stream_lines():
        yield ndjson_line({"type": "thinking", "message": "AI is thinking..."})
        if prepared["status"] >= 400:
            payload = {
                "status": prepared["status"],
                "question": prepared["question"],
                "bot_response": prepared["bot_response"],
                "structured_response": [],
                "related_lessons": [],
                "strict_mode": prepared["strict_mode"],
                "scope": prepared.get("scope", scope),
                "subject_id": prepared["selected_subject"].id if prepared["selected_subject"] else None,
                "lesson_id": prepared["selected_lesson"].id if prepared.get("selected_lesson") else None,
                "unit_id": prepared["selected_unit"].id if prepared.get("selected_unit") else None,
                "pdf_id": prepared["selected_pdf"].id if prepared["selected_pdf"] else None,
                "related_concepts": [],
                "result_reference_ids": [],
            }
            yield ndjson_line({"type": "error", "message": prepared["bot_response"]})
            yield ndjson_line({"type": "done", "payload": build_stream_done_payload(payload)})
            return

        streamed_payload = yield from _stream_generated_chat_payload(request, prepared)
        yield ndjson_line({"type": "done", "payload": build_stream_done_payload({**streamed_payload, "markdown": streamed_payload["bot_response"]})})
        return

    response = StreamingHttpResponse(_stream_lines(), content_type="application/x-ndjson")
    response["Cache-Control"] = "no-cache"
    return response


@login_required(login_url="user_login")
def curriculum_chat_history(request):
    page = max(_safe_positive_int(request.GET.get("page"), 1), 1)
    page_size = _safe_positive_int(request.GET.get("page_size"), 20)
    page_size = min(max(page_size, 5), 50)

    query_set = ChatQuery.objects.filter(user=request.user).select_related("subject", "reference_pdf")
    paginator = Paginator(query_set, page_size)
    page_obj = paginator.get_page(page)

    items = []
    for chat_query in page_obj.object_list:
        items.append(
            {
                "thread_id": f"query-{chat_query.id}",
                "title": _chat_title_from_question(chat_query.question),
                "question": chat_query.question,
                "response_text": chat_query.response_text,
                "created_at": chat_query.created_at.isoformat(),
                "strict_mode": chat_query.strict_mode,
                "subject_id": chat_query.subject_id,
                "subject_name": chat_query.subject.name if chat_query.subject else "",
                "reference_pdf_id": chat_query.reference_pdf_id,
                "reference_pdf_title": chat_query.reference_pdf.title if chat_query.reference_pdf else "",
                "related_concepts": chat_query.related_concepts,
                "result_reference_ids": chat_query.result_reference_ids,
            }
        )

    return JsonResponse(
        {
            "items": items,
            "page": page_obj.number,
            "page_size": page_size,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
            "total_pages": paginator.num_pages,
            "total_items": paginator.count,
        }
    )


@login_required(login_url="user_login")
@require_http_methods(["DELETE"])
def delete_chat(request, chat_id):
    chat_query = ChatQuery.objects.filter(id=chat_id).first()
    if not chat_query:
        return JsonResponse({"success": False, "error": "Chat not found."}, status=404)
    if chat_query.user_id != request.user.id:
        return JsonResponse({"success": False, "error": "Not authorized."}, status=403)

    chat_query.delete()
    return JsonResponse({"success": True, "deleted_id": chat_id})


@login_required(login_url="user_login")
def curriculum_chat(request):
    bot_response = None
    structured_response = []
    related_lessons = []
    question = None
    response_status = 200
    demo_flow = []
    demo_mode = request.GET.get("demo") == "1"
    subjects = _visible_subjects_with_pdfs()
    semesters = Semester.objects.filter(is_active=True).order_by("number")
    lesson_catalog = list(
        Lesson.objects.filter(
            is_active=True,
            subject__is_active=True,
            subject__semester__is_active=True,
        )
        .select_related("subject")
        .order_by("subject__name", "order")
        .values("id", "title", "subject_id", "subject__name")
    )
    units = Unit.objects.filter(
        is_active=True,
        subject__is_active=True,
        subject__semester__is_active=True,
    ).select_related("subject").order_by("subject__name", "unit_number")
    pdf_options = ReferencePDF.objects.filter(
        is_active=True,
        status=ReferencePDF.Status.APPROVED,
        is_syllabus_reference=True,
        subject__is_active=True,
        subject__semester__is_active=True,
    ).select_related("subject").order_by("subject__name", "title")
    regulations = list(
        Semester.objects.filter(is_active=True)
        .values_list("regulation", flat=True)
        .distinct()
        .order_by("regulation")
    )
    branches = list(
        Subject.objects.filter(is_active=True, semester__is_active=True)
        .exclude(branch__isnull=True)
        .exclude(branch="")
        .values_list("branch", flat=True)
        .distinct()
        .order_by("branch")
    )
    strict_mode = request.user.is_student
    request_scope = normalize_scope(request.GET.get("scope", "global"))
    regulation = request.GET.get("regulation")
    branch = request.GET.get("branch")
    semester = request.GET.get("semester")

    if request.method == "POST":
        is_json_request = (request.content_type or "").startswith("application/json")
        json_payload = {}
        if is_json_request:
            try:
                json_payload = json.loads(request.body.decode("utf-8") or "{}")
            except Exception as e:
                print("ERROR:", str(e))
                return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        post_question = request.POST.get("question")
        if is_json_request:
            post_question = json_payload.get("question") or json_payload.get("message")

        post_subject_id = request.POST.get("subject_id")
        if is_json_request:
            post_subject_id = json_payload.get("subject_id")
        if not post_subject_id:
            post_subject_id = request.GET.get("subject_id")

        post_lesson_id = request.POST.get("lesson_id")
        if is_json_request:
            post_lesson_id = json_payload.get("lesson_id")
        if not post_lesson_id:
            post_lesson_id = request.GET.get("lesson_id")

        post_unit_id = request.POST.get("unit_id")
        if is_json_request:
            post_unit_id = json_payload.get("unit_id")
        if not post_unit_id:
            post_unit_id = request.GET.get("unit_id")

        if is_json_request:
            regulation = json_payload.get("regulation", regulation)
            branch = json_payload.get("branch", branch)
            semester = json_payload.get("semester", semester)
        else:
            regulation = request.POST.get("regulation") or regulation
            branch = request.POST.get("branch") or branch
            semester = request.POST.get("semester") or semester

        post_scope = request.GET.get("scope", request_scope)
        if is_json_request:
            post_scope = json_payload.get("scope", post_scope)
        post_scope = normalize_scope(post_scope)

        post_pdf_id = request.POST.get("pdf_id")
        if is_json_request:
            post_pdf_id = json_payload.get("pdf_id")

        strict_mode_flag = request.POST.get("strict_mode") == "on"
        if is_json_request:
            strict_mode_flag = bool(json_payload.get("strict_mode", strict_mode_flag))

        payload = _run_chat_query(
            request,
            post_question,
            scope=post_scope,
            subject_id=post_subject_id,
            pdf_id=post_pdf_id,
            lesson_id=post_lesson_id,
            unit_id=post_unit_id,
            strict_mode=strict_mode_flag,
            regulation=regulation,
            branch=branch,
            semester=semester,
        )

        if is_json_request:
            return JsonResponse(
                {
                    "markdown": payload.get("bot_response") or "",
                    "bot_response": payload.get("bot_response") or "",
                    "structured_response": payload.get("structured_response", []),
                    "related_lessons": payload.get("related_lessons", []),
                    "strict_mode": payload.get("strict_mode", strict_mode),
                    "scope": payload.get("scope", post_scope),
                    "question": payload.get("question"),
                },
                status=payload.get("status", 200),
            )

        question = payload.get("question")
        bot_response = payload.get("bot_response")
        structured_response = payload.get("structured_response", [])
        related_lessons = [
            Lesson(id=lesson["id"], title=lesson["title"]) for lesson in payload.get("related_lessons", [])
        ]
        strict_mode = payload.get("strict_mode", strict_mode)
        response_status = payload.get("status", 200)

    recent_queries = ChatQuery.objects.filter(user=request.user).order_by("-created_at")[:25]

    return render(
        request,
        "chat.html",
        {
            "bot_response": bot_response,
            "question": question,
            "subjects": subjects,
            "semesters": semesters,
            "lesson_catalog": lesson_catalog,
            "units": units,
            "pdf_options": pdf_options,
            "regulations": regulations,
            "branches": branches,
            "strict_mode": strict_mode,
            "strict_locked": request.user.is_student,
            "structured_response": structured_response,
            "related_lessons": related_lessons,
            "demo_flow": demo_flow,
            "demo_mode": demo_mode,
            "recent_queries": recent_queries,
        },
        status=response_status,
    )


@login_required(login_url="user_login")
@faculty_required
def upload_pdf(request):
    if not request.user.is_faculty_or_principal:
        return HttpResponseForbidden("Insufficient permissions.")

    subjects = Subject.objects.filter(is_active=True, semester__is_active=True).order_by(
        "semester__number", "name"
    )

    if request.method == "POST":
        _deactivate_existing_duplicate_pdfs()
        title = (request.POST.get("title") or "").strip()
        file = request.FILES.get("file")
        subject_id = request.POST.get("subject_id")
        if not all([title, file, subject_id]):
            messages.error(request, "Please provide title, subject, and PDF file.")
            return render(request, "upload_pdf.html", {"subjects": subjects})

        subject = get_object_or_404(Subject, id=subject_id, is_active=True, semester__is_active=True)

        incoming_file_name = Path(getattr(file, "name", "")).name.lower().strip()
        if incoming_file_name:
            duplicate_name = ReferencePDF.objects.filter(
                subject=subject,
                is_active=True,
                file__iendswith=f"/{incoming_file_name}",
            ).exists()
            if duplicate_name:
                messages.warning(request, "Duplicate PDF detected. Upload skipped.")
                return render(request, "upload_pdf.html", {"subjects": subjects})

        try:
            file.seek(0)
            preview_bytes = file.read()
            document = fitz.open(stream=preview_bytes, filetype="pdf")
            if document.page_count == 0:
                raise ValueError("The PDF has no readable pages.")
            document.close()
            file.seek(0)
        except Exception as e:
            print("ERROR:", str(e))
            messages.error(request, "PDF processing failed. Please upload a valid PDF file.")
            return render(request, "upload_pdf.html", {"subjects": subjects})

        try:
            pdf_instance = ReferencePDF.objects.create(
                uploaded_by=request.user,
                subject=subject,
                title=title,
                file=file,
                extracted_text="",
                status=ReferencePDF.Status.APPROVED,
                is_syllabus_reference=True,
            )
        except IntegrityError:
            messages.error(request, "A PDF with this title already exists for the selected subject.")
            return render(request, "upload_pdf.html", {"subjects": subjects})
        dispatch = queue_reference_pdf_processing(pdf_instance, replace_existing=True)
        pdf_instance.refresh_from_db()
        if dispatch["queued"]:
            messages.success(
                request,
                "PDF uploaded successfully, auto-approved, and queued for extraction.",
            )
        elif pdf_instance.processing_status == ReferencePDF.ProcessingStatus.FAILED:
            messages.warning(
                request,
                "PDF uploaded and approved, but extraction failed. You can reprocess it after checking OCR and embedding dependencies.",
            )
        else:
            messages.success(request, "PDF uploaded, auto-approved, and processed.")
        log_system_event(
            user=request.user,
            action_type="UPLOAD",
            object_type="ReferencePDF",
            object_id=pdf_instance.id,
            metadata={
                "subject_id": subject.id,
                "title": pdf_instance.title,
                "queued": dispatch["queued"],
            },
        )
        return redirect("pdf_list")

    return render(request, "upload_pdf.html", {"subjects": subjects})


@login_required(login_url="user_login")
@principal_required
@require_POST
def approve_pdf(request, pdf_id):
    if not request.user.is_principal:
        return HttpResponseForbidden("Insufficient permissions.")

    pdf = get_object_or_404(ReferencePDF, id=pdf_id)
    was_approved = pdf.status == ReferencePDF.Status.APPROVED
    pdf.is_active = True
    pdf.save(update_fields=["is_active"])
    set_reference_pdf_status(pdf, ReferencePDF.Status.APPROVED)
    if was_approved:
        messages.warning(request, "PDF was already approved.")
    else:
        messages.success(request, "PDF approved successfully.")
    log_system_event(
        user=request.user,
        action_type="APPROVE",
        object_type="ReferencePDF",
        object_id=pdf.id,
        metadata={"uploaded_by_id": pdf.uploaded_by_id, "subject_id": pdf.subject_id},
    )
    return redirect("pdf_list")


@login_required(login_url="user_login")
@principal_required
@require_POST
def hold_pdf(request, pdf_id):
    pdf = get_object_or_404(ReferencePDF, id=pdf_id)
    set_reference_pdf_status(pdf, ReferencePDF.Status.HOLD)
    messages.success(request, "PDF placed on hold.")
    log_system_event(
        user=request.user,
        action_type="APPROVE",
        object_type="ReferencePDF",
        object_id=pdf.id,
        metadata={"event": "hold_pdf", "uploaded_by_id": pdf.uploaded_by_id},
    )
    return redirect("pdf_list")


@login_required(login_url="user_login")
@principal_required
@require_POST
def reject_pdf(request, pdf_id):
    pdf = get_object_or_404(ReferencePDF, id=pdf_id)
    set_reference_pdf_status(pdf, ReferencePDF.Status.REJECTED)
    messages.success(request, "PDF rejected.")
    log_system_event(
        user=request.user,
        action_type="DELETE",
        object_type="ReferencePDF",
        object_id=pdf.id,
        metadata={"event": "reject_pdf", "uploaded_by_id": pdf.uploaded_by_id},
    )
    return redirect("pdf_list")


@login_required(login_url="user_login")
@principal_required
@require_POST
def toggle_pdf_reference(request, pdf_id):
    pdf = get_object_or_404(ReferencePDF, id=pdf_id)
    pdf.is_syllabus_reference = not pdf.is_syllabus_reference
    pdf.save(update_fields=["is_syllabus_reference"])
    messages.success(
        request,
        "Syllabus reference flag updated.",
    )
    log_system_event(
        user=request.user,
        action_type="APPROVE",
        object_type="ReferencePDF",
        object_id=pdf.id,
        metadata={"event": "toggle_syllabus_reference", "is_syllabus_reference": pdf.is_syllabus_reference},
    )
    return redirect("pdf_list")


@login_required(login_url="user_login")
@principal_required
@require_POST
def deactivate_pdf(request, pdf_id):
    pdf = get_object_or_404(ReferencePDF, id=pdf_id)
    pdf.is_active = False
    pdf.save(update_fields=["is_active"])
    messages.success(request, "PDF deactivated.")
    log_system_event(
        user=request.user,
        action_type="DELETE",
        object_type="ReferencePDF",
        object_id=pdf.id,
        metadata={"event": "deactivate_pdf"},
    )
    return redirect("pdf_list")


@login_required(login_url="user_login")
@faculty_required
@require_POST
def reprocess_pdf(request, pdf_id):
    pdf = get_object_or_404(ReferencePDF, id=pdf_id)
    if not _user_can_manage_pdf(request.user, pdf):
        return HttpResponseForbidden("Insufficient permissions.")

    dispatch = queue_reference_pdf_processing(pdf, replace_existing=True)
    pdf.refresh_from_db()

    if dispatch["queued"]:
        messages.success(request, "PDF reprocessing queued successfully.")
    elif pdf.processing_status == ReferencePDF.ProcessingStatus.READY:
        messages.success(request, "PDF reprocessed successfully.")
    else:
        messages.warning(request, "PDF reprocessed, but extraction is still incomplete.")
    log_system_event(
        user=request.user,
        action_type="UPLOAD",
        object_type="ReferencePDF",
        object_id=pdf.id,
        metadata={"event": "reprocess_pdf", "queued": dispatch["queued"]},
    )
    return redirect("pdf_list")


@login_required(login_url="user_login")
@faculty_required
def edit_pdf(request, pdf_id):
    pdf = get_object_or_404(
        ReferencePDF.objects.select_related("subject", "uploaded_by", "subject__semester"),
        id=pdf_id,
    )
    if not _user_can_manage_pdf(request.user, pdf):
        return HttpResponseForbidden("Insufficient permissions.")

    subjects = Subject.objects.filter(is_active=True, semester__is_active=True).order_by(
        "semester__number", "name"
    )
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        subject_id = request.POST.get("subject_id")
        if not title or not subject_id:
            messages.error(request, "Title and subject are required.")
            return render(request, "edit_pdf.html", {"pdf": pdf, "subjects": subjects})

        subject = get_object_or_404(
            Subject,
            id=subject_id,
            is_active=True,
            semester__is_active=True,
        )
        pdf.title = title
        pdf.subject = subject
        try:
            pdf.save(update_fields=["title", "subject"])
        except IntegrityError:
            messages.error(request, "A PDF with this title already exists for the selected subject.")
            return render(request, "edit_pdf.html", {"pdf": pdf, "subjects": subjects})

        messages.success(request, "PDF metadata updated successfully.")
        log_system_event(
            user=request.user,
            action_type="APPROVE",
            object_type="ReferencePDF",
            object_id=pdf.id,
            metadata={"event": "edit_pdf", "subject_id": subject.id},
        )
        return redirect("pdf_list")

    return render(request, "edit_pdf.html", {"pdf": pdf, "subjects": subjects})


@login_required(login_url="user_login")
@faculty_required
@require_POST
def delete_pdf(request, pdf_id):
    pdf = get_object_or_404(ReferencePDF.objects.select_related("uploaded_by"), id=pdf_id)
    if not _user_can_manage_pdf(request.user, pdf):
        return HttpResponseForbidden("Insufficient permissions.")

    title = pdf.title
    pdf_identifier = pdf.id
    delete_reference_pdf(pdf)
    messages.success(request, "PDF deleted successfully.")
    log_system_event(
        user=request.user,
        action_type="DELETE",
        object_type="ReferencePDF",
        object_id=pdf_identifier,
        metadata={"event": "delete_pdf", "title": title},
    )
    return redirect("pdf_list")


@login_required(login_url="user_login")
@faculty_required
def preview_pdf_chunks(request, pdf_id):
    pdf = get_object_or_404(
        ReferencePDF.objects.select_related("subject", "uploaded_by"),
        id=pdf_id,
    )
    if not _user_can_manage_pdf(request.user, pdf):
        return HttpResponseForbidden("Insufficient permissions.")

    chunks = PDFPageChunk.objects.filter(reference_pdf=pdf).order_by("page_number", "chunk_index")
    return render(
        request,
        "pdf_chunk_preview.html",
        {
            "pdf": pdf,
            "chunks": chunks,
        },
    )


@login_required(login_url="user_login")
def pdf_text_api(request, pdf_id):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    pdf = get_object_or_404(
        ReferencePDF.objects.select_related("subject", "subject__semester", "uploaded_by"),
        id=pdf_id,
    )
    if not _user_can_view_pdf(request.user, pdf):
        return HttpResponseForbidden("Insufficient permissions.")

    rows = list(
        PDFPageChunk.objects.filter(reference_pdf=pdf)
        .order_by("page_number", "chunk_index")
        .values("id", "page_number", "chunk_index", "text_content")[:80]
    )
    chunks = []
    for row in rows:
        cleaned = _clean_pdf_display_text(row.get("text_content", ""))
        if not cleaned:
            continue
        chunks.append(
            {
                "id": row["id"],
                "page_number": row["page_number"],
                "chunk_index": row["chunk_index"],
                "text": cleaned,
            }
        )

    merged_preview = "\n\n".join(chunk["text"] for chunk in chunks[:5]).strip()
    if not merged_preview:
        merged_preview = NO_RESULT_MESSAGE

    return JsonResponse(
        {
            "pdf_id": pdf.id,
            "title": pdf.title,
            "chunk_count": len(chunks),
            "preview": merged_preview,
            "chunks": chunks,
        }
    )


@login_required(login_url="user_login")
def pdf_list(request):
    qs = ReferencePDF.objects.select_related("subject", "subject__semester", "uploaded_by").filter(
        is_active=True,
        subject__is_active=True,
        subject__semester__is_active=True,
    )
    mine_only = request.GET.get("mine") == "1"
    semester_id = request.GET.get("semester")
    subject_id = request.GET.get("subject")
    q = request.GET.get("q")
    if semester_id:
        qs = qs.filter(subject__semester_id=semester_id)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)
    if q:
        qs = qs.filter(title__icontains=q)

    if request.user.is_student:
        qs = qs.filter(
            status=ReferencePDF.Status.APPROVED,
            is_syllabus_reference=True,
            subject__is_active=True,
            subject__semester__is_active=True,
        )
    elif request.user.is_faculty:
        if mine_only:
            qs = qs.filter(uploaded_by=request.user)
        else:
            qs = qs.filter(
                Q(uploaded_by=request.user, subject__is_active=True, subject__semester__is_active=True)
                | Q(
                    status=ReferencePDF.Status.APPROVED,
                    is_syllabus_reference=True,
                    subject__is_active=True,
                    subject__semester__is_active=True,
                )
            ).distinct()

    page_size = _safe_positive_int(request.GET.get("page_size"), 15)
    page_size = min(max(page_size, 5), 50)
    paginator = Paginator(qs.order_by("-uploaded_at"), page_size)
    page_obj = paginator.get_page(request.GET.get("page"))

    semesters = Semester.objects.filter(is_active=True)
    subjects = Subject.objects.filter(is_active=True, semester__is_active=True)
    response = render(
        request,
        "pdf_library.html",
        {
            "pdfs": page_obj,
            "semesters": semesters,
            "subjects": subjects,
            "mine_only": mine_only,
            "page_size": page_size,
        },
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@login_required(login_url="user_login")
@principal_required
def system_architecture(request):
    dashboard_metrics = principal_dashboard_metrics()
    report_path = Path(settings.BASE_DIR) / "reports" / "final_benchmark_report.md"
    report_excerpt = ""
    if report_path.exists():
        report_excerpt = report_path.read_text(encoding="utf-8")[:3200]

    runtime_cards = [
        {
            "label": "Embedding Backend",
            "value": get_embedding_backend_name(),
            "detail": "Semantic reranking backend used during hybrid retrieval.",
        },
        {
            "label": "Background Jobs",
            "value": "Celery Active" if CELERY_AVAILABLE else "Synchronous Fallback",
            "detail": "PDF ingestion uses Celery when the broker is available and falls back to in-process execution otherwise.",
        },
        {
            "label": "OCR Support",
            "value": "Disabled",
            "detail": "OCR pipeline removed in structure cleanup mode.",
        },
        {
            "label": "Cache Backend",
            "value": settings.CACHES["default"]["BACKEND"].rsplit(".", 1)[-1],
            "detail": "Query caching and chat response reuse layer.",
        },
    ]

    return render(
        request,
        "system_architecture.html",
        {
            "architecture_sections": [],
            "architecture_diagram": ARCHITECTURE_DIAGRAM,
            "runtime_cards": runtime_cards,
            "report_excerpt": report_excerpt,
            "dashboard_metrics": dashboard_metrics,
        },
    )


@login_required(login_url="user_login")
def serve_reference_pdf(request, pdf_id):
    reference_pdf = get_object_or_404(
        ReferencePDF.objects.select_related("subject", "subject__semester"),
        id=pdf_id,
    )
    if not reference_pdf.is_active:
        return HttpResponseNotFound()
    if not _user_can_view_pdf(request.user, reference_pdf):
        return HttpResponseForbidden("Insufficient permissions.")

    file_path = reference_pdf.file.path
    if not os.path.exists(file_path):
        raise Http404("PDF file not found.")

    response = FileResponse(open(file_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(file_path)}"'
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


