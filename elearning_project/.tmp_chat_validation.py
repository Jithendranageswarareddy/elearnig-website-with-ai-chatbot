import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")
django.setup()

from chatbot.services.search_service import search_chunks
from chatbot.services.answer_service import generate_answer

queries = [
    "What is OOP",
    "Process scheduling",
    "Transport layer",
]

for q in queries:
    chunks = search_chunks(q, limit=5)
    result = generate_answer(q, chunks, recent_questions=[])
    print("=" * 70)
    print("Q:", q)
    print("confidence:", result.get("confidence_label"), result.get("confidence_score"))
    print("answer_from:", result.get("answer_from"))
    print("markdown:")
    print(result.get("markdown", "").strip())
    print()
