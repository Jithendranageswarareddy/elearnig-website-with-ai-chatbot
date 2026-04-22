import argparse
import json
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django

django.setup()

from django.db import transaction
from django.test import RequestFactory

from accounts.models import User
from chatbot.views import _run_chat_query
from courses.models import Subject, Unit

REPORT_PATH = BASE_DIR / "reports" / "final_1000_optimized_report.json"
ANSWER_SERVICE_PATH = BASE_DIR / "chatbot" / "services" / "answer_service.py"
SEARCH_SERVICE_PATH = BASE_DIR / "chatbot" / "services" / "search_service.py"
FORMATTER_PATH = BASE_DIR / "chatbot" / "services" / "answer_formatter.py"

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


def load_or_init_report(total_batches, batch_size):
    if REPORT_PATH.exists():
        try:
            with REPORT_PATH.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            data.setdefault("total_batches", total_batches)
            data.setdefault("batch_size", batch_size)
            data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            data.setdefault("batches", [])
            data.setdefault("overall_metrics", {})
            return data
        except Exception as e:
            print("ERROR:", str(e))
            pass

    return {
        "total_batches": total_batches,
        "batch_size": batch_size,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "batches": [],
        "overall_metrics": {},
    }


def save_report(report):
    report["updated_at"] = datetime.now(timezone.utc).isoformat()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)


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
    }


def generate_batch_questions(batch_number, batch_size, subjects, units):
    if not subjects or not units:
        return []

    rng = random.Random(3000 + batch_number)
    templates = question_templates()
    categories = list(templates.keys())

    by_subject = defaultdict(list)
    for unit in units:
        by_subject[int(unit.get("subject_id"))].append(unit)

    subject_cycle = list(subjects)
    rng.shuffle(subject_cycle)
    if not subject_cycle:
        return []

    questions = []
    for idx in range(batch_size):
        category = categories[idx % len(categories)]
        subject = subject_cycle[idx % len(subject_cycle)]
        sid = int(subject["id"])
        subject_units = by_subject.get(sid) or units
        unit = rng.choice(subject_units)
        other_unit = rng.choice(units)
        topic = unit.get("title") or subject.get("name")
        topic2 = other_unit.get("title") or topic
        question = rng.choice(templates[category]).format(topic=topic, topic2=topic2)
        questions.append(
            {
                "id": f"b{batch_number:02d}_q{idx + 1:03d}",
                "question": question,
                "question_type": category,
                "subject_id": sid,
                "subject_name": subject.get("name") or "Unknown",
                "unit_id": int(unit.get("id")),
            }
        )
    return questions


def tokenize(text):
    return [
        token
        for token in re.findall(r"[A-Za-z]{3,}", str(text or "").lower())
        if token not in STOPWORDS
    ]


def overlap_ratio(question, answer):
    q_terms = set(tokenize(question))
    if not q_terms:
        return 0.0
    a_terms = set(tokenize(answer))
    return float(len(q_terms & a_terms)) / float(len(q_terms))


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
    words = sentence.split()
    if len(words) < 5:
        return True
    if len(words) >= 6:
        return False
    return not bool(VERB_HINT_PATTERN.search(sentence))


def detect_issues(item, markdown):
    issues = []
    text_lower = (markdown or "").lower()

    if not markdown.strip():
        issues.append("empty_answer")

    required_headers = ["## Definition", "## Explanation", "## Key Points", "## Example", "## Conclusion"]
    if not all(header in markdown for header in required_headers):
        issues.append("formatting_missing_sections")

    lines = [line.strip() for line in markdown.splitlines() if line.strip() and not line.startswith("##")]
    if any(has_broken_fragment(line) for line in lines):
        issues.append("broken_sentence_fragment")

    ov = overlap_ratio(item["question"], markdown)
    if ov < 0.20:
        issues.append("irrelevant_content")

    hint_tokens = set(tokenize(item.get("subject_name", "")))
    answer_tokens = set(tokenize(text_lower))
    if hint_tokens and not (hint_tokens & answer_tokens):
        issues.append("wrong_subject")

    return sorted(set(issues))


def evaluate_scores(question, markdown, issues):
    overlap = overlap_ratio(question, markdown)
    headers = ["## Definition", "## Explanation", "## Key Points", "## Example", "## Conclusion"]
    has_structure = all(h in (markdown or "") for h in headers)

    accuracy = 10.0
    relevance = min(10.0, max(0.0, overlap * 10.0))
    clarity = 8.0

    penalty = {
        "formatting_missing_sections": (1.0, 1.0, 1.0),
        "broken_sentence_fragment": (1.5, 1.0, 2.0),
        "irrelevant_content": (2.0, 3.0, 1.0),
        "wrong_subject": (2.0, 2.0, 0.5),
        "empty_answer": (4.0, 4.0, 4.0),
    }

    for issue in issues:
        p = penalty.get(issue, (0.0, 0.0, 0.0))
        accuracy -= p[0]
        relevance -= p[1]
        clarity -= p[2]

    accuracy = round(max(0.0, min(10.0, accuracy)), 3)
    relevance = round(max(0.0, min(10.0, relevance)), 3)
    clarity = round(max(0.0, min(10.0, clarity)), 3)

    return accuracy, relevance, clarity, bool(has_structure)


def resolve_run_user():
    user = User.objects.filter(is_active=True, role=User.Role.STUDENT).order_by("id").first()
    if user:
        return user
    user = User.objects.filter(is_active=True).order_by("id").first()
    if user:
        return user
    raise RuntimeError("No active user found to run chat API loop.")


def ask_chatbot_non_stream_api(request_factory, user, item, regulation, branch, scope, semester=None):
    request = request_factory.post("/chat/")
    request.user = user

    with transaction.atomic():
        payload = _run_chat_query(
            request,
            item["question"],
            subject_id=item.get("subject_id"),
            unit_id=item.get("unit_id"),
            scope=scope,
            strict_mode=False,
            regulation=regulation,
            branch=branch,
            semester=semester,
        )
        transaction.set_rollback(True)

    markdown = str(payload.get("bot_response") or "").strip()
    return payload, markdown


def apply_one_best_fix(top_issue):
    """Apply exactly one highest-impact micro-fix per batch."""
    if top_issue == "broken_sentence_fragment":
        if ANSWER_SERVICE_PATH.exists():
            content = ANSWER_SERVICE_PATH.read_text(encoding="utf-8")
            old = "keep_sentence = (word_count >= 5 and _has_verb(sentence)) or (word_count >= 6)"
            new = "keep_sentence = (word_count >= 5 and _has_verb(sentence)) or (word_count >= 6 and sentence[0].isalnum())"
            if old in content:
                ANSWER_SERVICE_PATH.write_text(content.replace(old, new, 1), encoding="utf-8")
                return "answer_service.py: tightened 6-word fallback to alnum-led lines"
            return "answer_service.py: best fragment guard already active"

    if top_issue == "wrong_subject":
        if SEARCH_SERVICE_PATH.exists():
            content = SEARCH_SERVICE_PATH.read_text(encoding="utf-8")
            old = "and (keyword_hits > 0 or (unit_title_hits > 0 and subject_hits > 0))"
            new = "and ((keyword_hits > 0 and (subject_hits > 0 or unit_title_hits > 0)) or (unit_title_hits > 0 and subject_hits > 0))"
            if old in content:
                SEARCH_SERVICE_PATH.write_text(content.replace(old, new, 1), encoding="utf-8")
                return "search_service.py: strengthened subject/unit gate for keyword matches"
            return "search_service.py: subject gate already strengthened"

    if top_issue == "irrelevant_content":
        if ANSWER_SERVICE_PATH.exists():
            content = ANSWER_SERVICE_PATH.read_text(encoding="utf-8")
            old = "if keyword_hits >= 1 or overlap >= 0.40:"
            new = "if keyword_hits >= 1 or overlap >= 0.42:"
            if old in content:
                ANSWER_SERVICE_PATH.write_text(content.replace(old, new, 1), encoding="utf-8")
                return "answer_service.py: raised overlap fallback threshold from 0.40 to 0.42"
            return "answer_service.py: overlap threshold already tuned"

    if FORMATTER_PATH.exists():
        content = FORMATTER_PATH.read_text(encoding="utf-8")
        old = "A concise explanation is provided from the available references."
        new = "A concise, directly relevant explanation is provided from the available references."
        if old in content:
            FORMATTER_PATH.write_text(content.replace(old, new, 1), encoding="utf-8")
            return "answer_formatter.py: strengthened fallback relevance wording"

    return "No safe one-line fix candidate found; kept current best configuration"


def summarize_weak_dimensions(records):
    by_subject = defaultdict(list)
    by_type = defaultdict(list)
    for rec in records:
        by_subject[rec["subject_name"]].append(rec["relevance"])
        by_type[rec["question_type"]].append(rec["relevance"])

    weak_subjects = sorted(
        [{"subject": k, "avg_relevance": round(mean(v), 3)} for k, v in by_subject.items()],
        key=lambda x: x["avg_relevance"],
    )[:3]

    weak_types = sorted(
        [{"question_type": k, "avg_relevance": round(mean(v), 3)} for k, v in by_type.items()],
        key=lambda x: x["avg_relevance"],
    )[:3]

    return weak_subjects, weak_types


def run_batch(batch_number, batch_size, subjects, units, user, regulation, branch, scope, semester, delay_ms):
    rf = RequestFactory()
    questions = generate_batch_questions(batch_number, batch_size, subjects, units)

    records = []
    issue_counter = Counter()
    acc = []
    rel = []
    cla = []
    formatting_pass = 0

    for idx, item in enumerate(questions, start=1):
        try:
            _payload, markdown = ask_chatbot_non_stream_api(rf, user, item, regulation, branch, scope, semester)
        except Exception as exc:
            markdown = ""
            issues = ["empty_answer", "irrelevant_content"]
            accuracy, relevance, clarity, fmt = 0.0, 0.0, 0.0, False
            issue_counter.update(issues)
            records.append(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "question_type": item["question_type"],
                    "subject_name": item["subject_name"],
                    "accuracy": accuracy,
                    "relevance": relevance,
                    "clarity": clarity,
                    "formatting": "FAIL",
                    "issues": issues + [f"runtime_error:{exc}"],
                }
            )
            continue

        issues = detect_issues(item, markdown)
        accuracy, relevance, clarity, fmt = evaluate_scores(item["question"], markdown, issues)

        acc.append(accuracy)
        rel.append(relevance)
        cla.append(clarity)
        if fmt:
            formatting_pass += 1

        issue_counter.update(issues)
        records.append(
            {
                "id": item["id"],
                "question": item["question"],
                "question_type": item["question_type"],
                "subject_name": item["subject_name"],
                "accuracy": accuracy,
                "relevance": relevance,
                "clarity": clarity,
                "formatting": "PASS" if fmt else "FAIL",
                "issues": issues,
            }
        )

        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        if idx % 25 == 0:
            print(f"  Batch {batch_number}: processed {idx}/{batch_size}")

    top_issues = issue_counter.most_common(3)
    weak_subjects, weak_types = summarize_weak_dimensions(records)
    top_issue = top_issues[0][0] if top_issues else "none"
    fix_applied = apply_one_best_fix(top_issue)

    return {
        "batch_number": batch_number,
        "questions_tested": len(questions),
        "accuracy_avg": round(mean(acc), 3) if acc else 0.0,
        "relevance_avg": round(mean(rel), 3) if rel else 0.0,
        "clarity_avg": round(mean(cla), 3) if cla else 0.0,
        "formatting_pass_rate": round((formatting_pass / len(questions)) * 100.0, 2) if questions else 0.0,
        "top_3_issues": [{"issue": k, "count": v} for k, v in top_issues],
        "weak_subjects": weak_subjects,
        "weak_question_types": weak_types,
        "best_issue_selected": top_issue,
        "fix_applied": fix_applied,
    }


def recompute_overall_metrics(report):
    batches = report.get("batches", [])
    if not batches:
        report["overall_metrics"] = {
            "accuracy": 0.0,
            "relevance": 0.0,
            "clarity": 0.0,
            "best_batch": None,
            "top_improvements": [],
            "final_verdict": "insufficient_data",
        }
        return

    accuracy = round(mean([b.get("accuracy_avg", 0.0) for b in batches]), 3)
    relevance = round(mean([b.get("relevance_avg", 0.0) for b in batches]), 3)
    clarity = round(mean([b.get("clarity_avg", 0.0) for b in batches]), 3)

    best_batch = max(batches, key=lambda b: (b.get("accuracy_avg", 0), b.get("relevance_avg", 0), b.get("clarity_avg", 0)))

    improvements = []
    prev = None
    for batch in batches:
        if prev is None:
            prev = batch
            continue
        improvements.append(
            {
                "from_batch": prev["batch_number"],
                "to_batch": batch["batch_number"],
                "accuracy_delta": round(batch["accuracy_avg"] - prev["accuracy_avg"], 3),
                "relevance_delta": round(batch["relevance_avg"] - prev["relevance_avg"], 3),
                "clarity_delta": round(batch["clarity_avg"] - prev["clarity_avg"], 3),
            }
        )
        prev = batch

    top_improvements = sorted(
        improvements,
        key=lambda x: (x["relevance_delta"] + x["accuracy_delta"] + x["clarity_delta"]),
        reverse=True,
    )[:3]

    if relevance >= 6.0 and clarity >= 6.0 and accuracy >= 7.0:
        verdict = "best_settings_stable"
    elif relevance >= 5.0 and clarity >= 5.8:
        verdict = "good_but_tunable"
    else:
        verdict = "needs_more_tuning"

    report["overall_metrics"] = {
        "accuracy": accuracy,
        "relevance": relevance,
        "clarity": clarity,
        "best_batch": best_batch,
        "top_improvements": top_improvements,
        "final_verdict": verdict,
    }


def run_optimization(total_batches, batch_size, regulation, branch, scope, semester, delay_ms):
    report = load_or_init_report(total_batches=total_batches, batch_size=batch_size)
    completed = len(report.get("batches", []))
    start_batch = completed + 1

    if start_batch > total_batches:
        recompute_overall_metrics(report)
        save_report(report)
        print("Optimization already complete.")
        return

    subjects, units = collect_catalog()
    if not subjects or not units:
        raise RuntimeError("Catalog is empty. Ensure active subjects/units are available.")

    run_user = resolve_run_user()

    print(f"Starting CONTROLLED OPTIMIZATION loop: batches {start_batch} to {total_batches}")
    print(f"Batch size={batch_size}, total test cases target={total_batches * batch_size}")
    print(f"Run user={run_user.email} (role={run_user.role})")

    for batch_number in range(start_batch, total_batches + 1):
        print(f"\nRunning batch {batch_number}/{total_batches} ...")
        summary = run_batch(
            batch_number=batch_number,
            batch_size=batch_size,
            subjects=subjects,
            units=units,
            user=run_user,
            regulation=regulation,
            branch=branch,
            scope=scope,
            semester=semester,
            delay_ms=delay_ms,
        )

        prev = report["batches"][-1] if report.get("batches") else None
        improvement = {
            "accuracy_delta": round(summary["accuracy_avg"] - prev["accuracy_avg"], 3) if prev else 0.0,
            "relevance_delta": round(summary["relevance_avg"] - prev["relevance_avg"], 3) if prev else 0.0,
            "clarity_delta": round(summary["clarity_avg"] - prev["clarity_avg"], 3) if prev else 0.0,
        }
        summary["improvement_vs_previous_batch"] = improvement

        report.setdefault("batches", []).append(summary)
        recompute_overall_metrics(report)
        save_report(report)

        print(
            f"Batch {batch_number} complete | accuracy={summary['accuracy_avg']} "
            f"relevance={summary['relevance_avg']} clarity={summary['clarity_avg']} "
            f"formatting={summary['formatting_pass_rate']}%"
        )
        print(f"Top issues: {summary['top_3_issues']}")
        print(f"Applied one fix: {summary['fix_applied']}")

    print("\nOptimization loop complete.")
    print(f"Report updated: {REPORT_PATH}")


def parse_args():
    parser = argparse.ArgumentParser(description="Controlled 10x100 chatbot optimization loop")
    parser.add_argument("--total-batches", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--regulation", default="MIC20")
    parser.add_argument("--branch", default="CSE")
    parser.add_argument("--scope", default="global")
    parser.add_argument("--semester", default=None)
    parser.add_argument("--delay-ms", type=int, default=1)
    return parser.parse_args()


def main():
    args = parse_args()
    run_optimization(
        total_batches=max(1, int(args.total_batches)),
        batch_size=max(1, int(args.batch_size)),
        regulation=args.regulation,
        branch=args.branch,
        scope=args.scope,
        semester=args.semester,
        delay_ms=max(0, int(args.delay_ms)),
    )


if __name__ == "__main__":
    main()
