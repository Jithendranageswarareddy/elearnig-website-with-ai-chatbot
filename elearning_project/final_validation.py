#!/usr/bin/env python
"""Final validation - all 5 original queries with v3 word-boundary fix"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning_project.settings')

import django
django.setup()

from chatbot.services.search_service import search_chunks
from chatbot.services.answer_service import generate_answer
import time
import json

def get_text(chunk):
    if isinstance(chunk, dict):
        return chunk.get("text_content", "")
    else:
        return getattr(chunk, "text_content", "")

# Test queries
queries = [
    ("What is Database Normalization?", "should find relevant content"),
    ("What is SQL?", "should find relevant content"),
    ("Compare recursion and iteration", "should find relevant content"),
    ("What is IPL cricket?", "MUST REJECT (hallucination test)"),
    ("What is Software Architecture?", "should find relevant content"),
]

results = {}

print("\n" + "="*80)
print("FINAL VALIDATION - All 5 Original Queries with v3 Word-Boundary Fix")
print("="*80)

for i, (query, expected) in enumerate(queries, 1):
    print(f"\n{'─'*80}")
    print(f"Query {i}: '{query}'")
    print(f"Expected: {expected}")
    print(f"{'─'*80}")
    
    start = time.time()
    chunks = search_chunks(query)
    elapsed = (time.time() - start) * 1000
    
    text_first = get_text(chunks[0]) if chunks else ""
    is_rejected = text_first == "No relevant content found in PDFs"
    chunk_count = len(chunks)
    
    print(f"Chunks: {chunk_count} | Time: {elapsed:.1f}ms")
    
    if chunk_count == 0:
        print("Result: REJECTED (empty)")
        result_status = "REJECTED"
    elif is_rejected:
        print("Result: REJECTED (fallback message)")
        result_status = "REJECTED"
    else:
        print(f"Result: ACCEPTED ({chunk_count} chunks)")
        result_status = "ACCEPTED"
        for j, chunk in enumerate(chunks[:2], 1):
            metadata = getattr(chunk, 'retrieval_metadata', {})
            score = metadata.get('score', 0) if isinstance(metadata, dict) else 0
            text = get_text(chunk)
            print(f"  Chunk {j} (score: {score:.3f}): {text[:60]}...")
    
    # Determine PASS/FAIL
    if i == 4:  # IPL cricket - must reject
        status = "✅ PASS" if result_status == "REJECTED" else "❌ FAIL"
    else:  # Others - must accept
        status = "✅ PASS" if result_status == "ACCEPTED" else "❌ FAIL"
    
    print(f"Status: {status}")
    results[i] = {
        "query": query,
        "result": result_status,
        "chunks": chunk_count,
        "time_ms": elapsed,
        "pass": "PASS" in status
    }

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
passed = sum(1 for r in results.values() if r["pass"])
total = len(results)

for i, result in results.items():
    status = "✅" if result["pass"] else "❌"
    print(f"{status} Query {i}: {result['result']} ({result['chunks']} chunks)")

print(f"\nFinal Score: {passed}/{total} tests passed")
print("="*80)

if passed == total:
    print("🎉 ALL VALIDATION TESTS PASSED - SYSTEM READY FOR DEPLOYMENT!")
else:
    print(f"⚠️  {total - passed} test(s) failed")

print("="*80)
