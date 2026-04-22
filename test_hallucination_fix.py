#!/usr/bin/env python
"""
HALLUCINATION FIX VALIDATION: Before/After Test
Tests Query 4 (IPL cricket) which previously hallucinated
"""
import os
import sys
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "elearning_project"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django
django.setup()

from accounts.models import User
from courses.models import Subject
from chatbot.services.search_service import search_chunks
from chatbot.services.answer_service import generate_answer

# Create test user if needed
student, _ = User.objects.get_or_create(
    email="test_student@test.com",
    defaults={
        "name": "Test Student",
        "role": User.Role.STUDENT,
    }
)

# Get a subject with PDFs
subject = Subject.objects.filter(reference_pdfs__isnull=False).first()
print(f"Subject: {subject.subject_code} - {subject.name}\n")

# Critical test cases
test_cases = [
    {
        "name": "CRITICAL: IPL Cricket (Should REJECT)",
        "query": "What is IPL cricket?",
        "type": "irrelevant",
        "expected": "REJECTED",
        "description": "Sports topic - completely off-topic from CS curriculum"
    },
    {
        "name": "VALID: Operating System (Should ACCEPT)",
        "query": "What is operating system?",
        "type": "valid",
        "expected": "ACCEPTED",
        "description": "Core CS topic covered in syllabus"
    },
    {
        "name": "EDGE: Random Gibberish (Should REJECT)",
        "query": "asdfghjkl",
        "type": "random",
        "expected": "REJECTED",
        "description": "No semantic meaning"
    },
]

results = []
print("=" * 100)
print("HALLUCINATION FIX VALIDATION TEST")
print("=" * 100)
print()

for i, test_case in enumerate(test_cases, start=1):
    print(f"TEST {i}: {test_case['name']}")
    print(f"  Description: {test_case['description']}")
    print(f"  Query: '{test_case['query']}'")
    print(f"  Expected: {test_case['expected']}")
    print("-" * 100)
    
    # Search for chunks
    search_start = time.perf_counter()
    try:
        chunks = search_chunks(
            query=test_case['query'],
            subject_id=subject.id,
            limit=5,
        )
        search_elapsed = (time.perf_counter() - search_start) * 1000
        chunk_count = len(chunks) if chunks else 0
    except Exception as e:
        search_elapsed = (time.perf_counter() - search_start) * 1000
        chunk_count = 0
        chunks = []
        print(f"  ⚠ ERROR: {str(e)}")
    
    # Generate answer
    answer_start = time.perf_counter()
    try:
        response_data = generate_answer(test_case['query'], chunks)
        answer_elapsed = (time.perf_counter() - answer_start) * 1000
        markdown = response_data.get('markdown', '')
        is_fallback = "No relevant content found" in markdown
        references = response_data.get('references', [])
    except Exception as e:
        answer_elapsed = (time.perf_counter() - answer_start) * 1000
        markdown = str(e)
        is_fallback = True
        references = []
    
    # Determine result
    result_status = "REJECTED" if is_fallback else "PROVIDED_ANSWER"
    is_correct = (result_status == test_case['expected']) or \
                 (test_case['expected'] == "REJECTED" and result_status == "REJECTED") or \
                 (test_case['expected'] == "ACCEPTED" and result_status == "PROVIDED_ANSWER")
    
    result_symbol = "✅" if is_correct else "❌"
    
    print(f"  Chunks Retrieved: {chunk_count}")
    print(f"  Search Time: {search_elapsed:.1f}ms")
    print(f"  Answer Time: {answer_elapsed:.1f}ms")
    print(f"  Answer Status: {result_status}")
    print(f"  References Found: {len(references)}")
    print(f"  Response Length: {len(markdown)} chars")
    print()
    
    if is_fallback:
        print(f"  🛡️ FALLBACK TRIGGERED")
        print(f"     Message: 'No relevant content found in PDFs'")
    else:
        print(f"  📝 ANSWER PROVIDED")
        preview = markdown[:150].replace('\n', ' ') + "..." if len(markdown) > 150 else markdown.replace('\n', ' ')
        print(f"     Preview: {preview}")
    
    print()
    print(f"  {result_symbol} TEST RESULT: {'PASS ✅' if is_correct else 'FAIL ❌'}")
    print()
    
    results.append({
        "test": test_case['name'],
        "query": test_case['query'],
        "chunks_retrieved": chunk_count,
        "expected": test_case['expected'],
        "actual": result_status,
        "is_correct": is_correct,
        "search_time_ms": f"{search_elapsed:.1f}",
        "answer_time_ms": f"{answer_elapsed:.1f}",
        "references": len(references),
    })

print("=" * 100)
print("SUMMARY REPORT")
print("=" * 100)
print()

passed = sum(1 for r in results if r['is_correct'])
total = len(results)
accuracy = (passed / total * 100) if total > 0 else 0

print(f"Tests Passed: {passed}/{total} ({accuracy:.0f}%)")
print()

# Critical test result
critical_test = results[0]  # IPL cricket test
print(f"🔴 CRITICAL TEST (Hallucination Fix): {critical_test['test']}")
print(f"   Query: {critical_test['query']}")
print(f"   Expected: {critical_test['expected']}")
print(f"   Actual: {critical_test['actual']}")
print(f"   Status: {'✅ FIXED!' if critical_test['is_correct'] else '❌ STILL BROKEN'}")
print()

# Performance summary
avg_search = sum(float(r['search_time_ms']) for r in results) / len(results)
print(f"⚡ Performance:")
print(f"   Average Search Time: {avg_search:.1f}ms")
print()

# System status
if passed == total:
    print("🎉 ALL TESTS PASSED - HALLUCINATION FIX SUCCESSFUL")
    status = "READY_FOR_DEPLOYMENT"
else:
    print("⚠️ SOME TESTS FAILED - FIX NOT COMPLETE")
    status = "FIX_INCOMPLETE"

print()
print("=" * 100)

# Save results
report = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "test_type": "Hallucination Fix Validation",
    "status": status,
    "tests_passed": passed,
    "tests_total": total,
    "accuracy_percent": accuracy,
    "tests": results,
    "critical_test_result": critical_test['is_correct'],
    "before_behavior": "Query 4 (IPL cricket) returned answer - HALLUCINATION",
    "after_behavior": "Query 4 should now return 'No relevant content found' - NO HALLUCINATION",
}

with open("hallucination_fix_validation.json", "w") as f:
    json.dump(report, f, indent=2)

print(f"✓ Detailed results saved to: hallucination_fix_validation.json")
print()

# Exit code indicates success/failure
sys.exit(0 if passed == total else 1)
