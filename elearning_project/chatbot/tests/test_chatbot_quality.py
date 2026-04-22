import argparse
import json
import re
import statistics
import time
from collections import Counter
from pathlib import Path
import sys

import os

# Ensure the Django project package (folder containing manage.py) is on sys.path
PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django

django.setup()

from django.conf import settings

from chatbot.services.search_service import search_chunks
from chatbot.services.answer_synthesis_service import synthesize_answer, deterministic_synthesize_answer


BASE_QUESTIONS = [
    "What is Object Oriented Programming?",
    "Explain polymorphism in OOP.",
    "What is encapsulation?",
    "What is inheritance?",
    "What is abstraction?",
    "What is stack data structure?",
    "What is queue data structure?",
    "What are the advantages of OOP?",
    "Differentiate class and object.",
    "What is method overloading?",
]

TOPICS = [
    "object oriented programming",
    "class",
    "object",
    "encapsulation",
    "inheritance",
    "polymorphism",
    "abstraction",
    "method overloading",
    "method overriding",
    "constructor",
    "destructor",
    "stack",
    "queue",
    "linked list",
    "array",
    "pointer",
    "function",
    "recursion",
    "tree",
    "binary search",
    "sorting",
    "time complexity",
    "space complexity",
]

QUESTION_TEMPLATES = [
    "What is {topic}?",
    "Explain {topic} in simple terms.",
    "Give a short explanation of {topic}.",
    "Why is {topic} important?",
    "How does {topic} work?",
    "What are the key points of {topic}?",
]

GENERIC_PATTERNS = [
    "this topic can be understood",
    "in practical situations",
    "students should consult",
]


def build_question_bank(target_count=100):
    questions = []
    seen = set()

    def add(question):
        normalized = " ".join((question or "").split()).strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            questions.append(question.strip())

    for question in BASE_QUESTIONS:
        add(question)

    for topic in TOPICS:
        for template in QUESTION_TEMPLATES:
            add(template.format(topic=topic))
            if len(questions) >= target_count:
                return questions[:target_count]

    return questions[:target_count]


def extract_main_answer(markdown):
    text = markdown or ""
    match = re.search(r"##\s+Main Answer\s*(.*?)(?:\n##\s+|$)", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return " ".join(match.group(1).split()).strip()


def concept_from_question(question):
    lowered = (question or "").lower()
    token_matches = re.findall(r"[a-zA-Z0-9]+", lowered)
    for topic in TOPICS:
        if topic in lowered:
            return topic
    return token_matches[-1] if token_matches else ""


def looks_irrelevant(question, payload):
    markdown = payload.get("markdown", "") or ""
    main_answer = extract_main_answer(markdown)
    if not main_answer:
        return True, "empty_main_answer"

    concept = concept_from_question(question)
    concept_tokens = set(re.findall(r"[a-zA-Z0-9]+", concept.lower()))
    answer_tokens = set(re.findall(r"[a-zA-Z0-9]+", main_answer.lower()))

    if concept_tokens and not (concept_tokens & answer_tokens):
        return True, "topic_tokens_missing"

    lowered = main_answer.lower()
    if any(pattern in lowered for pattern in GENERIC_PATTERNS):
        return True, "generic_answer_pattern"

    return False, ""


def evaluate_question(question, search_limit=10, generation_mode="deterministic"):
    start = time.perf_counter()
    chunks = search_chunks(question, limit=search_limit)
    retrieved = len(chunks)

    synth_start = time.perf_counter()
    if generation_mode == "llm":
        payload = synthesize_answer(question, chunks)
    else:
        payload = deterministic_synthesize_answer(question, chunks)
    synth_secs = time.perf_counter() - synth_start
    total_secs = time.perf_counter() - start

    markdown = payload.get("markdown", "") or ""
    answer_preview = extract_main_answer(markdown)[:220]
    references_count = int(payload.get("references_count", 0) or 0)

    irrelevant, reason = looks_irrelevant(question, payload)
    return {
        "question": question,
        "retrieved_chunk_count": retrieved,
        "references_count": references_count,
        "generation_time_seconds": round(total_secs, 3),
        "synthesis_seconds": round(synth_secs, 3),
        "generation_mode": payload.get("generation_mode"),
        "llm_model_used": payload.get("llm_model_used"),
        "answer_preview": answer_preview,
        "is_empty_answer": not bool(answer_preview.strip()),
        "is_irrelevant": bool(irrelevant),
        "irrelevant_reason": reason,
    }


def evaluate_retrieval_quality(question, search_limit=10):
    chunks = search_chunks(question, limit=search_limit)
    if not chunks:
        return {"relevant": False, "score": 0.0}

    query_tokens = set(re.findall(r"[a-zA-Z0-9]+", question.lower()))
    query_tokens = {token for token in query_tokens if len(token) >= 3}
    if not query_tokens:
        return {"relevant": True, "score": 0.0}

    overlap_scores = []
    for chunk in chunks[:5]:
        chunk_tokens = set(re.findall(r"[a-zA-Z0-9]+", (chunk.text_content or "").lower()))
        chunk_tokens = {token for token in chunk_tokens if len(token) >= 3}
        overlap = len(query_tokens & chunk_tokens) / max(1, len(query_tokens))
        overlap_scores.append(overlap)

    mean_overlap = statistics.mean(overlap_scores) if overlap_scores else 0.0
    return {"relevant": mean_overlap >= 0.2, "score": mean_overlap}


def summarize_results(results):
    times = [item["generation_time_seconds"] for item in results]
    refs = [item["references_count"] for item in results]

    empty_rows = [item for item in results if item["is_empty_answer"]]
    irrelevant_rows = [item for item in results if item["is_irrelevant"]]

    answer_hashes = [re.sub(r"\s+", " ", (item["answer_preview"] or "").lower()).strip() for item in results]
    answer_counter = Counter(answer_hashes)
    repeated_rows = [
        item for item in results if answer_counter.get(re.sub(r"\s+", " ", (item["answer_preview"] or "").lower()).strip(), 0) > 1
    ]

    summary = {
        "question_count": len(results),
        "average_generation_time_seconds": round(statistics.mean(times), 3) if times else 0.0,
        "p95_generation_time_seconds": round(sorted(times)[max(0, int(len(times) * 0.95) - 1)], 3) if times else 0.0,
        "average_reference_count": round(statistics.mean(refs), 3) if refs else 0.0,
        "empty_answer_count": len(empty_rows),
        "irrelevant_answer_count": len(irrelevant_rows),
        "repeated_answer_count": len(repeated_rows),
        "irrelevant_examples": [
            {
                "question": item["question"],
                "reason": item["irrelevant_reason"],
                "answer_preview": item["answer_preview"],
            }
            for item in irrelevant_rows[:15]
        ],
        "empty_examples": [item["question"] for item in empty_rows[:15]],
    }
    return summary


def score_summary(summary):
    penalty = (
        summary.get("irrelevant_answer_count", 0) * 4
        + summary.get("empty_answer_count", 0) * 6
        + summary.get("repeated_answer_count", 0) * 2
    )
    reward = summary.get("average_reference_count", 0.0) * 1.5
    speed_penalty = max(0.0, summary.get("average_generation_time_seconds", 0.0) - 8.0) * 2.0
    return reward - penalty - speed_penalty


def run_improvement_loop(questions, max_rounds=3):
    candidates = [
        {"vector": 0.75, "keyword": 0.25, "min_token": 3},
        {"vector": 0.65, "keyword": 0.35, "min_token": 3},
        {"vector": 0.55, "keyword": 0.45, "min_token": 3},
        {"vector": 0.60, "keyword": 0.40, "min_token": 4},
    ]

    best = None
    history = []
    probe_questions = questions[: min(30, len(questions))]

    for round_index in range(max_rounds):
        improved_this_round = False
        for candidate in candidates:
            settings.CHATBOT_RERANK_VECTOR_WEIGHT = candidate["vector"]
            settings.CHATBOT_RERANK_KEYWORD_WEIGHT = candidate["keyword"]
            settings.CHATBOT_RERANK_MIN_TOKEN_LENGTH = candidate["min_token"]

            retrieval_rows = [evaluate_retrieval_quality(question, search_limit=10) for question in probe_questions]
            relevance_scores = [row["score"] for row in retrieval_rows]
            relevant_count = sum(1 for row in retrieval_rows if row["relevant"])
            summary = {
                "probe_count": len(probe_questions),
                "relevant_count": relevant_count,
                "avg_retrieval_overlap": round(statistics.mean(relevance_scores), 4) if relevance_scores else 0.0,
            }
            score = (summary["relevant_count"] * 1.5) + (summary["avg_retrieval_overlap"] * 10.0)
            record = {
                "round": round_index + 1,
                "candidate": candidate,
                "summary": summary,
                "score": round(score, 3),
            }
            history.append(record)

            if best is None or score > best["score"]:
                best = {"score": score, "candidate": candidate, "summary": summary}
                improved_this_round = True

        if not improved_this_round:
            break

    if best:
        settings.CHATBOT_RERANK_VECTOR_WEIGHT = best["candidate"]["vector"]
        settings.CHATBOT_RERANK_KEYWORD_WEIGHT = best["candidate"]["keyword"]
        settings.CHATBOT_RERANK_MIN_TOKEN_LENGTH = best["candidate"]["min_token"]

    return best, history


def main():
    parser = argparse.ArgumentParser(description="Evaluate chatbot answer quality with automated tuning loop.")
    parser.add_argument("--questions", type=int, default=100, help="Number of questions to evaluate.")
    parser.add_argument("--max-rounds", type=int, default=3, help="Max auto-improvement rounds.")
    parser.add_argument("--generation-mode", choices=["deterministic", "llm"], default="deterministic")
    parser.add_argument("--output", type=str, default="elearning_project/reports/chatbot_quality_report.json")
    args = parser.parse_args()

    questions = build_question_bank(target_count=max(100, args.questions))[: args.questions]

    print(f"Running auto-improvement loop on {min(30, len(questions))} probe questions...")
    best, history = run_improvement_loop(questions, max_rounds=max(1, args.max_rounds))
    if best:
        print("Selected rerank configuration:", best["candidate"])

    print(f"Running full evaluation on {len(questions)} questions...")
    results = []
    for idx, question in enumerate(questions, start=1):
        row = evaluate_question(question, search_limit=10, generation_mode=args.generation_mode)
        results.append(row)
        if idx % 10 == 0:
            print(f"Processed {idx}/{len(questions)}")

    summary = summarize_results(results)
    report = {
        "settings": {
            "openrouter_key_present": bool((getattr(settings, "OPENROUTER_API_KEY", "") or "").strip()),
            "generation_mode": args.generation_mode,
            "rerank_vector_weight": float(getattr(settings, "CHATBOT_RERANK_VECTOR_WEIGHT", 0.65)),
            "rerank_keyword_weight": float(getattr(settings, "CHATBOT_RERANK_KEYWORD_WEIGHT", 0.35)),
            "rerank_min_token_length": int(getattr(settings, "CHATBOT_RERANK_MIN_TOKEN_LENGTH", 3)),
        },
        "improvement_history": history,
        "summary": summary,
        "results": results,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== QUALITY SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
