import json
import re
import time
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from chatbot.models import PDFPageChunk, ReferencePDF
from chatbot.services.chat_cache_service import _cache_key
from chatbot.services.self_improving_service import evaluate_answer_quality
from chatbot.services.answer_synthesis_service import understand_query_for_retrieval
from chatbot.services.search_service import _tokenize


QUESTION_TEMPLATES = [
    "Define {concept} in Object Oriented Programming and explain why it matters.",
    "How does {concept} work with a practical classroom example?",
    "Differentiate {concept} from related OOP concepts with one example.",
]

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is", "it", "of", "on",
    "or", "that", "the", "to", "was", "what", "when", "where", "which", "with", "this", "these", "those", "their",
    "there", "than", "then", "into", "such", "about", "have", "has", "had", "will", "would", "can", "could", "should",
    "may", "might", "also", "using",
}


class Command(BaseCommand):
    help = "Run nightly-style evaluation for self-improving chatbot and generate JSON reports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit-concepts",
            type=int,
            default=8,
            help="Maximum number of syllabus concepts to evaluate.",
        )
        parser.add_argument(
            "--output",
            default=str(Path(settings.BASE_DIR) / "test_logs" / "nightly_pipeline_report.json"),
            help="Path to nightly evaluation report JSON.",
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
            raise CommandError("No approved syllabus reference PDF available for nightly evaluation.")

        chunks = list(
            PDFPageChunk.objects.filter(reference_pdf=approved_pdf)
            .order_by("page_number", "chunk_index")
        )
        if not chunks:
            raise CommandError("Approved syllabus PDF has no chunks. Reprocess the PDF first.")

        concepts = self._extract_syllabus_concepts(chunks, max_items=max(1, int(options["limit_concepts"])))
        if not concepts:
            raise CommandError("Could not derive concepts from syllabus chunks.")

        question_bank = self._build_question_bank(concepts)
        corpus_tokens = set(_tokenize("\n".join((chunk.text_content or "") for chunk in chunks)))

        evaluator = self._build_evaluation_user()
        client = Client()
        client.force_login(evaluator)

        tests = []
        previous_pull_flag = bool(getattr(settings, "SELF_IMPROVING_ALLOW_MODEL_PULL", False))
        try:
            settings.SELF_IMPROVING_ALLOW_MODEL_PULL = True
            for concept, question in question_bank:
                tests.append(
                    self._run_case(
                        client=client,
                        user=evaluator,
                        approved_pdf=approved_pdf,
                        question=question,
                        concept=concept,
                        corpus_tokens=corpus_tokens,
                    )
                )
        finally:
            settings.SELF_IMPROVING_ALLOW_MODEL_PULL = previous_pull_flag

        summary = self._build_summary(tests)
        recommendations = self._build_recommendations(summary)

        report = {
            "generated_at": timezone.now().isoformat(),
            "command": "python manage.py evaluate_self_improving_pipeline",
            "environment": {
                "debug": settings.DEBUG,
                "ollama_base_url": getattr(settings, "OLLAMA_BASE_URL", ""),
                "llm_model": getattr(settings, "CHATBOT_LLM_MODEL", ""),
                "allow_model_pull_during_eval": True,
            },
            "knowledge_base": {
                "reference_pdf_id": approved_pdf.id,
                "reference_pdf_title": approved_pdf.title,
                "subject_id": approved_pdf.subject_id,
                "subject_name": approved_pdf.subject.name,
                "chunk_count": len(chunks),
                "derived_concepts": concepts,
            },
            "tests": tests,
            "summary": summary,
            "recommendations": recommendations,
            "artifacts": {
                "self_improving_attempts": str(Path(settings.BASE_DIR) / "test_logs" / "self_improving_pipeline.json"),
                "nightly_report": str(Path(options["output"])),
            },
        }

        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Nightly report written to {output_path}"))
        self.stdout.write(
            " | ".join(
                [
                    f"Questions={summary['question_count']}",
                    f"Pass={summary['acceptable_answers']}",
                    f"Streaming={summary['streaming_passes']}",
                    f"AvgQuality={summary['average_quality_score']}",
                ]
            )
        )
        for test in tests:
            self.stdout.write(
                " | ".join(
                    [
                        f"question={test['concept']}",
                        f"generation_mode={test['generation']['generation_mode']}",
                        f"llm_model_used={test['generation'].get('llm_model_used') or 'N/A'}",
                        f"candidate_source={test['generation'].get('candidate_source', 'DB')}",
                        f"retrieved_chunk_count={test['generation'].get('retrieved_chunk_count', 0)}",
                        f"model_used={test['generation']['model_used']}",
                        f"context_chunk_count={test['generation']['context_chunk_count']}",
                        f"retry_count={test['generation']['retry_count']}",
                        f"final_quality_score={test['generation']['final_quality_score']}",
                    ]
                )
            )
        if recommendations:
            self.stdout.write("Recommendations:")
            for rec in recommendations:
                self.stdout.write(f"- {rec}")

    def _run_case(self, *, client, user, approved_pdf, question, concept, corpus_tokens):
        query_understanding = understand_query_for_retrieval(question, recent_queries=[])
        cache_key = _cache_key(
            "||".join([question, query_understanding.get("expanded_question") or ""]),
            subject_id=approved_pdf.subject_id,
            reference_pdf_id=approved_pdf.id,
            strict_mode=True,
        )
        cache.delete(cache_key)
        cache.delete(f"chatbot:rate:{user.id}")

        started = time.perf_counter()
        response = client.post(
            reverse("curriculum_chat_stream"),
            data={
                "question": question,
                "subject_id": str(approved_pdf.subject_id),
                "pdf_id": str(approved_pdf.id),
            },
        )

        events = []
        buffer = ""
        token_count = 0
        first_token_latency_ms = None
        for raw in response.streaming_content:
            chunk_text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            buffer += chunk_text
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                event = json.loads(line)
                events.append(event)
                if event.get("type") == "token":
                    token_count += 1
                    if first_token_latency_ms is None:
                        first_token_latency_ms = round((time.perf_counter() - started) * 1000, 2)

        total_latency_ms = round((time.perf_counter() - started) * 1000, 2)
        done_event = next((event for event in reversed(events) if event.get("type") == "done"), None)
        payload = done_event.get("payload") if done_event else {}

        retrieved_snippets = " ".join(
            preview.get("snippet", "") for preview in (payload.get("retrieval_previews") or [])
        )
        overlap = self._grounding_overlap(payload.get("answer") or payload.get("markdown") or "", retrieved_snippets, corpus_tokens)
        initial_quality = evaluate_answer_quality(question, payload, [])
        final_quality = payload.get("improvement_trace", {}).get("quality") or initial_quality
        final_model = payload.get("final_model") or payload.get("improvement_trace", {}).get("selected_model") or payload.get("generation_mode", "unknown")
        context_chunk_count = payload.get("context_chunk_count") or payload.get("improvement_trace", {}).get("context_chunk_count") or len(payload.get("retrieval_previews") or [])
        retry_count = payload.get("retry_count") if payload.get("retry_count") is not None else payload.get("improvement_trace", {}).get("retry_count", 0)
        final_quality_score = payload.get("final_quality_score") or final_quality.get("quality_score", 0)

        cache.delete(cache_key)
        cache.delete(f"chatbot:rate:{user.id}")

        return {
            "concept": concept,
            "question": question,
            "http_status": response.status_code,
            "latency_ms": total_latency_ms,
            "first_token_latency_ms": first_token_latency_ms,
            "streaming": {
                "token_event_count": token_count,
                "done_event_seen": done_event is not None,
                "schema_valid": self._schema_valid(payload),
            },
            "generation": {
                "generation_mode": payload.get("generation_mode", "unknown"),
                "final_model": final_model,
                "model_used": final_model,
                "llm_model_used": payload.get("llm_model_used"),
                "candidate_source": payload.get("candidate_source", "DB"),
                "retrieved_chunk_count": payload.get("retrieved_chunk_count", context_chunk_count),
                "context_chunk_count": context_chunk_count,
                "retry_count": retry_count,
                "final_quality_score": final_quality_score,
                "confidence_score": payload.get("confidence_score", 0.0),
                "insufficient_context": payload.get("insufficient_context", False),
            },
            "quality": {
                **final_quality,
                "grounding_overlap_from_payload": overlap,
            },
            "initial_quality": initial_quality,
            "improvement_trace": payload.get("improvement_trace", {}),
        }

    def _extract_syllabus_concepts(self, chunks, max_items):
        text = "\n".join((chunk.text_content or "") for chunk in chunks)
        candidate_phrases = re.findall(r"\b[A-Za-z][A-Za-z\- ]{2,30}\b", text)
        counter = Counter()
        protected = {"object oriented programming", "oop", "encapsulation", "inheritance", "polymorphism", "abstraction", "composition"}
        for phrase in candidate_phrases:
            normalized = " ".join(phrase.lower().split())
            tokens = [token for token in normalized.split() if token not in STOPWORDS and len(token) > 2]
            if not tokens:
                continue
            compact = " ".join(tokens[:3])
            if len(compact) < 4:
                continue
            if compact in protected:
                counter[compact] += 8
            elif len(tokens) == 1:
                counter[compact] += 1
            else:
                counter[compact] += 2

        if not counter:
            return []

        concepts = [concept for concept, _score in counter.most_common(max_items)]
        return concepts

    def _build_question_bank(self, concepts):
        questions = []
        for idx, concept in enumerate(concepts):
            template = QUESTION_TEMPLATES[idx % len(QUESTION_TEMPLATES)]
            question = template.format(concept=concept)
            questions.append((concept, question))
        return questions

    def _build_summary(self, tests):
        if not tests:
            return {
                "question_count": 0,
                "acceptable_answers": 0,
                "streaming_passes": 0,
                "average_quality_score": 0,
                "quality_failures": {},
                "model_usage": {},
            }

        quality_failures = Counter()
        model_usage = Counter()
        acceptable_answers = 0
        streaming_passes = 0
        total_quality = 0
        for result in tests:
            quality = result.get("quality", {})
            total_quality += quality.get("quality_score", 0)
            if quality.get("acceptable"):
                acceptable_answers += 1
            for issue in quality.get("issues", []):
                quality_failures[issue] += 1
            final_model = result.get("generation", {}).get("final_model") or "unknown"
            model_usage[final_model] += 1
            streaming_info = result.get("streaming", {})
            if streaming_info.get("token_event_count", 0) > 0 and streaming_info.get("done_event_seen") and streaming_info.get("schema_valid"):
                streaming_passes += 1

        return {
            "question_count": len(tests),
            "acceptable_answers": acceptable_answers,
            "streaming_passes": streaming_passes,
            "average_quality_score": round(total_quality / max(1, len(tests)), 2),
            "quality_failures": dict(quality_failures),
            "model_usage": dict(model_usage),
        }

    def _build_recommendations(self, summary):
        recommendations = []
        question_count = max(1, summary.get("question_count", 0))
        acceptable = summary.get("acceptable_answers", 0)
        if acceptable / question_count < 0.8:
            recommendations.append("Increase retry budget and keep context_chunk_count >= 8 for low-scoring questions.")
        failures = summary.get("quality_failures", {})
        if failures.get("missing_reference_pages", 0) > 0:
            recommendations.append("Force citation section completion in prompt expansion and maintain retrieval_previews in final payload.")
        if failures.get("reference_grounding_weak", 0) > 0 or failures.get("hallucination_risk_high", 0) > 0:
            recommendations.append("Prioritize semantic rerank strategy and reduce temperature for unstable answers.")
        if summary.get("streaming_passes", 0) < question_count:
            recommendations.append("Investigate streaming stability: ensure token events and done payload schema are emitted for every run.")
        return recommendations

    def _build_evaluation_user(self):
        user, _created = User.objects.get_or_create(
            email="self-improving-evaluator@example.com",
            defaults={"name": "Self Improving Evaluator", "role": User.Role.STUDENT},
        )
        user.role = User.Role.STUDENT
        user.name = user.name or "Self Improving Evaluator"
        user.is_active = True
        user.set_password("pass12345")
        user.save()
        return user

    def _schema_valid(self, payload):
        if not isinstance(payload, dict):
            return False
        required = ["markdown", "structured_response", "confidence_score", "generation_mode"]
        return all(key in payload for key in required)

    def _grounding_overlap(self, answer_text, snippets_text, corpus_tokens):
        answer_tokens = set(_tokenize(answer_text or ""))
        snippet_tokens = set(_tokenize(snippets_text or "")) or set(corpus_tokens)
        if not answer_tokens:
            return 0.0
        return round(len(answer_tokens & snippet_tokens) / max(1, len(answer_tokens)), 4)
