import os
import sys
from pathlib import Path

import django


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")
os.chdir(ROOT)
django.setup()

from accounts.models import User  # noqa: E402
from courses.models import Subject, Unit  # noqa: E402
from chatbot.models import ReferencePDF, PDFPageChunk, ChunkEmbedding  # noqa: E402
from chatbot.services.embedding_service import store_chunk_embeddings  # noqa: E402
from chatbot.services.faiss_service import upsert_index_for_chunk_ids  # noqa: E402
from chatbot.services.search_service import search_chunks  # noqa: E402
from chatbot.services.answer_service import generate_answer, NO_RESULT_MESSAGE  # noqa: E402


SEED_DATA = {
    "20CS4T01": {
        "unit_number": 2,
        "unit_title": "Unit 2: Process Scheduling and Deadlocks",
        "text": (
            "Operating Systems: Process scheduling is the method used by the operating system to allocate CPU time to multiple processes. "
            "Scheduling algorithms include FCFS, SJF, Priority and Round Robin. Process scheduling improves throughput, waiting time and response time. "
            "Deadlocks happen when mutual exclusion, hold and wait, no preemption, and circular wait occur together. "
            "Deadlock handling includes prevention, avoidance, detection and recovery."
        ),
    },
    "20CS2T01": {
        "unit_number": 2,
        "unit_title": "Unit 2: Stack Queue Searching and Recursion",
        "text": (
            "Data Structures: Stack follows LIFO using push and pop operations. Queue follows FIFO using enqueue and dequeue operations. "
            "Stack vs Queue is a core comparison in data structures based on insertion and deletion order and typical applications. "
            "Searching methods include linear search and binary search. Recursion solves a problem by reducing it into smaller subproblems with base case and recursive case."
        ),
    },
    "20CS3T04": {
        "unit_number": 2,
        "unit_title": "Unit 2: Transactions Indexing and Normalization",
        "text": (
            "DBMS: Transactions follow ACID properties: Atomicity, Consistency, Isolation and Durability. "
            "Indexing improves query performance using primary index, secondary index and B-tree index. "
            "Database normalization reduces data redundancy and anomalies through 1NF, 2NF, 3NF and BCNF. "
            "Database normalization is important for schema design, integrity and efficient transaction processing."
        ),
    },
}


def ensure_pdf(subject, user, title):
    pdf, _ = ReferencePDF.objects.get_or_create(
        subject=subject,
        title=title,
        defaults={
            "uploaded_by": user,
            "file": "pdfs/seed_reference.pdf",
            "status": ReferencePDF.Status.APPROVED,
            "is_syllabus_reference": True,
            "is_active": True,
            "processing_status": ReferencePDF.ProcessingStatus.READY,
            "extracted_text": "",
        },
    )
    changed = False
    if not pdf.file:
        pdf.file = "pdfs/seed_reference.pdf"
        changed = True
    if pdf.uploaded_by_id != user.id:
        pdf.uploaded_by = user
        changed = True
    if pdf.status != ReferencePDF.Status.APPROVED:
        pdf.status = ReferencePDF.Status.APPROVED
        changed = True
    if not pdf.is_syllabus_reference:
        pdf.is_syllabus_reference = True
        changed = True
    if not pdf.is_active:
        pdf.is_active = True
        changed = True
    if pdf.processing_status != ReferencePDF.ProcessingStatus.READY:
        pdf.processing_status = ReferencePDF.ProcessingStatus.READY
        changed = True
    if changed:
        pdf.save()
    return pdf


def main():
    user = User.objects.filter(is_active=True).order_by("id").first()
    if user is None:
        raise RuntimeError("No active user found")

    seeded = []

    for code, payload in SEED_DATA.items():
        subject = Subject.objects.get(subject_code=code, is_active=True, semester__is_active=True)

        unit, _ = Unit.objects.get_or_create(
            subject=subject,
            unit_number=payload["unit_number"],
            defaults={
                "title": payload["unit_title"],
                "content": payload["text"],
                "is_active": True,
            },
        )
        unit.title = payload["unit_title"]
        unit.content = payload["text"]
        unit.is_active = True
        unit.save(update_fields=["title", "content", "is_active"])

        pdf = ensure_pdf(subject, user, f"Seed Minimal Content {code}")
        pdf.extracted_text = payload["text"]
        pdf.processing_error = ""
        pdf.save(update_fields=["extracted_text", "processing_error"])

        PDFPageChunk.objects.filter(reference_pdf=pdf).delete()
        chunk = PDFPageChunk.objects.create(
            reference_pdf=pdf,
            page_number=1,
            chunk_index=0,
            text_content=payload["text"],
            metadata={"source": "manual_seed", "subject_code": code, "unit_number": payload["unit_number"]},
        )
        pdf.chunk_count = PDFPageChunk.objects.filter(reference_pdf=pdf).count()
        pdf.save(update_fields=["chunk_count"])

        ChunkEmbedding.objects.filter(chunk=chunk).delete()
        stored = store_chunk_embeddings([chunk])
        upsert_index_for_chunk_ids([chunk.id])

        seeded.append({
            "subject_code": code,
            "chunk_id": chunk.id,
            "stored_embeddings": stored,
        })

    test_queries = [
        "What is Database Normalization?",
        "Compare database normalization and recursion with practical differences.",
        "What is process scheduling?",
        "Stack vs Queue",
    ]

    tests = []
    for query in test_queries:
        chunks = search_chunks(query, regulation="MIC20", branch="CSE", scope="global")
        answer = generate_answer(query, chunks)
        markdown = (answer.get("markdown") or "").lower()
        accepted = NO_RESULT_MESSAGE.lower() not in markdown
        tests.append({"query": query, "accepted": accepted, "count": len(chunks)})

    print({"seeded": seeded, "tests": tests})


if __name__ == "__main__":
    main()
