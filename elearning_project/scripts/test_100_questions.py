"""
Test chatbot performance with 100 generated questions.
Evaluates accuracy, relevance, and rejection behavior.
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from statistics import mean

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from courses.models import Subject, Unit

# Configuration
TEST_CONFIG = {
    "scope": "global",
    "regulation": "MIC20",
    "branch": "CSE",
}

# Rejection message from chatbot
REJECT_MSG = "This topic is not available in the selected syllabus."

# Stopwords for overlap calculation
STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "and", "or", "to", "of", "in", "for", "with", "on", "by", "from", "as", "it",
    "its", "this", "that", "be", "vs", "versus", "why", "how", "where", "when", "define", "explain", "differentiate", 
    "compare", "list", "describe", "discuss", "elaborate", "give", "provide", "about", "then", "do", "not", "can", "should"
}


def tokenize(text):
    """Extract meaningful tokens from text."""
    return [
        token
        for token in re.findall(r"[a-zA-Z]{3,}", str(text or "").lower())
        if token not in STOPWORDS
    ]


def overlap_ratio(question, answer):
    """Calculate overlap between question and answer tokens."""
    q_tokens = set(tokenize(question))
    a_tokens = set(tokenize(answer))
    if not q_tokens:
        return 0.0
    return len(q_tokens & a_tokens) / len(q_tokens)


def parse_stream_response(response):
    """Parse streaming JSON response from chatbot API."""
    done_payload = None
    error_msg = None
    chunks = []
    
    try:
        for part in response.streaming_content:
            if isinstance(part, bytes):
                part = part.decode("utf-8", "ignore")
            chunks.append(part)
        
        content = "".join(chunks)
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") == "error":
                    error_msg = event.get("message", "Unknown error")
                if event.get("type") == "done":
                    done_payload = event.get("payload") or {}
            except json.JSONDecodeError:
                continue
    except Exception as e:
        error_msg = str(e)
    
    return done_payload or {}, error_msg


def classify_result(question, response, answer, response_code, error):
    """Classify test result as PASS, FAIL, or REJECT."""
    
    # Check if rejected by system
    is_rejected = answer.strip() == REJECT_MSG
    if is_rejected:
        return "REJECT", "System rejected the question"
    
    # Check for errors or bad response
    if response_code != 200:
        return "FAIL", f"HTTP {response_code}"
    
    if error:
        return "FAIL", f"Stream error: {error}"
    
    if not answer or len(answer.strip()) < 20:
        return "FAIL", "Empty or too short response"
    
    # Check relevance through token overlap
    overlap = overlap_ratio(question, answer)
    if overlap < 0.15:
        return "FAIL", f"Low relevance (overlap: {overlap:.2f})"
    
    # Calculate answer quality metrics
    answer_length = len(answer.split())
    if answer_length < 10:
        return "FAIL", "Answer too brief"
    
    # Check if answer seems reasonable (not just keywords)
    if answer_length > 5 and len(answer) > 50:
        return "PASS", f"Relevant answer (overlap: {overlap:.2f}, length: {answer_length} words)"
    
    return "FAIL", "Answer quality insufficient"


def calculate_relevance(answer):
    """Calculate relevance score (0-10) based on answer characteristics."""
    if not answer or answer == REJECT_MSG:
        return 0
    
    # Factors for relevance scoring
    length = min(len(answer.split()) / 50, 1.0)  # Longer answers more relevant
    structure = min(answer.count('.') / 5, 1.0)  # More sentences better structured
    clarity = min(len(answer) / 500, 1.0)  # More detailed = more clear
    
    score = (length + structure + clarity) / 3 * 10
    return round(score, 2)


def main():
    print("=" * 80)
    print("CHATBOT 100-QUESTION PERFORMANCE TEST")
    print("=" * 80)
    
    # Load test questions
    questions_file = os.path.join("reports", "test_100_questions.json")
    if not os.path.exists(questions_file):
        print(f"❌ ERROR: Questions file not found: {questions_file}")
        return
    
    with open(questions_file, "r", encoding="utf-8") as f:
        questions = json.load(f)
    
    print(f"\n📚 Loaded {len(questions)} test questions")
    print(f"⚙️  Configuration:")
    for key, value in TEST_CONFIG.items():
        print(f"   • {key}: {value}")
    
    # Get authenticated user
    User = get_user_model()
    user = User.objects.filter(is_active=True).order_by("id").first()
    if not user:
        print("❌ ERROR: No active user found")
        return
    
    print(f"👤 User: {user.username}")
    
    # Initialize test client
    client = Client()
    client.force_login(user)
    
    print("\n🧪 Testing questions...")
    print("-" * 80)
    
    results = []
    stats = {
        "total": len(questions),
        "pass": 0,
        "fail": 0,
        "reject": 0,
        "errors": 0,
    }
    
    relevance_scores = []
    subject_results = defaultdict(lambda: {"pass": 0, "fail": 0, "reject": 0, "total": 0})
    type_results = defaultdict(lambda: {"pass": 0, "fail": 0, "reject": 0, "total": 0})
    
    for idx, question in enumerate(questions, 1):
        question_text = question["question"]
        subject = question.get("subject", "Unknown")
        unit = question.get("unit", "Unknown")
        qtype = question.get("type", "unknown")
        
        # Prepare form data
        form_data = {
            "question": question_text,
            "scope": TEST_CONFIG["scope"],
            # regulation and branch are typically not form params, but settings
        }
        
        # Send request to chatbot API
        try:
            response = client.post("/chat/stream/", data=form_data, secure=True)
            done_payload, error = parse_stream_response(response)
            
            answer = (done_payload.get("markdown") or done_payload.get("bot_response") or "").strip()
            
            # Classify result
            status, reason = classify_result(question_text, response, answer, response.status_code, error)
            
            # Calculate relevance
            relevance = calculate_relevance(answer)
            if status != "REJECT":
                relevance_scores.append(relevance)
            
            # Update statistics
            stats[status.lower()] += 1
            subject_results[subject][status.lower()] += 1
            subject_results[subject]["total"] += 1
            type_results[qtype][status.lower()] += 1
            type_results[qtype]["total"] += 1
            
            # Store result
            result = {
                "id": question["id"],
                "question": question_text[:100] + "..." if len(question_text) > 100 else question_text,
                "subject": subject,
                "unit": unit,
                "type": qtype,
                "difficulty": question.get("difficulty", "unknown"),
                "status": status,
                "reason": reason,
                "response_snippet": answer[:200] + "..." if len(answer) > 200 else answer,
                "response_length": len(answer),
                "relevance_score": relevance,
                "http_status": response.status_code,
            }
            results.append(result)
            
            # Progress indicator
            if idx % 10 == 0:
                print(f"   ✓ Processed {idx}/{len(questions)} questions")
        
        except Exception as e:
            print(f"   ❌ Error on question {idx}: {str(e)}")
            stats["errors"] += 1
            results.append({
                "id": question["id"],
                "question": question_text[:100],
                "subject": subject,
                "unit": unit,
                "type": qtype,
                "status": "ERROR",
                "reason": str(e),
                "response_snippet": "",
                "response_length": 0,
                "relevance_score": 0,
                "http_status": 0,
            })
    
    print(f"   ✓ Processed {len(questions)}/{len(questions)} questions")
    
    # Save detailed results
    os.makedirs("reports", exist_ok=True)
    results_file = os.path.join("reports", "test_100_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Calculate metrics
    accuracy = round((stats["pass"] / max(1, stats["total"] - stats["errors"])) * 100, 2)
    relevance_avg = round(mean(relevance_scores), 2) if relevance_scores else 0
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ Final Results:")
    print(f"   • Total Questions: {stats['total']}")
    print(f"   • Passed: {stats['pass']} ({round((stats['pass']/stats['total'])*100, 1)}%)")
    print(f"   • Failed: {stats['fail']} ({round((stats['fail']/stats['total'])*100, 1)}%)")
    print(f"   • Rejected: {stats['reject']} ({round((stats['reject']/stats['total'])*100, 1)}%)")
    if stats["errors"] > 0:
        print(f"   • Errors: {stats['errors']} ({round((stats['errors']/stats['total'])*100, 1)}%)")
    
    print(f"\n📈 Performance Metrics:")
    print(f"   • Accuracy: {accuracy}%")
    print(f"   • Average Relevance Score: {relevance_avg}/10")
    print(f"   • Effective Pass Rate: {round((stats['pass'] + stats['pass']*0.5) / stats['total'] * 100, 1)}%")
    
    # Subject-wise breakdown
    print(f"\n📚 Subject-wise Performance:")
    for subject in sorted(subject_results.keys()):
        s = subject_results[subject]
        subject_accuracy = round((s["pass"] / max(1, s["total"])) * 100, 1)
        print(f"   • {subject}: {s['pass']}/{s['total']} passed ({subject_accuracy}%)")
    
    # Type-wise breakdown
    print(f"\n❓ Question Type Performance:")
    for qtype in sorted(type_results.keys()):
        t = type_results[qtype]
        type_accuracy = round((t["pass"] / max(1, t["total"])) * 100, 1)
        print(f"   • {qtype.capitalize()}: {t['pass']}/{t['total']} passed ({type_accuracy}%)")
    
    # Detailed failure analysis
    failures = [r for r in results if r["status"] == "FAIL"]
    if failures:
        print(f"\n⚠️  Failure Analysis ({len(failures)} failures):")
        failure_reasons = defaultdict(int)
        for failure in failures:
            reason = failure["reason"]
            # Extract main reason
            main_reason = reason.split("(")[0].strip()
            failure_reasons[main_reason] += 1
        
        for reason, count in sorted(failure_reasons.items(), key=lambda x: -x[1])[:5]:
            print(f"   • {reason}: {count} failures")
    
    # Rejections analysis
    rejections = [r for r in results if r["status"] == "REJECT"]
    if rejections:
        print(f"\n🚫 Rejections Analysis ({len(rejections)} rejections):")
        print(f"   • Total rejections: {len(rejections)}")
        rejection_subjects = defaultdict(int)
        for rejection in rejections:
            rejection_subjects[rejection["subject"]] += 1
        
        print(f"   • By subject:")
        for subject, count in sorted(rejection_subjects.items(), key=lambda x: -x[1])[:5]:
            print(f"     - {subject}: {count}")
    
    print("\n" + "=" * 80)
    print(f"📁 Detailed results saved to: {os.path.abspath(results_file)}")
    print("=" * 80)
    
    # Save summary to JSON
    summary = {
        "test_config": TEST_CONFIG,
        "total_questions": stats["total"],
        "passed": stats["pass"],
        "failed": stats["fail"],
        "rejected": stats["reject"],
        "errors": stats["errors"],
        "accuracy_percentage": accuracy,
        "average_relevance_score": relevance_avg,
        "subject_performance": dict(subject_results),
        "type_performance": dict(type_results),
        "timestamp": str(Path(results_file).stat().st_mtime) if os.path.exists(results_file) else None,
    }
    
    summary_file = os.path.join("reports", "test_100_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"📋 Summary saved to: {os.path.abspath(summary_file)}")


if __name__ == "__main__":
    main()
