import os
import sys
from pathlib import Path

import fitz
import django
from django.core.files.base import ContentFile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")
os.chdir(ROOT)
django.setup()

from accounts.models import User  # noqa: E402
from courses.models import Subject, Unit  # noqa: E402
from chatbot.models import ReferencePDF, PDFPageChunk, ChunkEmbedding  # noqa: E402
from chatbot.services.pdf_processor import process_pdf  # noqa: E402
from chatbot.services.chunk_service import create_chunks_for_pdf  # noqa: E402
from chatbot.services.embedding_service import store_chunk_embeddings  # noqa: E402
from chatbot.services.faiss_service import upsert_index_for_chunk_ids  # noqa: E402
from chatbot.services.search_service import search_chunks  # noqa: E402
from chatbot.services.answer_service import generate_answer, NO_RESULT_MESSAGE  # noqa: E402


SEED_DATA = {
    "20CS4T01": {
        "unit_number": 2,
        "unit_title": "Unit 2: Process Scheduling and Deadlocks",
        "text": (
            "Operating Systems topic coverage: Process scheduling allocates CPU time among multiple processes. "
            "Scheduling algorithms include FCFS, SJF, Priority scheduling and Round Robin. Process scheduling "
            "improves throughput, waiting time and response time. Deadlocks occur when processes wait forever due "
            "to mutual exclusion, hold-and-wait, no preemption and circular wait. Deadlock handling uses prevention, "
            "avoidance (Banker's algorithm), detection and recovery."
        ),
    },
    "20CS2T01": {
        "unit_number": 2,
        "unit_title": "Unit 2: Stack Queue Searching and Recursion",
        "text": (
            "Data Structures topic coverage: Stack follows LIFO with push and pop operations. Queue follows FIFO "
            "with enqueue and dequeue operations. Stack vs Queue comparison is based on insertion/deletion rules, "
            "memory usage and applications. Searching techniques include linear search and binary search. "
            "Recursion solves a problem by calling the same function on smaller input; base case and recursive case "
            "are required for correctness."
        ),
    },
    "20CS3T04": {
        "unit_number": 2,
        "unit_title": "Unit 2: Transactions Indexing and Normalization",
        "text": (
            "DBMS topic coverage: Transactions follow ACID properties (Atomicity, Consistency, Isolation, Durability). "
            "Concurrency control uses locking and serializability. Indexing improves query performance using primary, "
            "secondary and B-tree indexes. Database normalization reduces redundancy and anomalies using 1NF, 2NF, "
            "3NF and BCNF. Database normalization is essential for clean schema design and reliable transaction processing."
        ),
    },
}


def create_pdf_bytes(title: str, body: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), f"{title}\n\n{body}")
    data = doc.tobytes()
    doc.close()
    return data


def ensure_pdf(subject, user, title, body):
    pdf, _ = ReferencePDF.objects.get_or_create(
        subject=subject,
        title=title,
        defaults={
            "uploaded_by": user,
            "status": ReferencePDF.Status.APPROVED,
            "is_syllabus_reference": True,
            "is_active": True,
        },
    )

    content = ContentFile(create_pdf_bytes(title, body), name=f"seed_{subject.subject_code.lower()}.pdf")
    pdf.file.save(content.name, content, save=False)
    pdf.uploaded_by = user
    pdf.status = ReferencePDF.Status.APPROVED
    pdf.is_syllabus_reference = True
    pdf.is_active = True
    pdf.processing_status = ReferencePDF.ProcessingStatus.PENDING
    pdf.processing_error = ""
    pdf.save()
    return pdf


def main():
    user = User.objects.filter(is_active=True).order_by("id").first()
    if user is None:
        raise RuntimeError("No active user found for uploaded_by")

    seeded = []
    total_chunks = 0
    total_embeddings = 0

    for code, payload in SEED_DATA.items():
        subject = Subject.objects.get(subject_code=code, is_active=True, semester__is_active=True)

        unit, _ = Unit.objects.get_or_create(
            subject=subject,
            unit_number=payload["unit_number"],
            defaults={"title": payload["unit_title"], "content": payload["text"], "is_active": True},
        )
        unit.title = payload["unit_title"]
        unit.content = payload["text"]
        unit.is_active = True
        unit.save(update_fields=["title", "content", "is_active"])

        pdf_title = f"Seed Minimal Content {code}"
        pdf = ensure_pdf(subject, user, pdf_title, payload["text"])
        process_pdf(pdf, replace_existing=True)
        chunks = create_chunks_for_pdf(pdf, text=pdf.extracted_text)

        ChunkEmbedding.objects.filter(chunk__reference_pdf=pdf).delete()
        stored = store_chunk_embeddings(chunks)
        upsert_index_for_chunk_ids([chunk.id for chunk in chunks])

        chunk_count = PDFPageChunk.objects.filter(reference_pdf=pdf).count()
        emb_count = ChunkEmbedding.objects.filter(chunk__reference_pdf=pdf).count()
        total_chunks += chunk_count
        total_embeddings += emb_count

        seeded.append(
            {
                "subject_code": code,
                "unit_number": payload["unit_number"],
                "chunk_count": chunk_count,
                "embedding_count": emb_count,
                "stored_now": stored,
            }
        )

    queries = [
        "What is Database Normalization?",
        "Compare database normalization and recursion with practical differences.",
        "What is process scheduling and deadlock handling?",
        "Stack vs Queue and searching methods",
        "Explain transactions and indexing in DBMS",
    ]
    query_results = []
    for query in queries:
        chunks = search_chunks(query, regulation="MIC20", branch="CSE", scope="global")
        answer = generate_answer(query, chunks)
        markdown = (answer.get("markdown") or "").lower()
        accepted = NO_RESULT_MESSAGE.lower() not in markdown
        query_results.append({"query": query, "chunks": len(chunks), "accepted": accepted})

    print(
        {
            "seeded": seeded,
            "total_seed_chunks": total_chunks,
            "total_seed_embeddings": total_embeddings,
            "query_results": query_results,
        }
    )


if __name__ == "__main__":
    main()
