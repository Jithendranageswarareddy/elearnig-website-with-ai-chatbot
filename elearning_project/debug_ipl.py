#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning_project.settings')
import django
django.setup()

from chatbot.services.search_service import search_chunks

query = "What is IPL cricket?"
print(f"\nTesting query: '{query}'")
print("="*70)

chunks = search_chunks(query)
print(f"\nNumber of chunks: {len(chunks)}")

for i, chunk in enumerate(chunks):
    print(f"\nChunk {i}:")
    print(f"  Type: {type(chunk)}")
    print(f"  Has text_content attr: {hasattr(chunk, 'text_content')}")
    
    if hasattr(chunk, 'text_content'):
        text = chunk.text_content
        print(f"  text_content: '{text}'")
        print(f"  Is fallback: {text == 'No relevant content found in PDFs'}")
    elif isinstance(chunk, dict):
        text = chunk.get('text_content', 'N/A')
        print(f"  text_content: '{text}'")
        print(f"  Is fallback: {text == 'No relevant content found in PDFs'}")
    else:
        print(f"  Cannot access text_content")
        print(f"  Dir: {dir(chunk)[:5]}")
    
    if hasattr(chunk, 'retrieval_metadata'):
        metadata = chunk.retrieval_metadata
        print(f"  metadata: {metadata}")
