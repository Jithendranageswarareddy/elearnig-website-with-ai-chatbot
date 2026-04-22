import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django
from django.core.files import File
from django.test import Client


django.setup()

from django.contrib.auth import get_user_model

from chatbot.models import PDFPageChunk, ReferencePDF
from chatbot.services.chunk_service import create_chunks_for_pdf
from chatbot.services.embedding_service import store_chunk_embeddings
from chatbot.services.faiss_service import upsert_index_for_chunk_ids
from chatbot.services.pdf_processor import process_pdf
from courses.models import Lesson, Subject, Unit


STOPWORDS = {
    "what",
    "is",
    "are",
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "for",
    "with",
    "on",
    "by",
    "from",
    "as",
    "it",
    "its",
    "this",
    "that",
    "be",
    "vs",
    "versus",
    "why",
    "how",
    "where",
    "when",
    "define",
    "explain",
    "differentiate",
    "compare",
    "list",
    "into",
    "about",
    "using",
    "used",
    "their",
    "there",
    "than",
    "then",
    "also",
    "can",
    "could",
    "would",
    "should",
}

REJECT_MSG = "This topic is not available in the selected syllabus."
REPORTS_DIR = BASE_DIR / "reports"
GENERATED_QUESTIONS_PATH = REPORTS_DIR / "generated_10000_questions.json"
FINAL_VALIDATION_PATH = REPORTS_DIR / "final_10000q_validation.json"
KNOWLEDGE_MAP_PATH = REPORTS_DIR / "database_knowledge_map.json"
PDF_VALIDATION_PATH = REPORTS_DIR / "pdf_20q_validation.json"


EASY_TEMPLATES = {
    "definition": [
        "Define {topic}.",
        "What is {topic}?",
        "Give a short definition of {topic}.",
    ],
    "explanation": [
        "Explain {topic} in simple terms.",
        "Write a brief explanation of {topic}.",
    ],
    "comparison": [
        "Differentiate {topic} and {keyword2}.",
        "Compare {topic} with {keyword2}.",
    ],
    "process": [
        "Explain the process of {topic}.",
        "List the main steps involved in {topic}.",
    ],
    "advantages_disadvantages": [
        "State the advantages and disadvantages of {topic}.",
        "What are the merits and limitations of {topic}?",
    ],
    "algorithms": [
        "What is the algorithm behind {topic}?",
        "Describe the basic algorithmic idea of {topic}.",
    ],
    "conceptual": [
        "Explain the core concept of {topic}.",
        "Why is {topic} important in this unit?",
    ],
    "applications": [
        "Give one practical application of {topic}.",
        "Where is {topic} used in real systems?",
    ],
}

MEDIUM_TEMPLATES = {
    "definition": [
        "Define {topic} and mention its role in {unit_title}.",
        "How is {topic} defined in the context of {subject_name}?",
    ],
    "explanation": [
        "Explain {topic} with relevant details from {unit_title}.",
        "Describe how {topic} works with reference to {keyword1}.",
    ],
    "comparison": [
        "Compare {topic} and {keyword2} with suitable points.",
        "Differentiate {topic} versus {keyword2} with use-case context.",
    ],
    "process": [
        "Explain the step-by-step process of {topic} and its outcome.",
        "How does {topic} proceed from input to result?",
    ],
    "advantages_disadvantages": [
        "Discuss advantages and disadvantages of {topic} with examples.",
        "Evaluate benefits and drawbacks of {topic} in {subject_name}.",
    ],
    "algorithms": [
        "Explain the algorithmic flow of {topic} with key stages.",
        "How does {topic} optimize performance compared with {keyword2}?",
    ],
    "conceptual": [
        "Explain the conceptual relationship between {topic} and {keyword1}.",
        "What assumptions are involved in understanding {topic}?",
    ],
    "applications": [
        "Explain practical applications of {topic} in {subject_name}.",
        "How is {topic} applied in problem-solving scenarios?",
    ],
}

ADVANCED_TEMPLATES = {
    "definition": [
        "Formally define {topic} and relate it to {keyword1} and {keyword2}.",
        "Provide a rigorous definition of {topic} with constraints.",
    ],
    "explanation": [
        "Provide an in-depth explanation of {topic}, including edge cases.",
        "Explain {topic} with deeper reasoning and boundary conditions.",
    ],
    "comparison": [
        "Critically compare {topic} and {keyword2} in terms of complexity and applicability.",
        "Analyze trade-offs between {topic} and {keyword2} for advanced use.",
    ],
    "process": [
        "Explain the complete process of {topic} with intermediate states.",
        "Describe a full workflow for {topic} and discuss failure points.",
    ],
    "advantages_disadvantages": [
        "Critically analyze strengths and limitations of {topic} under varied conditions.",
        "Assess advantages and disadvantages of {topic} with technical justification.",
    ],
    "algorithms": [
        "Derive the algorithmic strategy for {topic} and discuss complexity implications.",
        "Explain advanced optimization techniques relevant to {topic}.",
    ],
    "conceptual": [
        "Discuss the theoretical foundations of {topic} and implications for {subject_name}.",
        "How does {topic} connect to higher-level principles in {unit_title}?",
    ],
    "applications": [
        "Evaluate real-world applications of {topic} and implementation challenges.",
        "How can {topic} be adapted for large-scale practical systems?",
    ],
}

QUESTION_TYPES = [
    "definition",
    "explanation",
    "comparison",
    "process",
    "advantages_disadvantages",
    "algorithms",
    "conceptual",
    "applications",
]


def tokenize(text):
    return [
        token
        for token in re.findall(r"[a-zA-Z]{3,}", str(text or "").lower())
        if token not in STOPWORDS
    ]


def normalized_name(name):
    return re.sub(r"\s+", " ", str(name or "").strip()).lower()


def sanitize_pdf_filename(name):
    base = re.sub(r"[^A-Za-z0-9]+", "_", str(name or "").strip())
    base = re.sub(r"_+", "_", base).strip("_")
    if not base:
        base = "Reference_PDF"
    return f"{base}.pdf"


def sentence_candidates(text, min_len=25, max_len=220):
    raw = re.split(r"(?<=[.!?])\s+", str(text or ""))
    results = []
    for sentence in raw:
        line = " ".join(sentence.split()).strip()
        if len(line) < min_len:
            continue
        if len(line) > max_len:
            line = line[:max_len].rsplit(" ", 1)[0].strip() + "..."
        results.append(line)
    return results


def top_keywords(text, limit=25):
    counts = Counter(tokenize(text))
    return [item for item, _ in counts.most_common(limit)]


def overlap_score(tokens_a, tokens_b):
    a = set(tokens_a or [])
    b = set(tokens_b or [])
    if not a:
        return 0.0
    return float(len(a & b)) / float(len(a))


def parse_stream_done(response):
    done = None
    err = None
    chunks = []
    for part in response.streaming_content:
        if isinstance(part, bytes):
            part = part.decode("utf-8", "ignore")
        chunks.append(part)
    for line in "".join(chunks).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except Exception as e:
            print("ERROR:", str(e))
            continue
        if evt.get("type") == "error":
            err = evt.get("message")
        if evt.get("type") == "done":
            done = evt.get("payload") or {}
    return done or {}, err


def build_database_knowledge_map():
    subjects = list(
        Subject.objects.filter(is_active=True, semester__is_active=True)
        .select_related("semester")
        .order_by("semester__number", "name")
    )
    units = list(
        Unit.objects.filter(is_active=True, subject__is_active=True, subject__semester__is_active=True)
        .select_related("subject")
        .order_by("subject__id", "unit_number")
    )
    lessons = list(
        Lesson.objects.filter(is_active=True, subject__is_active=True, subject__semester__is_active=True)
        .select_related("subject", "unit")
        .order_by("subject__id", "order")
    )
    pdfs = list(
        ReferencePDF.objects.filter(
            is_active=True,
            status=ReferencePDF.Status.APPROVED,
            is_syllabus_reference=True,
            subject__is_active=True,
            subject__semester__is_active=True,
        )
        .select_related("subject", "unit")
        .order_by("subject__id", "title")
    )
    chunks = list(
        PDFPageChunk.objects.filter(
            reference_pdf__is_active=True,
            reference_pdf__status=ReferencePDF.Status.APPROVED,
            reference_pdf__is_syllabus_reference=True,
            reference_pdf__subject__is_active=True,
            reference_pdf__subject__semester__is_active=True,
        )
        .select_related("reference_pdf", "reference_pdf__subject", "reference_pdf__unit")
        .order_by("reference_pdf_id", "page_number", "chunk_index")
    )

    lessons_by_unit = defaultdict(list)
    for lesson in lessons:
        key = lesson.unit_id or 0
        lessons_by_unit[key].append(lesson)

    chunks_by_unit = defaultdict(list)
    chunks_by_subject = defaultdict(list)
    for chunk in chunks:
        unit_id = getattr(chunk.reference_pdf, "unit_id", None) or 0
        subject_id = getattr(chunk.reference_pdf, "subject_id", None) or 0
        chunks_by_unit[unit_id].append(chunk)
        chunks_by_subject[subject_id].append(chunk)

    pdfs_by_subject = defaultdict(list)
    for pdf in pdfs:
        pdfs_by_subject[pdf.subject_id].append(pdf)

    map_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "counts": {
            "subjects": len(subjects),
            "units": len(units),
            "lessons": len(lessons),
            "reference_pdfs": len(pdfs),
            "pdf_chunks": len(chunks),
        },
        "subjects": [],
    }

    unit_profiles = {}

    for subject in subjects:
        subject_units = [unit for unit in units if unit.subject_id == subject.id]
        subject_chunks = chunks_by_subject.get(subject.id, [])
        subject_text_parts = [subject.name, subject.description]
        subject_topics = []
        subject_keywords = []

        subject_entry = {
            "subject_id": subject.id,
            "subject_code": subject.subject_code,
            "subject_name": subject.name,
            "semester": getattr(subject.semester, "number", None),
            "regulation": getattr(subject.semester, "regulation", None),
            "unit_count": len(subject_units),
            "pdf_count": len(pdfs_by_subject.get(subject.id, [])),
            "units": [],
        }

        for unit in subject_units:
            lesson_set = lessons_by_unit.get(unit.id, [])
            unit_chunks = chunks_by_unit.get(unit.id, [])
            if not unit_chunks:
                unit_chunks = [chunk for chunk in subject_chunks if chunk.reference_pdf.unit_id == unit.id]

            unit_text_parts = [unit.title, unit.content or ""]
            unit_text_parts.extend([lesson.title for lesson in lesson_set])
            unit_text_parts.extend([lesson.content for lesson in lesson_set])
            unit_text_parts.extend([chunk.text_content for chunk in unit_chunks])
            unit_text = "\n".join(part for part in unit_text_parts if part)

            keywords = top_keywords(unit_text, limit=30)
            topics = [line for line in sentence_candidates(unit_text, min_len=20, max_len=140)[:20]]
            definitions = [
                line
                for line in sentence_candidates(unit_text, min_len=30, max_len=180)
                if re.search(r"\b(is|are|defined as|refers to|means|consists of|process|steps?)\b", line, flags=re.IGNORECASE)
            ][:20]

            unit_entry = {
                "unit_id": unit.id,
                "unit_number": unit.unit_number,
                "unit_title": unit.title,
                "lesson_count": len(lesson_set),
                "chunk_count": len(unit_chunks),
                "topics": topics,
                "keywords": keywords,
                "definitions_concepts_processes": definitions,
            }
            subject_entry["units"].append(unit_entry)

            unit_profiles[unit.id] = {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "subject_code": subject.subject_code,
                "unit_id": unit.id,
                "unit_number": unit.unit_number,
                "unit_title": unit.title,
                "keywords": keywords,
                "topics": topics,
                "definitions": definitions,
                "pdf_ids": [pdf.id for pdf in pdfs_by_subject.get(subject.id, []) if pdf.unit_id in {None, unit.id}],
                "text_blob": unit_text,
            }

            subject_text_parts.append(unit_text)
            subject_topics.extend(topics[:4])
            subject_keywords.extend(keywords[:10])

        subject_text = "\n".join(part for part in subject_text_parts if part)
        subject_entry["topics"] = list(dict.fromkeys(subject_topics))[:30]
        subject_entry["keywords"] = list(dict.fromkeys(subject_keywords or top_keywords(subject_text, limit=30)))[:30]
        map_payload["subjects"].append(subject_entry)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_MAP_PATH.write_text(json.dumps(map_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "subjects": subjects,
        "units": units,
        "lessons": lessons,
        "pdfs": pdfs,
        "chunks": chunks,
        "unit_profiles": unit_profiles,
        "knowledge_map": map_payload,
    }


def choose_topic(profile, rng):
    candidates = profile.get("topics") or profile.get("definitions") or []
    if not candidates:
        candidates = [profile.get("unit_title") or profile.get("subject_name") or "concept"]
    text = rng.choice(candidates)
    text = re.sub(r"\s+", " ", str(text).strip())
    if len(text) > 110:
        text = text[:110].rsplit(" ", 1)[0]
    return text.strip(" .")


def choose_keywords(profile, rng):
    keywords = profile.get("keywords") or tokenize(profile.get("unit_title") + " " + profile.get("subject_name"))
    if not keywords:
        keywords = ["concept", "process", "application"]
    if len(keywords) == 1:
        return keywords[0], keywords[0]
    first = rng.choice(keywords)
    second = rng.choice([item for item in keywords if item != first] or keywords)
    return first, second


def difficulty_bucket(index, total):
    easy_limit = int(total * 0.40)
    medium_limit = int(total * 0.80)
    if index < easy_limit:
        return "easy"
    if index < medium_limit:
        return "medium"
    return "advanced"


def render_question(template, profile, qtype, rng):
    topic = choose_topic(profile, rng)
    keyword1, keyword2 = choose_keywords(profile, rng)
    return template.format(
        topic=topic,
        keyword1=keyword1,
        keyword2=keyword2,
        unit_title=profile.get("unit_title") or "this unit",
        subject_name=profile.get("subject_name") or "this subject",
    ).strip()


def generate_questions(unit_profiles, total_questions=10000, seed=42):
    if not unit_profiles:
        raise RuntimeError("Cannot generate questions: no active units found in database.")

    rng = random.Random(seed)
    profiles = list(unit_profiles.values())
    profiles.sort(key=lambda item: (item["subject_id"], item["unit_number"], item["unit_id"]))

    per_unit = total_questions // len(profiles)
    remainder = total_questions % len(profiles)

    generated = []
    seen = set()

    template_map = {
        "easy": EASY_TEMPLATES,
        "medium": MEDIUM_TEMPLATES,
        "advanced": ADVANCED_TEMPLATES,
    }

    difficulty_counts = Counter()
    type_counts = Counter()

    global_index = 0
    for idx, profile in enumerate(profiles):
        target = per_unit + (1 if idx < remainder else 0)
        for local_index in range(target):
            difficulty = difficulty_bucket(global_index, total_questions)
            qtype = QUESTION_TYPES[(global_index + local_index) % len(QUESTION_TYPES)]
            templates = template_map[difficulty][qtype]

            attempts = 0
            question_text = ""
            while attempts < 8:
                template = templates[(global_index + attempts) % len(templates)]
                candidate = render_question(template, profile, qtype, rng)
                key = normalized_name(candidate)
                if key and key not in seen:
                    seen.add(key)
                    question_text = candidate
                    break
                attempts += 1

            if not question_text:
                question_text = f"Explain {profile.get('unit_title')} with reference to {profile.get('subject_name')} ({global_index + 1})."
                seen.add(normalized_name(question_text))

            expected_pdf_id = profile.get("pdf_ids", [None])[0] if profile.get("pdf_ids") else None

            record = {
                "id": global_index + 1,
                "question": question_text,
                "difficulty": difficulty,
                "question_type": qtype,
                "subject_id": profile["subject_id"],
                "subject_name": profile["subject_name"],
                "unit_id": profile["unit_id"],
                "unit_number": profile["unit_number"],
                "unit_title": profile["unit_title"],
                "pdf_id": expected_pdf_id,
            }
            generated.append(record)
            difficulty_counts[difficulty] += 1
            type_counts[qtype] += 1
            global_index += 1

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_questions": len(generated),
        "distribution": {
            "difficulty": dict(difficulty_counts),
            "question_types": dict(type_counts),
            "subjects": dict(Counter(item["subject_name"] for item in generated)),
            "units": dict(Counter(f"{item['subject_name']}::Unit {item['unit_number']}" for item in generated)),
        },
        "questions": generated,
    }

    GENERATED_QUESTIONS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def evaluate_response(question_text, scope, selected_subject_id, selected_unit_id, selected_pdf_id, response, done_payload, stream_error):
    answer = (done_payload.get("markdown") or done_payload.get("bot_response") or "").strip()
    refs = done_payload.get("reference_previews") or []
    rets = done_payload.get("retrieval_previews") or []
    labels = [row.get("label", "") for row in refs] + [row.get("label", "") for row in rets]

    wrong_scope = False
    if scope == "subject" and selected_subject_id and done_payload.get("subject_id"):
        wrong_scope = str(done_payload.get("subject_id")) != str(selected_subject_id)
    if scope == "unit" and selected_unit_id and done_payload.get("unit_id"):
        wrong_scope = str(done_payload.get("unit_id")) != str(selected_unit_id)
    if scope == "pdf" and selected_pdf_id and done_payload.get("pdf_id"):
        wrong_scope = str(done_payload.get("pdf_id")) != str(selected_pdf_id)

    overlap = overlap_score(tokenize(question_text), tokenize(answer))
    irrelevant = answer != REJECT_MSG and overlap < 0.10
    strong_source = bool(labels) or bool(done_payload.get("answer_from"))

    reasons = []
    if response.status_code != 200:
        reasons.append("request_failed")
    if stream_error:
        reasons.append("stream_error")
    if not answer:
        reasons.append("empty_answer")
    if wrong_scope:
        reasons.append("wrong_scope_match")
    if irrelevant:
        reasons.append("irrelevant_answer")
    if answer != REJECT_MSG and not strong_source:
        reasons.append("missing_source_signal")

    has_heading = bool(re.search(r"(^|\n)#{1,6}\s+", answer))
    has_bullets = bool(re.search(r"(^|\n)\s*[-*+]\s+", answer))

    accuracy = 9.0
    if irrelevant:
        accuracy -= 3
    if answer != REJECT_MSG and not strong_source:
        accuracy -= 2
    if wrong_scope:
        accuracy -= 2
    if answer == REJECT_MSG:
        accuracy = min(accuracy, 8.0)
    accuracy = max(0.0, min(10.0, accuracy))

    relevance = 5.0 + min(5.0, overlap * 10.0)
    if wrong_scope:
        relevance -= 3.0
    if answer == REJECT_MSG:
        relevance = min(relevance, 6.0)
    relevance = max(0.0, min(10.0, relevance))

    clarity = 6.0 + (2.0 if len(answer) > 80 else 0.0) + (1.0 if has_heading else 0.0) + (1.0 if has_bullets else 0.0)
    clarity = max(0.0, min(10.0, clarity))

    structure = 4.0 + (3.0 if has_heading else 0.0) + (3.0 if has_bullets else 0.0)
    structure = max(0.0, min(10.0, structure))

    return {
        "answer": answer,
        "answer_from": done_payload.get("answer_from"),
        "source_labels": labels[:5],
        "strict_fail": bool(reasons),
        "strict_fail_reasons": reasons,
        "scores": {
            "accuracy": round(accuracy, 2),
            "clarity": round(clarity, 2),
            "structure": round(structure, 2),
            "relevance": round(relevance, 2),
        },
    }


def run_10000_question_stress_test(questions_payload):
    User = get_user_model()
    user = User.objects.filter(is_active=True).order_by("id").first()
    if not user:
        raise RuntimeError("No active user found for chatbot validation.")

    client = Client()
    client.force_login(user)

    all_scope_results = []
    question_rollup = []
    issue_counts = Counter()
    rejection_count = 0
    total_scope_runs = 0

    questions = questions_payload.get("questions", [])

    for idx, item in enumerate(questions, start=1):
        question_text = item["question"]
        selected_subject_id = item.get("subject_id")
        selected_unit_id = item.get("unit_id")
        selected_pdf_id = item.get("pdf_id")

        scopes = ["global", "subject", "unit"]
        if selected_pdf_id:
            scopes.append("pdf")

        per_scope = []
        for scope in scopes:
            total_scope_runs += 1
            form = {
                "question": question_text,
                "subject_id": str(selected_subject_id) if scope in {"subject", "unit", "pdf"} and selected_subject_id else "",
                "unit_id": str(selected_unit_id) if scope == "unit" and selected_unit_id else "",
                "pdf_id": str(selected_pdf_id) if scope == "pdf" and selected_pdf_id else "",
                "strict_mode": "on",
            }

            response = client.post(f"/chat/stream/?scope={scope}", data=form, secure=True)
            done_payload, stream_error = parse_stream_done(response)
            evaluation = evaluate_response(
                question_text,
                scope,
                selected_subject_id,
                selected_unit_id,
                selected_pdf_id,
                response,
                done_payload,
                stream_error,
            )

            if evaluation["answer"] == REJECT_MSG:
                rejection_count += 1

            for reason in evaluation["strict_fail_reasons"]:
                issue_counts[reason] += 1

            per_scope.append(
                {
                    "scope": scope,
                    "status": response.status_code,
                    "question": question_text,
                    "subject_id": selected_subject_id,
                    "unit_id": selected_unit_id,
                    "pdf_id": selected_pdf_id,
                    "answer": evaluation["answer"],
                    "answer_from": evaluation["answer_from"],
                    "source_labels": evaluation["source_labels"],
                    "scores": evaluation["scores"],
                    "strict_fail": evaluation["strict_fail"],
                    "strict_fail_reasons": evaluation["strict_fail_reasons"],
                }
            )

        all_scope_results.extend(per_scope)

        avg_accuracy = mean(row["scores"]["accuracy"] for row in per_scope)
        avg_clarity = mean(row["scores"]["clarity"] for row in per_scope)
        avg_structure = mean(row["scores"]["structure"] for row in per_scope)
        avg_relevance = mean(row["scores"]["relevance"] for row in per_scope)

        question_rollup.append(
            {
                "id": item["id"],
                "question": question_text,
                "subject_name": item.get("subject_name"),
                "unit_title": item.get("unit_title"),
                "difficulty": item.get("difficulty"),
                "question_type": item.get("question_type"),
                "tested_scopes": scopes,
                "passed": all(not row["strict_fail"] for row in per_scope),
                "failed_scopes": [row["scope"] for row in per_scope if row["strict_fail"]],
                "avg_scores": {
                    "accuracy": round(avg_accuracy, 2),
                    "clarity": round(avg_clarity, 2),
                    "structure": round(avg_structure, 2),
                    "relevance": round(avg_relevance, 2),
                },
            }
        )

        if idx % 200 == 0:
            print(f"[STRESS] processed {idx}/{len(questions)} questions")

    total_questions = len(question_rollup)
    passed_questions = sum(1 for row in question_rollup if row["passed"])
    failed_questions = total_questions - passed_questions

    summary = {
        "total_questions": total_questions,
        "passed_questions": passed_questions,
        "failed_questions": failed_questions,
        "passed_percentage": round((passed_questions / max(1, total_questions)) * 100.0, 2),
        "failed_percentage": round((failed_questions / max(1, total_questions)) * 100.0, 2),
        "avg_accuracy": round(mean(row["avg_scores"]["accuracy"] for row in question_rollup), 2) if question_rollup else 0.0,
        "avg_clarity": round(mean(row["avg_scores"]["clarity"] for row in question_rollup), 2) if question_rollup else 0.0,
        "avg_structure": round(mean(row["avg_scores"]["structure"] for row in question_rollup), 2) if question_rollup else 0.0,
        "avg_relevance": round(mean(row["avg_scores"]["relevance"] for row in question_rollup), 2) if question_rollup else 0.0,
        "total_scope_runs": total_scope_runs,
        "scope_failures": sum(1 for row in all_scope_results if row["strict_fail"]),
        "rejection_count": rejection_count,
        "top_failure_reasons": dict(issue_counts.most_common(10)),
    }

    return {
        "summary": summary,
        "question_rollup": question_rollup,
        "sample_scope_results": all_scope_results[:200],
    }


def detect_semester_from_path(file_path):
    joined = " ".join(part for part in file_path.parts)
    match = re.search(r"SEM\s*(\d+)", joined, flags=re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except Exception as e:
            print("ERROR:", str(e))
            return None
    return None


def load_pdf_text_sample(path, max_chars=6000):
    try:
        import fitz

        doc = fitz.open(str(path))
        pages = []
        for page_idx in range(min(2, len(doc))):
            try:
                pages.append(doc[page_idx].get_text() or "")
            except Exception as e:
                print("ERROR:", str(e))
                pages.append("")
        doc.close()
        text = "\n".join(pages)
        return text[:max_chars]
    except Exception as e:
        print("ERROR:", str(e))
        return ""


def subject_profile_tokens(subject, units_by_subject, map_subject_entry):
    parts = [subject.name, subject.subject_code or "", subject.description or ""]
    for unit in units_by_subject.get(subject.id, []):
        parts.append(unit.title)
        parts.append(unit.content or "")
    if map_subject_entry:
        parts.extend(map_subject_entry.get("keywords", []))
        parts.extend(map_subject_entry.get("topics", []))
    return tokenize(" ".join(parts))


def pick_best_subject_for_pdf(pdf_path, file_stem, file_text, subjects, units_by_subject, map_subject_lookup):
    semester_hint = detect_semester_from_path(pdf_path)
    target_subjects = [subject for subject in subjects if getattr(subject.semester, "number", None) == semester_hint] if semester_hint else list(subjects)
    if not target_subjects:
        target_subjects = list(subjects)

    file_tokens = tokenize(file_stem + " " + file_text)
    if not file_tokens:
        file_tokens = tokenize(file_stem)

    best_subject = None
    best_score = -1.0
    for subject in target_subjects:
        profile_tokens = subject_profile_tokens(subject, units_by_subject, map_subject_lookup.get(subject.id))
        score = overlap_score(file_tokens, profile_tokens)
        if subject.subject_code and subject.subject_code.lower() in file_stem.lower():
            score += 1.5
        if normalized_name(subject.name) in normalized_name(file_stem.replace("_", " ")):
            score += 2.0
        if score > best_score:
            best_score = score
            best_subject = subject

    if best_subject is None and subjects:
        best_subject = subjects[0]
    return best_subject, best_score


def pick_best_unit_for_pdf(subject, file_stem, file_text, units_by_subject):
    candidate_units = units_by_subject.get(subject.id, [])
    if not candidate_units:
        return None
    file_tokens = tokenize(file_stem + " " + file_text)
    best_unit = None
    best_score = -1.0
    for unit in candidate_units:
        score = overlap_score(file_tokens, tokenize(unit.title + " " + (unit.content or "")))
        if normalized_name(unit.title) and normalized_name(unit.title) in normalized_name(file_stem.replace("_", " ")):
            score += 1.2
        if score > best_score:
            best_score = score
            best_unit = unit
    return best_unit


def ingest_external_pdfs(source_folder, knowledge_map):
    source_path = Path(source_folder)
    if not source_path.exists():
        return {
            "source_folder": str(source_path),
            "scanned_files": 0,
            "added_pdfs": 0,
            "skipped_duplicates": 0,
            "failed": 0,
            "errors": [f"Source folder not found: {source_path}"],
            "added_pdf_ids": [],
        }

    subjects = list(
        Subject.objects.filter(is_active=True, semester__is_active=True)
        .select_related("semester")
        .order_by("semester__number", "name")
    )
    units = list(
        Unit.objects.filter(is_active=True, subject__is_active=True, subject__semester__is_active=True)
        .select_related("subject")
        .order_by("subject_id", "unit_number")
    )
    units_by_subject = defaultdict(list)
    for unit in units:
        units_by_subject[unit.subject_id].append(unit)

    map_subject_lookup = {entry["subject_id"]: entry for entry in knowledge_map.get("subjects", [])}

    existing_pdfs = list(ReferencePDF.objects.select_related("subject").all())
    existing_base_names = {Path(item.file.name).name.lower() for item in existing_pdfs if item.file and item.file.name}
    existing_title_subject = {(normalized_name(item.title), item.subject_id) for item in existing_pdfs}

    User = get_user_model()
    uploader = (
        User.objects.filter(is_active=True, role__in=["FACULTY", "PRINCIPAL"]).order_by("id").first()
        or User.objects.filter(is_active=True).order_by("id").first()
    )
    if not uploader:
        raise RuntimeError("No active uploader user available.")

    added_ids = []
    skipped_duplicates = 0
    failed = 0
    scanned = 0
    errors = []

    pdf_files = sorted([path for path in source_path.rglob("*.pdf") if path.is_file()])

    for pdf_path in pdf_files:
        scanned += 1
        file_stem = pdf_path.stem
        clean_file_name = sanitize_pdf_filename(file_stem)

        if clean_file_name.lower() in existing_base_names:
            skipped_duplicates += 1
            continue

        sample_text = load_pdf_text_sample(pdf_path)
        subject, subject_score = pick_best_subject_for_pdf(
            pdf_path,
            file_stem,
            sample_text,
            subjects,
            units_by_subject,
            map_subject_lookup,
        )
        if not subject:
            failed += 1
            errors.append(f"No subject match for PDF: {pdf_path}")
            continue

        unit = pick_best_unit_for_pdf(subject, file_stem, sample_text, units_by_subject)
        clean_title = re.sub(r"[_\-]+", " ", file_stem).strip() or file_stem

        title_subject_key = (normalized_name(clean_title), subject.id)
        if title_subject_key in existing_title_subject:
            skipped_duplicates += 1
            continue

        try:
            with pdf_path.open("rb") as handle:
                reference_pdf = ReferencePDF(
                    subject=subject,
                    unit=unit,
                    lesson=None,
                    uploaded_by=uploader,
                    title=clean_title,
                    is_active=True,
                    is_syllabus_reference=True,
                    status=ReferencePDF.Status.APPROVED,
                    processing_status=ReferencePDF.ProcessingStatus.PENDING,
                )
                reference_pdf.file.save(clean_file_name, File(handle), save=False)
                reference_pdf.save()

            process_pdf(reference_pdf, replace_existing=True)
            chunks = create_chunks_for_pdf(reference_pdf, reference_pdf.extracted_text or "")
            store_chunk_embeddings(chunks)
            upsert_index_for_chunk_ids([chunk.id for chunk in chunks])
            reference_pdf.chunk_count = len(chunks)
            reference_pdf.processing_status = ReferencePDF.ProcessingStatus.READY if chunks else ReferencePDF.ProcessingStatus.FAILED
            reference_pdf.save(update_fields=["chunk_count", "processing_status"])

            added_ids.append(reference_pdf.id)
            existing_base_names.add(clean_file_name.lower())
            existing_title_subject.add((normalized_name(clean_title), subject.id))

            if scanned % 20 == 0:
                print(f"[PDF INGEST] processed {scanned}/{len(pdf_files)} files")

        except Exception as exc:
            failed += 1
            errors.append(f"{pdf_path}: {exc}")

    return {
        "source_folder": str(source_path),
        "scanned_files": scanned,
        "added_pdfs": len(added_ids),
        "skipped_duplicates": skipped_duplicates,
        "failed": failed,
        "errors": errors[:200],
        "added_pdf_ids": added_ids,
    }


def generate_pdf_validation_questions(limit=20):
    questions = []
    chunks = list(
        PDFPageChunk.objects.filter(
            reference_pdf__is_active=True,
            reference_pdf__status=ReferencePDF.Status.APPROVED,
            reference_pdf__is_syllabus_reference=True,
            reference_pdf__subject__is_active=True,
            reference_pdf__subject__semester__is_active=True,
        )
        .select_related("reference_pdf", "reference_pdf__subject", "reference_pdf__unit")
        .order_by("reference_pdf_id", "page_number", "chunk_index")
    )

    for chunk in chunks:
        if len(questions) >= limit:
            break
        lines = sentence_candidates(chunk.text_content, min_len=35, max_len=140)
        if not lines:
            continue
        topic = lines[0].strip(" .")
        question = f"Explain this concept from the selected PDF: {topic}"
        questions.append(
            {
                "question": question,
                "pdf_id": chunk.reference_pdf_id,
                "subject_id": chunk.reference_pdf.subject_id,
                "unit_id": chunk.reference_pdf.unit_id,
                "expected_pdf_title": chunk.reference_pdf.title,
            }
        )
    return questions


def run_pdf_validation(questions):
    User = get_user_model()
    user = User.objects.filter(is_active=True).order_by("id").first()
    if not user:
        raise RuntimeError("No active user found for PDF validation.")

    client = Client()
    client.force_login(user)

    details = []
    issue_counts = Counter()
    passed = 0

    for idx, item in enumerate(questions, start=1):
        form = {
            "question": item["question"],
            "subject_id": str(item.get("subject_id") or ""),
            "unit_id": "",
            "pdf_id": str(item["pdf_id"]),
            "strict_mode": "on",
        }
        response = client.post("/chat/stream/?scope=pdf", data=form, secure=True)
        done_payload, stream_error = parse_stream_done(response)

        evaluation = evaluate_response(
            item["question"],
            "pdf",
            item.get("subject_id"),
            item.get("unit_id"),
            item.get("pdf_id"),
            response,
            done_payload,
            stream_error,
        )

        if not evaluation["strict_fail"]:
            passed += 1
        for reason in evaluation["strict_fail_reasons"]:
            issue_counts[reason] += 1

        details.append(
            {
                "id": idx,
                "question": item["question"],
                "pdf_id": item["pdf_id"],
                "status": response.status_code,
                "passed": not evaluation["strict_fail"],
                "reasons": evaluation["strict_fail_reasons"],
                "answer": evaluation["answer"],
                "answer_from": evaluation["answer_from"],
                "scores": evaluation["scores"],
            }
        )

    summary = {
        "total_questions": len(questions),
        "passed_questions": passed,
        "failed_questions": len(questions) - passed,
        "pass_percentage": round((passed / max(1, len(questions))) * 100.0, 2),
        "top_failure_reasons": dict(issue_counts.most_common(10)),
        "avg_accuracy": round(mean(item["scores"]["accuracy"] for item in details), 2) if details else 0.0,
        "avg_relevance": round(mean(item["scores"]["relevance"] for item in details), 2) if details else 0.0,
    }

    payload = {"summary": summary, "details": details}
    PDF_VALIDATION_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main():
    random.seed(42)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("[PHASE 1] Building database knowledge map...")
    context = build_database_knowledge_map()

    print("[PHASE 2] Generating 10,000 DB-only questions...")
    generated = generate_questions(context["unit_profiles"], total_questions=10000, seed=42)

    print("[PHASE 3+4] Running 10,000-question multi-scope stress test...")
    stress_result = run_10000_question_stress_test(generated)

    print("[PHASE 5] Ingesting PDFs from external folder...")
    source_folder = r"C:\Users\jithendra\OneDrive\Desktop\E learning Final Year Project\Final year project final\AI PDF's"
    pdf_ingestion_result = ingest_external_pdfs(source_folder, context["knowledge_map"])

    print("[PHASE 6] Running 20 PDF-specific validation questions...")
    pdf_questions = generate_pdf_validation_questions(limit=20)
    pdf_validation_result = run_pdf_validation(pdf_questions)

    final_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "phase1_database_analysis": {
            "knowledge_map_file": str(KNOWLEDGE_MAP_PATH),
            "counts": context["knowledge_map"].get("counts", {}),
        },
        "phase2_question_generation": {
            "questions_file": str(GENERATED_QUESTIONS_PATH),
            "total_questions": generated.get("total_questions", 0),
            "distribution": generated.get("distribution", {}),
        },
        "phase3_4_stress_validation": stress_result,
        "phase5_pdf_ingestion": pdf_ingestion_result,
        "phase6_pdf_validation": {
            "report_file": str(PDF_VALIDATION_PATH),
            "summary": pdf_validation_result.get("summary", {}),
        },
    }

    FINAL_VALIDATION_PATH.write_text(json.dumps(final_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    final_accuracy = stress_result["summary"].get("avg_accuracy", 0.0)
    total_added = pdf_ingestion_result.get("added_pdfs", 0)
    total_tested = stress_result["summary"].get("total_questions", 0)
    final_relevance = stress_result["summary"].get("avg_relevance", 0.0)

    ready = (
        stress_result["summary"].get("passed_percentage", 0.0) >= 95.0
        and final_accuracy >= 8.5
        and final_relevance >= 8.0
        and pdf_validation_result.get("summary", {}).get("pass_percentage", 0.0) >= 85.0
    )

    status_text = "✅ READY FOR FINAL SUBMISSION" if ready else "❌ NEEDS FIXES"

    print("\n=== FINAL OUTPUT ===")
    print(f"1. Total PDFs added: {total_added}")
    print(f"2. Total questions tested: {total_tested}")
    print(f"3. Final accuracy: {final_accuracy}")
    print(f"4. Final relevance: {final_relevance}")
    print(f"5. System status: {status_text}")
    print(f"Report: {FINAL_VALIDATION_PATH}")


if __name__ == "__main__":
    main()
