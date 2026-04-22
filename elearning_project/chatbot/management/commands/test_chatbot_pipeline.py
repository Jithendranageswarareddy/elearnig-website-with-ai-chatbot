import json
import re
import time
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from chatbot.models import ChatQuery, PDFPageChunk, ReferencePDF
from chatbot.services.answer_synthesis_service import _prepare_generation, understand_query_for_retrieval
from chatbot.services.chat_cache_service import _cache_key
from chatbot.services.search_service import _tokenize
from chatbot.views import _prepare_chat_query


QUESTION_BANK = [
    {"concept": "Object Oriented Programming", "question": "What is Object Oriented Programming"},
    {"concept": "objects and classes", "question": "What are objects and classes"},
    {"concept": "encapsulation", "question": "Explain encapsulation"},
    {"concept": "inheritance", "question": "Explain inheritance"},
    {"concept": "polymorphism", "question": "Explain polymorphism"},
    {"concept": "composition", "question": "What is composition in OOP"},
    {"concept": "benefits of OOP", "question": "What are benefits of OOP"},
    {"concept": "disadvantages of OOP", "question": "What are disadvantages of OOP"},
    {"concept": "abstract class", "question": "What is an abstract class"},
    {"concept": "design patterns", "question": "What are design patterns"},
]

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is",
    "it", "of", "on", "or", "that", "the", "to", "was", "what", "when", "where", "which", "with",
    "this", "these", "those", "their", "there", "than", "then", "into", "such", "about", "have",
    "has", "had", "will", "would", "can", "could", "should", "may", "might", "also", "using",
}

SECTION_LABEL_MAP = {
    "main answer": "main_answer",
    "key concepts": "key_concepts",
    "key points": "key_concepts",
    "example": "example",
    "references": "references",
    "concept links": "concept_links",
    "you may also ask": "follow_up_questions",
    "related diagram": "related_diagram",
}


class Command(BaseCommand):
    help = "Run end-to-end internal chatbot pipeline diagnostics against the live streaming endpoint."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(Path(settings.BASE_DIR) / "test_logs" / "chatbot_pipeline_tests.json"),
            help="Path to the JSON report file.",
        )

    def handle(self, *args, **options):
        approved_pdf = (
            ReferencePDF.objects.select_related("subject", "subject__semester")
            .filter(
                is_active=True,
                status=ReferencePDF.Status.APPROVED,
                is_syllabus_reference=True,
                subject__is_active=True,
                subject__semester__is_active=True,
            )
            .order_by("uploaded_at")
            .first()
        )
        if not approved_pdf:
            raise CommandError("No approved syllabus reference PDF is available for pipeline testing.")

        chunk_queryset = PDFPageChunk.objects.filter(reference_pdf=approved_pdf).order_by("page_number", "chunk_index")
        if not chunk_queryset.exists():
            raise CommandError("The approved syllabus PDF has no extracted chunks. Reprocess the PDF before running diagnostics.")

        corpus_text = "\n".join(chunk_queryset.values_list("text_content", flat=True))
        corpus_tokens = set(self._content_tokens(corpus_text))
        corpus_concepts = self._detect_present_concepts(corpus_text)
        evaluation_user = self._build_evaluation_user()
        client = Client()
        client.force_login(evaluation_user)
        request_factory = RequestFactory()

        report = {
            "generated_at": timezone.now().isoformat(),
            "command": "python manage.py test_chatbot_pipeline",
            "environment": {
                "debug": settings.DEBUG,
                "ollama_base_url": getattr(settings, "OLLAMA_BASE_URL", ""),
                "llm_model": getattr(settings, "CHATBOT_LLM_MODEL", ""),
            },
            "knowledge_base": {
                "reference_pdf_id": approved_pdf.id,
                "reference_pdf_title": approved_pdf.title,
                "subject_id": approved_pdf.subject_id,
                "subject_name": approved_pdf.subject.name,
                "chunk_count": chunk_queryset.count(),
                "detected_concepts": corpus_concepts,
            },
            "tests": [],
            "summary": {},
            "recommendations": [],
        }

        with transaction.atomic():
            created_user = evaluation_user.pk and not User.objects.filter(pk=evaluation_user.pk).exclude(email=evaluation_user.email).exists()
            for question_case in QUESTION_BANK:
                result = self._run_question_case(
                    client=client,
                    request_factory=request_factory,
                    user=evaluation_user,
                    approved_pdf=approved_pdf,
                    corpus_tokens=corpus_tokens,
                    corpus_concepts=corpus_concepts,
                    question_case=question_case,
                )
                report["tests"].append(result)

            transaction.set_rollback(True)

        report["summary"] = self._build_summary(report["tests"])
        report["recommendations"] = self._build_recommendations(report)

        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Chatbot pipeline diagnostic report written to {output_path}"))
        self.stdout.write(
            f"Questions: {report['summary']['question_count']} | "
            f"Answer pass: {report['summary']['answer_not_empty_passes']} | "
            f"Reference pass: {report['summary']['reference_passes']} | "
            f"Grounding pass: {report['summary']['grounding_passes']} | "
            f"Streaming pass: {report['summary']['streaming_passes']}"
        )
        for item in report["tests"]:
            self.stdout.write(
                f"question={item['question']} | "
                f"generation_mode={item['raw_payload'].get('generation_mode', 'unknown')} | "
                f"llm_model_used={item['raw_payload'].get('llm_model_used') or 'N/A'} | "
                f"candidate_source={item['raw_payload'].get('candidate_source', item['retrieval'].get('candidate_source', 'unknown'))} | "
                f"retrieved_chunk_count={item['raw_payload'].get('retrieved_chunk_count', item['retrieval'].get('retrieved_chunk_count', 0))}"
            )
        if report["recommendations"]:
            self.stdout.write("Recommendations:")
            for recommendation in report["recommendations"]:
                self.stdout.write(f"- {recommendation}")

    def _run_question_case(self, client, request_factory, user, approved_pdf, corpus_tokens, corpus_concepts, question_case):
        question = question_case["question"]
        fake_request = request_factory.post(reverse("curriculum_chat_stream"), data={
            "question": question,
            "subject_id": str(approved_pdf.subject_id),
            "pdf_id": str(approved_pdf.id),
        })
        fake_request.user = user

        recent_queries = list(
            ChatQuery.objects.filter(user=user).order_by("-created_at")[:3]
        )
        query_understanding = understand_query_for_retrieval(question, recent_queries=recent_queries)
        cache_question = "||".join([question, query_understanding["expanded_question"] or ""])
        response_cache_key = _cache_key(
            cache_question,
            subject_id=approved_pdf.subject_id,
            reference_pdf_id=approved_pdf.id,
            strict_mode=True,
        )
        cache.delete(response_cache_key)
        cache.delete(f"chatbot:rate:{user.id}")

        prepared = _prepare_chat_query(
            fake_request,
            question,
            subject_id=str(approved_pdf.subject_id),
            pdf_id=str(approved_pdf.id),
            strict_mode=True,
        )
        generation_prepared = None
        if prepared.get("status") == 200 and prepared.get("chunks"):
            generation_prepared = _prepare_generation(
                question,
                prepared["chunks"],
                recent_queries=prepared.get("recent_queries", []),
            )

        started_at = time.perf_counter()
        response = client.post(
            reverse("curriculum_chat_stream"),
            data={
                "question": question,
                "subject_id": str(approved_pdf.subject_id),
                "pdf_id": str(approved_pdf.id),
            },
        )

        events = []
        token_text = []
        first_token_latency_ms = None
        buffer = ""
        for raw_chunk in response.streaming_content:
            chunk_text = raw_chunk.decode("utf-8") if isinstance(raw_chunk, bytes) else str(raw_chunk)
            buffer += chunk_text
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                event = json.loads(line)
                events.append(event)
                if event.get("type") == "token":
                    token_text.append(event.get("token", ""))
                    if first_token_latency_ms is None:
                        first_token_latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

        total_latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        done_event = next((event for event in reversed(events) if event.get("type") == "done"), None)
        error_event = next((event for event in events if event.get("type") == "error"), None)
        final_payload = done_event.get("payload") if done_event else {}
        markdown = final_payload.get("markdown") or final_payload.get("answer") or "".join(token_text)
        parsed_sections = self._parse_markdown_sections(markdown)
        structured_items = final_payload.get("structured_response") or []
        first_item = structured_items[0] if structured_items else {}

        raw_retrieved_chunks = self._serialize_chunks(prepared.get("chunks", []))
        reranked_chunks = self._serialize_chunks(generation_prepared.get("chunks", []) if generation_prepared else [])
        validation = self._validate_response(
            question=question,
            approved_pdf=approved_pdf,
            corpus_tokens=corpus_tokens,
            corpus_concepts=corpus_concepts,
            raw_retrieved_chunks=raw_retrieved_chunks,
            reranked_chunks=reranked_chunks,
            final_payload=final_payload,
            parsed_sections=parsed_sections,
            token_text="".join(token_text),
        )

        cache.delete(response_cache_key)
        cache.delete(f"chatbot:rate:{user.id}")

        return {
            "question": question,
            "concept": question_case["concept"],
            "concept_present_in_pdf": question_case["concept"].lower() in corpus_concepts,
            "http_status": response.status_code,
            "latency_ms": total_latency_ms,
            "first_token_latency_ms": first_token_latency_ms,
            "streaming": {
                "token_event_count": sum(1 for event in events if event.get("type") == "token"),
                "thinking_event_seen": any(event.get("type") == "thinking" for event in events),
                "done_event_seen": done_event is not None,
                "error_event": error_event,
                "schema_valid": self._payload_schema_valid(final_payload),
            },
            "query_understanding": {
                "question_type": prepared.get("question_type"),
                "expanded_question": prepared.get("expanded_question"),
                "search_query": prepared.get("search_query"),
                "detected_concepts": prepared.get("detected_concepts", []),
            },
            "retrieval": {
                "candidate_source": self._candidate_source(raw_retrieved_chunks),
                "retrieved_chunks": raw_retrieved_chunks,
                "retrieved_chunk_count": len(raw_retrieved_chunks),
                "final_reranked_chunks": reranked_chunks,
                "retrieval_previews": final_payload.get("retrieval_previews", []),
            },
            "structured_output": {
                "main_answer": parsed_sections.get("main_answer") or first_item.get("detailed_explanation", ""),
                "key_concepts": self._as_list(parsed_sections.get("key_concepts")) or first_item.get("key_points", []),
                "example": parsed_sections.get("example") or first_item.get("example", ""),
                "references": self._extract_reference_labels(parsed_sections, final_payload, first_item),
                "concept_links": self._extract_concept_links(final_payload, first_item, parsed_sections),
                "follow_up_questions": self._extract_follow_up_questions(final_payload, parsed_sections),
            },
            "generated_answer": final_payload.get("answer") or markdown,
            "reference_pages": self._extract_reference_labels(parsed_sections, final_payload, first_item),
            "raw_payload": {
                "confidence_score": final_payload.get("confidence_score"),
                "confidence_label": final_payload.get("confidence_label"),
                "generation_mode": final_payload.get("generation_mode"),
                "llm_model_used": final_payload.get("llm_model_used"),
                "candidate_source": final_payload.get("candidate_source", self._candidate_source(raw_retrieved_chunks)),
                "retrieved_chunk_count": final_payload.get("retrieved_chunk_count", len(raw_retrieved_chunks)),
                "insufficient_context": final_payload.get("insufficient_context", False),
            },
            "validation": validation,
            "issues": validation["issues"],
            "suggested_improvements": validation["suggested_improvements"],
        }

    def _build_evaluation_user(self):
        user, _created = User.objects.get_or_create(
            email="pipeline-evaluator@example.com",
            defaults={
                "name": "Pipeline Evaluator",
                "role": User.Role.STUDENT,
            },
        )
        user.role = User.Role.STUDENT
        user.name = user.name or "Pipeline Evaluator"
        user.is_active = True
        user.set_password("pass12345")
        user.save()
        return user

    def _serialize_chunks(self, chunks):
        serialized = []
        for chunk in chunks:
            metadata = getattr(chunk, "retrieval_metadata", {}) or {}
            serialized.append(
                {
                    "chunk_id": chunk.id,
                    "pdf_id": chunk.reference_pdf_id,
                    "pdf_title": chunk.reference_pdf.title,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "candidate_source": metadata.get("candidate_source", "DB"),
                    "candidate_score": round(float(metadata.get("candidate_score", 0.0)), 6),
                    "final_score": round(float(metadata.get("final_score", 0.0)), 6),
                    "semantic_score": round(float(metadata.get("semantic_score", 0.0)), 6),
                    "insufficient_context": bool(metadata.get("insufficient_context", False)),
                    "snippet": self._trim(chunk.text_content, 240),
                }
            )
        return serialized

    def _candidate_source(self, serialized_chunks):
        if not serialized_chunks:
            return "DB"
        sources = [str(item.get("candidate_source") or "DB").upper() for item in serialized_chunks]
        if any(source == "FAISS" for source in sources):
            return "FAISS"
        return "DB"

    def _parse_markdown_sections(self, markdown):
        sections = {}
        current_key = None
        lines = []
        for raw_line in (markdown or "").splitlines():
            heading_match = re.match(r"^##\s+(.+?)\s*$", raw_line.strip())
            if heading_match:
                if current_key is not None:
                    sections[current_key] = "\n".join(lines).strip()
                label = heading_match.group(1).split("—", 1)[0].strip().lower()
                current_key = SECTION_LABEL_MAP.get(label, label.replace(" ", "_"))
                lines = []
                continue
            if current_key is not None:
                lines.append(raw_line)
        if current_key is not None:
            sections[current_key] = "\n".join(lines).strip()
        return sections

    def _extract_reference_labels(self, parsed_sections, final_payload, first_item):
        labels = [item.get("label") for item in final_payload.get("references", []) if item.get("label")]
        if not labels:
            labels = [item.get("label") for item in final_payload.get("reference_previews", []) if item.get("label")]
        if not labels:
            labels = [item.get("label") for item in first_item.get("reference_previews", []) if item.get("label")]
        if not labels and parsed_sections.get("references"):
            labels = [line.lstrip("- ").strip() for line in parsed_sections["references"].splitlines() if line.strip()]
        return labels

    def _extract_concept_links(self, final_payload, first_item, parsed_sections):
        links = final_payload.get("concept_links") or first_item.get("related_concept_links") or []
        if links:
            return links
        if parsed_sections.get("concept_links"):
            return [line.lstrip("- ").strip() for line in parsed_sections["concept_links"].splitlines() if line.strip()]
        return []

    def _extract_follow_up_questions(self, final_payload, parsed_sections):
        items = final_payload.get("follow_up_questions") or []
        if items:
            return items
        if parsed_sections.get("follow_up_questions"):
            return [line.lstrip("- ").strip() for line in parsed_sections["follow_up_questions"].splitlines() if line.strip()]
        return []

    def _payload_schema_valid(self, payload):
        required = {"answer", "references", "concept_links", "diagrams", "follow_up_questions"}
        return bool(payload) and required.issubset(payload.keys())

    def _validate_response(self, question, approved_pdf, corpus_tokens, corpus_concepts, raw_retrieved_chunks, reranked_chunks, final_payload, parsed_sections, token_text):
        answer = (final_payload.get("answer") or "").strip()
        answer_tokens = self._content_tokens(answer)
        reference_labels = self._extract_reference_labels(parsed_sections, final_payload, (final_payload.get("structured_response") or [{}])[0])
        retrieved_text = " ".join(item["snippet"] for item in reranked_chunks or raw_retrieved_chunks)
        retrieved_tokens = set(self._content_tokens(retrieved_text))
        grounding_overlap = len(set(answer_tokens) & retrieved_tokens) / max(len(set(answer_tokens)) or 1, 1)
        unknown_ratio = len([token for token in answer_tokens if token not in corpus_tokens]) / max(len(answer_tokens), 1)
        has_reference_page = any("page" in label.lower() for label in reference_labels)
        question_tokens = set(self._content_tokens(question))
        scope_tokens = question_tokens | set(corpus_concepts)
        topic_overlap = len(set(answer_tokens) & scope_tokens) / max(len(scope_tokens), 1)
        generation_mode = final_payload.get("generation_mode") or "unknown"

        issues = []
        improvements = []

        answer_not_empty = bool(answer)
        if not answer_not_empty:
            issues.append("Answer is empty.")
            improvements.append("Investigate generation failures or fallback path handling.")

        grounded_in_chunks = bool((reranked_chunks or raw_retrieved_chunks)) and grounding_overlap >= 0.08
        if not grounded_in_chunks:
            issues.append("Answer has weak lexical grounding against retrieved PDF chunks.")
            improvements.append("Improve query rewriting or chunk granularity to increase answer-context overlap.")

        if not has_reference_page:
            issues.append("Answer is missing at least one explicit reference page.")
            improvements.append("Strengthen reference retention in answer synthesis and postprocessing.")

        academic_topic_scope = topic_overlap >= 0.05 or any(concept in answer.lower() for concept in corpus_concepts)
        if not academic_topic_scope:
            issues.append("Answer appears weakly aligned with the academic topic scope of the syllabus PDF.")
            improvements.append("Refine question understanding and scope control for academic-only answers.")

        not_hallucinated = unknown_ratio <= 0.55 and grounded_in_chunks and has_reference_page
        if not not_hallucinated:
            issues.append("Hallucination risk detected from weak grounding or too many out-of-corpus terms.")
            improvements.append("Tighten the synthesis prompt to discourage unsupported external information.")

        if len(raw_retrieved_chunks) < 2 or any(item.get("insufficient_context") for item in raw_retrieved_chunks):
            issues.append("Weak retrieval signal detected.")
            improvements.append("Consider smaller chunk sizes or more overlap to improve retrieval recall.")

        if not final_payload.get("concept_links"):
            issues.append("Concept links are missing or sparse.")
            improvements.append("Improve concept extraction or sync concept graph after PDF ingestion.")

        if not (
            generation_mode in {"ollama", "llm_rewriter"}
            or generation_mode.startswith("self_improving:")
        ):
            issues.append(f"LLM generation was not used; mode was '{generation_mode}'.")
            improvements.append("Ensure Ollama is running and the configured model is available for full pipeline validation.")

        return {
            "answer_not_empty": answer_not_empty,
            "grounded_in_retrieved_pdf_chunks": grounded_in_chunks,
            "has_reference_page": has_reference_page,
            "academic_topic_scope": academic_topic_scope,
            "not_hallucinated": not_hallucinated,
            "grounding_overlap_ratio": round(grounding_overlap, 4),
            "out_of_corpus_token_ratio": round(unknown_ratio, 4),
            "issues": list(dict.fromkeys(issues)),
            "suggested_improvements": list(dict.fromkeys(improvements)),
        }

    def _build_summary(self, tests):
        return {
            "question_count": len(tests),
            "answer_not_empty_passes": sum(1 for test in tests if test["validation"]["answer_not_empty"]),
            "grounding_passes": sum(1 for test in tests if test["validation"]["grounded_in_retrieved_pdf_chunks"]),
            "reference_passes": sum(1 for test in tests if test["validation"]["has_reference_page"]),
            "scope_passes": sum(1 for test in tests if test["validation"]["academic_topic_scope"]),
            "hallucination_passes": sum(1 for test in tests if test["validation"]["not_hallucinated"]),
            "streaming_passes": sum(1 for test in tests if test["streaming"]["schema_valid"] and test["streaming"]["done_event_seen"] and test["streaming"]["token_event_count"] > 0),
            "average_latency_ms": round(sum(test["latency_ms"] for test in tests) / max(len(tests), 1), 2),
            "ollama_generation_count": sum(1 for test in tests if test["raw_payload"].get("generation_mode") == "ollama"),
            "llm_rewriter_generation_count": sum(1 for test in tests if test["raw_payload"].get("generation_mode") == "llm_rewriter"),
            "deterministic_generation_count": sum(1 for test in tests if test["raw_payload"].get("generation_mode") == "deterministic"),
            "faiss_retrieval_count": sum(1 for test in tests if test["raw_payload"].get("candidate_source", "") == "FAISS"),
        }

    def _build_recommendations(self, report):
        issue_counter = Counter()
        for test in report["tests"]:
            issue_counter.update(test["issues"])

        recommendations = []
        if issue_counter["Weak retrieval signal detected."] >= 2:
            recommendations.append("Weak retrieval appears in multiple questions. Reduce chunk size or increase chunk overlap to improve recall for concept-level prompts.")
        if issue_counter["Answer is missing at least one explicit reference page."] >= 2:
            recommendations.append("Reference pages are missing in several answers. Strengthen reference preservation in the final synthesis payload and markdown postprocessing.")
        if issue_counter["Concept links are missing or sparse."] >= 2:
            recommendations.append("Concept graph linking is sparse. Revisit concept extraction thresholds and ensure PDF chunk-to-concept sync stays dense enough for OOP topics.")
        if issue_counter["Answer has weak lexical grounding against retrieved PDF chunks."] >= 2:
            recommendations.append("Grounding is weak for several answers. Improve retrieval query rewriting and semantic reranking so returned chunks contain the exact concept wording from the question.")
        if issue_counter["Hallucination risk detected from weak grounding or too many out-of-corpus terms."] >= 1:
            recommendations.append("Tighten the answer synthesis prompt to prefer only cited syllabus facts and avoid unsupported external explanations.")
        if report["summary"].get("ollama_generation_count", 0) < report["summary"].get("question_count", 0):
            recommendations.append("Some runs did not use Ollama. Verify the local Ollama service and configured llama3 model so full LLM generation is exercised consistently.")
        if not recommendations:
            recommendations.append("The current pipeline is behaving consistently for the evaluated questions. Next improvements should focus on broader subject coverage and more diverse question families.")
        return recommendations

    def _detect_present_concepts(self, corpus_text):
        lowered = (corpus_text or "").lower()
        present = []
        for case in QUESTION_BANK:
            concept = case["concept"].lower()
            if concept in lowered or any(token in lowered for token in concept.split() if len(token) > 3):
                present.append(concept)
        return sorted(set(present))

    def _content_tokens(self, text):
        return [token for token in _tokenize(text or "") if token not in STOPWORDS and len(token) > 2]

    def _trim(self, text, limit):
        compact = " ".join((text or "").split())
        if len(compact) <= limit:
            return compact
        return compact[:limit].rsplit(" ", 1)[0] + "..."

    def _as_list(self, value):
        if isinstance(value, list):
            return value
        if not value:
            return []
        return [line.lstrip("- ").strip() for line in str(value).splitlines() if line.strip()]