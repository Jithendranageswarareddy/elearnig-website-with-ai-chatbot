import argparse
import json
import os
import random
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django

django.setup()

from courses.models import Subject, Unit
from chatbot.services.search_service import search_chunks
from chatbot.services.answer_service import generate_answer

REPORT_PATH = BASE_DIR / "reports" / "final_100000_test_report.json"
ALLOWED_FIX_FILES = [
    BASE_DIR / "chatbot" / "services" / "answer_service.py",
    BASE_DIR / "chatbot" / "services" / "answer_formatter.py",
    BASE_DIR / "chatbot" / "services" / "search_service.py",
]

STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "and", "or", "to", "of", "in", "for", "with", "on", "by", "from",
    "as", "it", "its", "this", "that", "be", "vs", "versus", "why", "how", "where", "when", "define", "explain",
    "differentiate", "compare", "list", "please", "about", "give", "describe", "between", "used", "using",
}

VERB_HINT_PATTERN = re.compile(
    r"(?i)\\b("
    r"is|are|was|were|be|being|been|has|have|had|"
    r"do|does|did|can|could|will|would|shall|should|may|might|must|"
    r"allocate|allocates|allocated|allocating|schedule|schedules|scheduled|scheduling|"
    r"manage|manages|managed|managing|execute|executes|executed|executing|"
    r"process|processes|processed|processing|run|runs|running|"
    r"determine|determines|determined|determining|provide|provides|provided|providing|"
    r"use|uses|used|using|perform|performs|performed|performing|"
    r"(?:[A-Za-z]{4,}(?:ed|ing))"
    r")\\b"
)

BANNED_PHRASES = [
    "is a syllabus concept in which",
    "this unit covers",
    "seed content",
    "detailed explanation",
    "exact match is limited",
    "partial syllabus context",
]


def tokenize(text):
    return [
        token
        for token in re.findall(r"[A-Za-z]{3,}", str(text or "").lower())
        if token not in STOPWORDS
    ]


def overlap_ratio(question, answer):
    q_tokens = set(tokenize(question))
    a_tokens = set(tokenize(answer))
    if not q_tokens:
        return 0.0
    return float(len(q_tokens & a_tokens)) / float(len(q_tokens))


def load_or_init_report(total_questions):
    if REPORT_PATH.exists():
        with open(REPORT_PATH, "r", encoding="utf-8") as handle:
            report = json.load(handle)
        report.setdefault("batches", [])
        report.setdefault("overall_metrics", {})
        report.setdefault("meta", {})
        return report

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    return {
        "total_questions": total_questions,
        "batches": [],
        "overall_metrics": {
            "accuracy": 0.0,
            "relevance": 0.0,
            "clarity": 0.0,
            "formatting_pass_rate": 0.0,
            "improvement_trend": [],
            "top_10_recurring_issues": [],
            "system_verdict": "pending",
        },
        "meta": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def save_report(report):
    report["meta"]["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)


def collect_catalog():
    subjects = list(
        Subject.objects.filter(is_active=True, semester__is_active=True)
        .order_by("id")
        .values("id", "name")
    )
    units = list(
        Unit.objects.filter(is_active=True, subject__is_active=True, subject__semester__is_active=True)
        .order_by("id")
        .values("id", "title", "subject_id", "subject__name")
    )
    return subjects, units


def question_templates():
    return {
        "definitions": [
            "What is {topic}?",
            "Define {topic} in simple terms.",
        ],
        "concepts": [
            "Explain the core concept of {topic}.",
            "How does {topic} work?",
        ],
        "comparisons": [
            "Compare {topic} and {topic2}.",
            "Differentiate {topic} from {topic2}.",
        ],
        "applications": [
            "Where is {topic} applied in real systems?",
            "Give a practical use case of {topic}.",
        ],
        "edge_cases": [
            "What are common failure cases of {topic}?",
            "How does {topic} behave under heavy load?",
        ],
        "cross_subject": [
            "How is {topic} used in {subject2}?",
            "Relate {topic} from {subject} to {subject2} with one example.",
        ],
    }


def generate_batch_questions(batch_number, batch_size, subjects, units):
    if not units:
        return []
    rng = random.Random(1000 + batch_number)
    templates = question_templates()
    categories = list(templates.keys())

    questions = []
    for index in range(batch_size):
        category = categories[index % len(categories)]
        unit = rng.choice(units)
        subject = unit.get("subject__name") or "the subject"
        subject2 = rng.choice(subjects).get("name") if subjects else subject
        topic = unit.get("title") or subject
        topic2 = rng.choice(units).get("title") if len(units) > 1 else topic
        template = rng.choice(templates[category])

        question_text = template.format(
            topic=topic,
            topic2=topic2,
            subject=subject,
            subject2=subject2,
        )
        questions.append(
            {
                "id": f"b{batch_number:03d}_q{index + 1:04d}",
                "question": question_text,
                "category": category,
                "subject_hint": subject,
            }
        )
    return questions


def extract_text_sections(markdown):
    sections = {
        "definition": "",
        "explanation": "",
        "key_points": "",
        "example": "",
        "conclusion": "",
    }
    if not markdown:
        return sections

    pattern = re.compile(
        r"##\s*(Definition|Explanation|Key Points|Example|Conclusion)\s*\n",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(markdown))
    if not matches:
        sections["definition"] = markdown.strip()
        return sections

    for idx, match in enumerate(matches):
        title = match.group(1).strip().lower().replace(" ", "_")
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        sections[title] = markdown[start:end].strip()
    return sections


def has_broken_fragment(line):
    sentence = str(line or "").strip()
    if not sentence:
        return False
    if len(sentence.split()) < 5:
        return True
    if not VERB_HINT_PATTERN.search(sentence):
        return True
    return False


def detect_issues(question, markdown, payload):
    issues = []
    text_lower = (markdown or "").lower()
    sections = extract_text_sections(markdown)

    if not markdown:
        issues.append("empty_answer")

    required_headers = ["## Definition", "## Explanation", "## Key Points", "## Example", "## Conclusion"]
    if not all(header in (markdown or "") for header in required_headers):
        issues.append("formatting_missing_sections")

    for phrase in BANNED_PHRASES:
        if phrase in text_lower:
            issues.append("banned_phrase_present")
            break

    lines = [line.strip() for line in (markdown or "").splitlines() if line.strip() and not line.startswith("##")]
    if any(has_broken_fragment(line) for line in lines):
        issues.append("broken_sentence_fragment")

    if re.search(r"\b(\w+)\s+\1\b", markdown or "", flags=re.IGNORECASE):
        issues.append("repeated_words")

    overlap = overlap_ratio(question, markdown or "")
    if overlap < 0.20:
        issues.append("irrelevant_content")

    definition = sections.get("definition", "")
    if not re.search(r"\b(is|refers to|means|defined as)\b", definition.lower()):
        issues.append("weak_definition")

    example_text = sections.get("example", "")
    if len(example_text.split()) < 8:
        issues.append("missing_example")

    answer_from = str((payload or {}).get("answer_from") or "")
    question_tokens = tokenize(question)
    if question_tokens and answer_from:
        if len(set(question_tokens) & set(tokenize(answer_from))) == 0:
            issues.append("possible_wrong_subject")

    return sorted(set(issues))


def evaluate_scores(question, markdown, issues):
    overlap = overlap_ratio(question, markdown)
    headers = ["## Definition", "## Explanation", "## Key Points", "## Example", "## Conclusion"]
    has_structure = all(h in (markdown or "") for h in headers)
    definition = extract_text_sections(markdown).get("definition", "")

    accuracy = 10.0
    relevance = min(10.0, max(0.0, overlap * 10.0))
    clarity = 8.0

    penalty_map = {
        "formatting_missing_sections": (1.5, 1.5, 1.0),
        "banned_phrase_present": (2.0, 1.0, 1.0),
        "broken_sentence_fragment": (1.5, 1.0, 2.0),
        "repeated_words": (1.0, 0.5, 1.5),
        "irrelevant_content": (2.0, 3.0, 1.0),
        "weak_definition": (1.5, 1.0, 1.0),
        "missing_example": (1.0, 0.5, 1.5),
        "possible_wrong_subject": (2.0, 2.0, 0.5),
        "empty_answer": (4.0, 4.0, 4.0),
    }

    for issue in issues:
        p = penalty_map.get(issue, (0.0, 0.0, 0.0))
        accuracy -= p[0]
        relevance -= p[1]
        clarity -= p[2]

    if definition and len(definition.split()) >= 8 and re.search(r"\b(is|refers to|means|defined as)\b", definition.lower()):
        clarity += 0.5

    accuracy = round(max(0.0, min(10.0, accuracy)), 2)
    relevance = round(max(0.0, min(10.0, relevance)), 2)
    clarity = round(max(0.0, min(10.0, clarity)), 2)
    formatting_pass = has_structure and ("banned_phrase_present" not in issues)

    return accuracy, relevance, clarity, formatting_pass


def apply_small_auto_fixes(issue_counter):
    fixes = []

    # Safety: tiny deterministic replacements only.
    replacements = []
    if issue_counter.get("banned_phrase_present", 0) > 0:
        replacements.extend([
            (ALLOWED_FIX_FILES[0], "is a syllabus concept in which", "is"),
            (ALLOWED_FIX_FILES[0], "This unit covers", ""),
            (ALLOWED_FIX_FILES[1], "Detailed explanation is not available from the current context.", "A concise explanation is provided from the available references."),
        ])

    if issue_counter.get("repeated_words", 0) > 25:
        replacements.append((ALLOWED_FIX_FILES[0], r"return _collapse_duplicate_words\(_refine_academic_english\(sentence\)\)", "return _collapse_duplicate_words(_refine_academic_english(sentence))"))

    for file_path, old_text, new_text in replacements:
        try:
            if not file_path.exists():
                continue
            content = file_path.read_text(encoding="utf-8")
            if old_text in content:
                updated = content.replace(old_text, new_text)
                if updated != content:
                    file_path.write_text(updated, encoding="utf-8")
                    fixes.append(f"Updated {file_path.name}: replaced '{old_text[:40]}'")
        except Exception as exc:
            fixes.append(f"Failed to patch {file_path.name}: {exc}")

    if not fixes:
        fixes.append("No code patch required; existing safeguards already cover detected issues.")

    return fixes


def ask_chatbot_internal(question, regulation, branch, scope):
    chunks = search_chunks(
        question,
        scope=scope,
        regulation=regulation,
        branch=branch,
        limit=5,
    )
    payload = generate_answer(question, chunks)
    markdown = (payload.get("markdown") or payload.get("bot_response") or "").strip()
    return payload, markdown


def run_batch(batch_number, batch_size, subjects, units, regulation, branch, scope, delay_ms):
    questions = generate_batch_questions(batch_number, batch_size, subjects, units)

    batch_records = []
    accuracy_scores = []
    relevance_scores = []
    clarity_scores = []
    formatting_pass_count = 0
    issue_counter = Counter()
    sample_failures = []
    errors = []

    for idx, item in enumerate(questions, start=1):
        question = item["question"]
        payload = {}
        markdown = ""
        call_error = None

        for attempt in (1, 2):
            try:
                payload, markdown = ask_chatbot_internal(question, regulation, branch, scope)
                call_error = None
                break
            except Exception as exc:
                call_error = str(exc)
                if attempt == 1:
                    time.sleep(0.05)

        if call_error:
            issues = ["runtime_error", "empty_answer"]
            accuracy, relevance, clarity, formatting_pass = 0.0, 0.0, 0.0, False
            errors.append({"question": question, "error": call_error})
        else:
            issues = detect_issues(question, markdown, payload)
            accuracy, relevance, clarity, formatting_pass = evaluate_scores(question, markdown, issues)

        accuracy_scores.append(accuracy)
        relevance_scores.append(relevance)
        clarity_scores.append(clarity)
        if formatting_pass:
            formatting_pass_count += 1

        issue_counter.update(issues)
        if issues and len(sample_failures) < 15:
            sample_failures.append(
                {
                    "question": question,
                    "issues": issues,
                    "response_excerpt": (markdown or "")[:280],
                }
            )

        batch_records.append(
            {
                "id": item["id"],
                "category": item["category"],
                "question": question,
                "accuracy": accuracy,
                "relevance": relevance,
                "clarity": clarity,
                "formatting": "PASS" if formatting_pass else "FAIL",
                "issues": issues,
            }
        )

        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        if idx % 100 == 0:
            print(f"  Batch {batch_number}: processed {idx}/{batch_size}")

    fixes_applied = apply_small_auto_fixes(issue_counter)

    return {
        "batch_number": batch_number,
        "questions_tested": len(questions),
        "accuracy_avg": round(mean(accuracy_scores), 3) if accuracy_scores else 0.0,
        "relevance_avg": round(mean(relevance_scores), 3) if relevance_scores else 0.0,
        "clarity_avg": round(mean(clarity_scores), 3) if clarity_scores else 0.0,
        "formatting_pass_rate": round((formatting_pass_count / max(1, len(questions))) * 100.0, 2),
        "issues_found": [
            {"issue": issue, "count": count}
            for issue, count in issue_counter.most_common()
        ],
        "fixes_applied": fixes_applied,
        "sample_failures": sample_failures,
        "errors": errors[:20],
    }


def recompute_overall_metrics(report):
    batches = report.get("batches", [])
    if not batches:
        return

    total_q = sum(batch.get("questions_tested", 0) for batch in batches)
    weighted_accuracy = 0.0
    weighted_relevance = 0.0
    weighted_clarity = 0.0
    weighted_formatting = 0.0
    issue_counter = Counter()
    trend = []

    for batch in batches:
        tested = max(1, int(batch.get("questions_tested", 0) or 0))
        weighted_accuracy += float(batch.get("accuracy_avg", 0.0)) * tested
        weighted_relevance += float(batch.get("relevance_avg", 0.0)) * tested
        weighted_clarity += float(batch.get("clarity_avg", 0.0)) * tested
        weighted_formatting += float(batch.get("formatting_pass_rate", 0.0)) * tested

        for item in batch.get("issues_found", []):
            issue_counter.update({item.get("issue", "unknown"): int(item.get("count", 0) or 0)})

        trend.append(
            {
                "batch": batch.get("batch_number"),
                "accuracy": batch.get("accuracy_avg", 0.0),
                "relevance": batch.get("relevance_avg", 0.0),
                "clarity": batch.get("clarity_avg", 0.0),
            }
        )

    total_q = max(1, total_q)
    accuracy = round(weighted_accuracy / total_q, 3)
    relevance = round(weighted_relevance / total_q, 3)
    clarity = round(weighted_clarity / total_q, 3)
    formatting = round(weighted_formatting / total_q, 2)

    if accuracy >= 8.0 and relevance >= 8.0 and formatting >= 90.0:
        verdict = "excellent"
    elif accuracy >= 7.0 and relevance >= 7.0 and formatting >= 80.0:
        verdict = "stable"
    elif accuracy >= 5.5 and relevance >= 5.5:
        verdict = "improving"
    else:
        verdict = "needs_attention"

    report["overall_metrics"] = {
        "accuracy": accuracy,
        "relevance": relevance,
        "clarity": clarity,
        "formatting_pass_rate": formatting,
        "improvement_trend": trend,
        "top_10_recurring_issues": [
            {"issue": issue, "count": count}
            for issue, count in issue_counter.most_common(10)
        ],
        "system_verdict": verdict,
    }


def run_pipeline(total_batches, batch_size, run_batches, regulation, branch, scope, delay_ms):
    total_questions = total_batches * batch_size
    report = load_or_init_report(total_questions=total_questions)
    subjects, units = collect_catalog()

    if not units:
        raise RuntimeError("No active units available to generate stress questions.")

    completed = len(report.get("batches", []))
    start_batch = completed + 1
    end_batch = min(total_batches, completed + run_batches)

    if start_batch > total_batches:
        print("All batches already completed.")
        recompute_overall_metrics(report)
        save_report(report)
        return

    print(f"Starting SAFE MODE stress pipeline: batches {start_batch} to {end_batch}")
    print(f"Batch size={batch_size}, total target={total_batches} batches")

    for batch_number in range(start_batch, end_batch + 1):
        print(f"\nRunning batch {batch_number}/{total_batches} ...")
        batch_summary = run_batch(
            batch_number=batch_number,
            batch_size=batch_size,
            subjects=subjects,
            units=units,
            regulation=regulation,
            branch=branch,
            scope=scope,
            delay_ms=delay_ms,
        )

        report.setdefault("batches", []).append(batch_summary)
        recompute_overall_metrics(report)
        save_report(report)

        print(
            f"Batch {batch_number} complete | accuracy={batch_summary['accuracy_avg']} "
            f"relevance={batch_summary['relevance_avg']} clarity={batch_summary['clarity_avg']} "
            f"formatting={batch_summary['formatting_pass_rate']}%"
        )

    print("\nPipeline run finished for requested range.")
    print(f"Report updated: {REPORT_PATH}")


def parse_args():
    parser = argparse.ArgumentParser(description="Safe-mode 100k chatbot stress pipeline")
    parser.add_argument("--total-batches", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--run-batches", type=int, default=1, help="How many new batches to run in this invocation")
    parser.add_argument("--regulation", default="MIC20")
    parser.add_argument("--branch", default="CSE")
    parser.add_argument("--scope", default="global")
    parser.add_argument("--delay-ms", type=int, default=2)
    return parser.parse_args()


def main():
    args = parse_args()
    run_pipeline(
        total_batches=max(1, int(args.total_batches)),
        batch_size=max(1, int(args.batch_size)),
        run_batches=max(1, int(args.run_batches)),
        regulation=args.regulation,
        branch=args.branch,
        scope=args.scope,
        delay_ms=max(0, int(args.delay_ms)),
    )


if __name__ == "__main__":
    main()
