#!/usr/bin/env python
"""Test script to validate v3 word-boundary keyword matching fix"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning_project.settings')

import django
django.setup()

from chatbot.services.search_service import search_chunks
import time

def format_chunk_info(chunk):
    """Format chunk info for display"""
    # Handle both dict and PDFPageChunk objects
    if isinstance(chunk, dict):
        metadata = chunk.get('retrieval_metadata', {})
        text = chunk.get('text_content', '')
    else:
        metadata = getattr(chunk, 'retrieval_metadata', {})
        text = getattr(chunk, 'text_content', '')
    
    return {
        'text': str(text)[:80],
        'score': metadata.get('score', 0) if isinstance(metadata, dict) else 0,
        'semantic': metadata.get('semantic_score', 0) if isinstance(metadata, dict) else 0,
        'keyword': metadata.get('keyword_score', 0) if isinstance(metadata, dict) else 0,
    }

# Test 1: IPL Cricket (should be REJECTED)
print("\n" + "="*70)
print("TEST 1: IPL Cricket Query (should be REJECTED)")
print("="*70)
start = time.time()
chunks = search_chunks("What is IPL cricket?")
elapsed = (time.time() - start) * 1000

print(f"\nQuery: 'What is IPL cricket?'")
print(f"Chunks Retrieved: {len(chunks)}")
print(f"Search Time: {elapsed:.1f}ms")

def get_text(chunk):
    if isinstance(chunk, dict):
        return chunk.get("text_content", "")
    else:
        return getattr(chunk, "text_content", "")

is_rejected = chunks and get_text(chunks[0]) == "No relevant content found in PDFs"
if is_rejected:
    print("✅ RESULT: CORRECTLY REJECTED")
else:
    print("❌ RESULT: WRONG - Got answer instead of rejection")
    for i, chunk in enumerate(chunks[:2], 1):
        info = format_chunk_info(chunk)
        print(f"\n   Chunk {i}:")
        print(f"      Text: {info['text']}...")
        print(f"      Score: {info['score']:.3f} | Semantic: {info['semantic']:.3f} | Keyword: {info['keyword']:.1f}")

test1_pass = is_rejected

# Test 2: Operating System (should be ACCEPTED)
print("\n" + "="*70)
print("TEST 2: Operating System Query (should be ACCEPTED)")
print("="*70)
start = time.time()
chunks = search_chunks("What is an Operating System?")
elapsed = (time.time() - start) * 1000

print(f"\nQuery: 'What is an Operating System?'")
print(f"Chunks Retrieved: {len(chunks)}")
print(f"Search Time: {elapsed:.1f}ms")

is_accepted = chunks and get_text(chunks[0]) != "No relevant content found in PDFs"
if is_accepted:
    print("✅ RESULT: CORRECTLY ACCEPTED")
    for i, chunk in enumerate(chunks[:3], 1):
        info = format_chunk_info(chunk)
        print(f"\n   Chunk {i}:")
        print(f"      Text: {info['text']}...")
        print(f"      Score: {info['score']:.3f}")

test2_pass = is_accepted

# Test 3: Gibberish (should be REJECTED)
print("\n" + "="*70)
print("TEST 3: Gibberish Query (should be REJECTED)")
print("="*70)
start = time.time()
chunks = search_chunks("xyzabc qwerty asdfgh")
elapsed = (time.time() - start) * 1000

print(f"\nQuery: 'xyzabc qwerty asdfgh'")
print(f"Chunks Retrieved: {len(chunks)}")
print(f"Search Time: {elapsed:.1f}ms")

is_gibberish_rejected = not chunks or (chunks and get_text(chunks[0]) == "No relevant content found in PDFs")
if is_gibberish_rejected:
    print("✅ RESULT: CORRECTLY REJECTED")
    if not chunks:
        print("   (Empty result)")
else:
    print("❌ RESULT: WRONG")

test3_pass = is_gibberish_rejected

# Summary
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)
print(f"Test 1 (IPL - Reject): {'✅ PASS' if test1_pass else '❌ FAIL'}")
print(f"Test 2 (OS - Accept): {'✅ PASS' if test2_pass else '❌ FAIL'}")
print(f"Test 3 (Gibberish - Reject): {'✅ PASS' if test3_pass else '❌ FAIL'}")

all_pass = test1_pass and test2_pass and test3_pass
print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")
print("="*70)
