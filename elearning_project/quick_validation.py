#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning_project.settings')
import django
django.setup()

from chatbot.services.search_service import search_chunks
import time

queries = [
    ("What is Database Normalization?", "accept"),
    ("What is SQL?", "accept"),
    ("Compare recursion and iteration", "accept"),
    ("What is IPL cricket?", "reject"),
    ("What is Software Architecture?", "accept"),
]

print("\n" + "="*70)
print("FINAL VALIDATION - All 5 Queries with v3 Word-Boundary Fix")
print("="*70)

passed = 0
for i, (query, expected) in enumerate(queries, 1):
    start = time.time()
    chunks = search_chunks(query)
    elapsed = (time.time() - start) * 1000
    
    if chunks and isinstance(chunks[0], dict):
        text_first = chunks[0].get('text_content', '')
    elif chunks and hasattr(chunks[0], 'text_content'):
        text_first = chunks[0].text_content
    else:
        text_first = ""
    is_rejected = text_first == "No relevant content found in PDFs"
    
    if len(chunks) == 0:
        result = "REJECTED"
    elif is_rejected:
        result = "REJECTED"
    else:
        result = f"ACCEPTED ({len(chunks)} chunks)"
    
    is_pass = (expected == "reject" and result.startswith("REJECTED")) or (expected == "accept" and result.startswith("ACCEPTED"))
    status = "✅" if is_pass else "❌"
    if is_pass:
        passed += 1
    
    print(f"{status} Q{i}: {query[:38]:38} -> {result:20} [{elapsed:6.0f}ms]")

print("="*70)
print(f"Result: {passed}/{len(queries)} tests passed")
if passed == len(queries):
    print("🎉 ALL VALIDATION TESTS PASSED!")
print("="*70)
