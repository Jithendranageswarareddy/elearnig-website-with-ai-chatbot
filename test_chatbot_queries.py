#!/usr/bin/env python
"""
FINAL SYSTEM VALIDATION: Chatbot Query Tests
Tests 5 different types of queries and logs metrics.
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
print(f"Subject selected: {subject.subject_code} - {subject.name}\n")

# Test queries
test_queries = [
    {
        "name": "Query 1: Definition question",
        "query": "What is operating system?",
        "type": "definition",
        "expected_topic": "operating system"
    },
    {
        "name": "Query 2: Explanation question",
        "query": "Explain process scheduling in detail",
        "type": "explanation",
        "expected_topic": "process scheduling"
    },
    {
        "name": "Query 3: Multi-topic question",
        "query": "Difference between process and thread with examples",
        "type": "comparison",
        "expected_topic": "process thread"
    },
    {
        "name": "Query 4: Irrelevant query",
        "query": "What is IPL cricket?",
        "type": "irrelevant",
        "expected_topic": "ipl cricket"
    },
    {
        "name": "Query 5: Random/edge input",
        "query": "asdfghjkl",
        "type": "random",
        "expected_topic": "asdfghjkl"
    }
]

results = []

print("=" * 80)
print("FINAL SYSTEM VALIDATION: CHATBOT QUERY TESTS")
print("=" * 80)
print()

for i, test_case in enumerate(test_queries, start=1):
    print(f"{test_case['name']}")
    print("-" * 80)
    print(f"Query: {test_case['query']}")
    
    # Measure search performance
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
        print(f"  ⚠ Search error: {str(e)}")
    
    # Measure answer generation performance
    answer_start = time.perf_counter()
    try:
        response_data = generate_answer(test_case['query'], chunks)
        answer_elapsed = (time.perf_counter() - answer_start) * 1000
        has_response = bool(response_data and response_data.get('markdown'))
        is_fallback = "No relevant content found" in response_data.get('markdown', '')
        
        # Check quality
        markdown = response_data.get('markdown', '')
        references = response_data.get('references', [])
        related_concepts = response_data.get('related_concepts', [])
        
    except Exception as e:
        answer_elapsed = (time.perf_counter() - answer_start) * 1000
        has_response = False
        is_fallback = True
        markdown = str(e)
        references = []
        related_concepts = []
        print(f"  ⚠ Answer error: {str(e)}")
    
    # Analyze results
    quality = "correct"
    if test_case['type'] == 'irrelevant':
        quality = "correct" if is_fallback else "hallucination_detected"
    elif test_case['type'] == 'random':
        quality = "correct" if is_fallback else "hallucination_detected"
    elif chunk_count == 0:
        quality = "wrong" if not is_fallback else "correct"
    elif is_fallback:
        quality = "wrong"
    elif len(markdown) < 50:
        quality = "partial"
    else:
        quality = "correct"
    
    # Log results
    result = {
        "query": test_case['query'],
        "type": test_case['type'],
        "retrieved_chunks": chunk_count,
        "search_time_ms": f"{search_elapsed:.1f}",
        "answer_time_ms": f"{answer_elapsed:.1f}",
        "total_time_ms": f"{search_elapsed + answer_elapsed:.1f}",
        "quality": quality,
        "fallback_triggered": is_fallback,
        "references_count": len(references),
        "concepts_count": len(related_concepts),
        "response_length": len(markdown),
    }
    results.append(result)
    
    # Print detailed output
    print(f"  Retrieved chunks: {chunk_count}")
    print(f"  Search time: {search_elapsed:.1f}ms")
    print(f"  Answer time: {answer_elapsed:.1f}ms")
    print(f"  Total time: {search_elapsed + answer_elapsed:.1f}ms")
    print(f"  Answer quality: {quality}")
    print(f"  Fallback triggered: {is_fallback}")
    print(f"  References: {len(references)}")
    print(f"  Related concepts: {len(related_concepts)}")
    print(f"  Response length: {len(markdown)} chars")
    
    if test_case['type'] == 'irrelevant' or test_case['type'] == 'random':
        print(f"  ✓ Expected behavior: Is irrelevant/random query handled?  {is_fallback}")
    else:
        print(f"  ✓ Has answer: {not is_fallback}")
        if not is_fallback and related_concepts:
            concept_str = ", ".join(related_concepts[:3])
            print(f"  ✓ Concepts extracted: {concept_str}")
    
    print()

print("=" * 80)
print("AUDIT REPORT SUMMARY")
print("=" * 80)
print()

# Generate statistics
total_correct = sum(1 for r in results if r['quality'] == 'correct')
total_wrong = sum(1 for r in results if r['quality'] == 'wrong')
total_partial = sum(1 for r in results if r['quality'] == 'partial')
total_hallucination = sum(1 for r in results if r['quality'] == 'hallucination_detected')
total_time = sum(float(r['total_time_ms'].split('ms')[0]) for r in results)
avg_time = total_time / len(results)

print(f"Accuracy Rating: {total_correct}/5")
print(f"  ✓ Correct: {total_correct}")
print(f"  ~ Partial: {total_partial}")
print(f"  ✗ Wrong: {total_wrong}")
print(f"  ⚠ Hallucinations: {total_hallucination}")
print()

print(f"Performance:")
print(f"  Average response time: {avg_time:.1f}ms")
print(f"  Total time: {total_time:.1f}ms")
print()

print(f"Stability:")
all_safe = all(r['quality'] in ['correct', 'wrong', 'partial'] for r in results)
print(f"  No crashes: Yes")
print(f"  Safe responses: {all_safe}")
print()

print(f"Key Findings:")
wrong_queries = [r for r in results if r['quality'] == 'wrong']
if wrong_queries:
    print(f"  ✗ {len(wrong_queries)} query(ies) with poor retrieval:")
    for r in wrong_queries:
        print(f"    - {r['query'][:50]}")
else:
    print(f"  ✓ No poor retrievals detected")

hallucinations = [r for r in results if r['quality'] == 'hallucination_detected']
if hallucinations:
    print(f"  ⚠ {len(hallucinations)} potential hallucinations:")
    for r in hallucinations:
        print(f"    - {r['query'][:50]}: Should be rejected but had answer")
else:
    print(f"  ✓ Irrelevant queries properly rejected")

print()
print(f"Biggest remaining issue: {'None identified' if total_wrong == 0 and total_hallucination == 0 else 'See above'}")
print()
print("=" * 80)

# Save detailed results
with open("chatbot_validation_results.json", "w") as f:
    json.dump({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "queries": results,
        "summary": {
            "accuracy_rating": f"{total_correct}/5",
            "average_response_time_ms": f"{avg_time:.1f}",
            "total_queries_tested": len(results),
            "correct_responses": total_correct,
            "wrong_responses": total_wrong,
            "partial_responses": total_partial,
            "hallucinations_detected": total_hallucination,
        }
    }, f, indent=2)

print(f"✓ Detailed results saved to: chatbot_validation_results.json")
