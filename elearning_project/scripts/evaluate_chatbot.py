import argparse
import os
import sys
import time
import tracemalloc
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_project.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from accounts.models import User  # noqa: E402
from chatbot.models import PDFPageChunk, ReferencePDF  # noqa: E402
from chatbot.services.embedding_service import (  # noqa: E402
    get_embedding_backend_name,
    store_chunk_embeddings,
)
try:
    from chatbot.services.experience_service import ARCHITECTURE_DIAGRAM  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover
    ARCHITECTURE_DIAGRAM = "Text extraction -> chunking -> embeddings -> FAISS retrieval -> answer generation"
from chatbot.services.answer_service import generate_answer  # noqa: E402
from chatbot.services.search_service import (  # noqa: E402
    _base_queryset,
    _candidate_rows,
    _query_terms,
    search_chunks,
)
from courses.models import Semester, Subject  # noqa: E402


def _batched(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def _build_benchmark_cases(pdf_count, chunks_per_page, question_count):
    families = [
        ("queue operations", "design layout of queue operations"),
        ("stack workflow", "design layout of stack workflow"),
        ("tree hierarchy", "design layout of tree hierarchy"),
        ("graph traversal", "design layout of graph traversal"),
        ("sorting pipeline", "design layout of sorting pipeline"),
    ]
    cases = []
    start_pdf = max(pdf_count - question_count + 1, 1)
    for index in range(question_count):
        family_text, query_text = families[index % len(families)]
        pdf_number = start_pdf + index
        page_number = 3 + (index % 15)
        chunk_index = index % chunks_per_page
        cases.append(
            {
                "id": index + 1,
                "pdf_number": pdf_number,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "family_text": family_text,
                "expected_concepts": [family_text.title()],
                "query": f"Explain the {query_text} for syllabus case {index + 1}",
            }
        )
    return cases


def _create_benchmark_dataset(pdf_count, pages_per_pdf, chunks_per_page, question_count):
    faculty = User.objects.create_user(
        email="benchmark-faculty@example.com",
        password="pass12345",
        name="Benchmark Faculty",
        role=User.Role.FACULTY,
    )
    semester = Semester.objects.create(
        number=8,
        regulation="BENCHMARK-2026",
        description="Benchmark semester",
        is_active=True,
    )
    subject = Subject.objects.create(
        semester=semester,
        subject_code="BENCH101",
        name="Benchmark Retrieval",
        description="Synthetic benchmark subject",
        is_active=True,
    )

    cases = _build_benchmark_cases(pdf_count, chunks_per_page, question_count)
    case_lookup = {
        (case["pdf_number"], case["page_number"], case["chunk_index"]): case
        for case in cases
    }

    reference_pdfs = []
    for pdf_number in range(1, pdf_count + 1):
        reference_pdfs.append(
            ReferencePDF(
                subject=subject,
                uploaded_by=faculty,
                title=f"Benchmark PDF {pdf_number}",
                file=f"pdfs/benchmark_{pdf_number}.pdf",
                extracted_text="",
                is_syllabus_reference=True,
                status=ReferencePDF.Status.APPROVED,
                is_active=True,
                processing_status=ReferencePDF.ProcessingStatus.READY,
            )
        )
    ReferencePDF.objects.bulk_create(reference_pdfs)
    reference_pdfs = list(
        ReferencePDF.objects.filter(subject=subject).order_by("id")
    )

    chunk_rows = []
    for pdf_number, reference_pdf in enumerate(reference_pdfs, start=1):
        for page_number in range(1, pages_per_pdf + 1):
            for chunk_index in range(chunks_per_page):
                case = case_lookup.get((pdf_number, page_number, chunk_index))
                if case:
                    text = (
                        f"This architecture structure architecture section explains {case['family_text']} for syllabus case {case['id']}. "
                        f"The figure includes a flowchart, design layout, and structure map for {case['family_text']} and the academic workflow. "
                        f"Example: syllabus case {case['id']} applies {case['family_text']} in a laboratory exercise."
                    )
                else:
                    text = (
                        f"Common syllabus content for pdf {pdf_number} page {page_number} chunk {chunk_index}. "
                        "This paragraph discusses queue operations, stack workflow, tree hierarchy, "
                        "graph traversal, and sorting pipeline in general terms for coursework review."
                    )
                chunk_rows.append(
                    PDFPageChunk(
                        reference_pdf=reference_pdf,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        text_content=text,
                        metadata={
                            "source": "benchmark",
                            "paragraph_index": chunk_index,
                            "token_count": len(text.split()),
                        },
                    )
                )

    for batch in _batched(chunk_rows, 1000):
        PDFPageChunk.objects.bulk_create(batch)

    all_chunks = list(
        PDFPageChunk.objects.filter(reference_pdf__subject=subject).only("id", "text_content")
    )
    for batch in _batched(all_chunks, 256):
        store_chunk_embeddings(batch)

    pdf_number_by_id = {
        reference_pdf.id: index
        for index, reference_pdf in enumerate(reference_pdfs, start=1)
    }
    return subject, cases, pdf_number_by_id


def _baseline_tfidf_results(question, subject):
    rows = _candidate_rows(_base_queryset(subject=subject), _query_terms(question))
    ranked_rows = [
        (row, float(row.get("keyword_score", 0.0)))
        for row in rows
        if float(row.get("keyword_score", 0.0)) > 0
    ]
    return ranked_rows[:5]


def _parse_args():
    parser = argparse.ArgumentParser(description="Evaluate syllabus chatbot retrieval.")
    parser.add_argument("--pdfs", type=int, default=80)
    parser.add_argument("--pages", type=int, default=25)
    parser.add_argument("--chunks", type=int, default=5)
    parser.add_argument("--questions", type=int, default=20)
    parser.add_argument(
        "--report",
        type=str,
        default=str(BASE_DIR / "reports" / "final_benchmark_report.md"),
    )
    return parser.parse_args()


def _write_report(report_path, metrics):
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Final Benchmark Report",
        "",
        f"- Embedding backend: `{metrics['embedding_backend']}`",
        f"- Corpus: `{metrics['pdfs']} PDFs x {metrics['pages']} pages x {metrics['chunks']} chunks`",
        f"- Questions: `{metrics['questions']}`",
        f"- TF-IDF top-1 accuracy: `{metrics['tfidf_top1']:.2%}`",
        f"- Hybrid top-1 accuracy: `{metrics['hybrid_top1']:.2%}`",
        f"- TF-IDF top-5 recall: `{metrics['tfidf_top5']:.2%}`",
        f"- Hybrid top-5 recall: `{metrics['hybrid_top5']:.2%}`",
        f"- Average retrieval latency: `{metrics['avg_retrieval_ms']:.2f} ms`",
        f"- P95 retrieval latency: `{metrics['p95_retrieval_ms']:.2f} ms`",
        f"- Average response build latency: `{metrics['avg_response_ms']:.2f} ms`",
        f"- Concept coverage: `{metrics['concept_coverage']:.2%}`",
        f"- Response quality pass rate: `{metrics['response_quality']:.2%}`",
        f"- Peak traced memory: `{metrics['peak_memory_mb']:.2f} MB`",
        "",
        "## Architecture Diagram",
        "",
        "```text",
        ARCHITECTURE_DIAGRAM.rstrip(),
        "```",
        "",
        "## Notes",
        "",
        "- Retrieval remains restricted to approved syllabus PDFs.",
        "- The benchmark corpus is synthetic and generated inside a rollback-only transaction.",
        "- Semantic ranking quality depends on the embedding backend available at runtime.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    args = _parse_args()
    tracemalloc.start()
    with transaction.atomic():
        subject, cases, pdf_number_by_id = _create_benchmark_dataset(
            pdf_count=args.pdfs,
            pages_per_pdf=args.pages,
            chunks_per_page=args.chunks,
            question_count=args.questions,
        )

        tfidf_top1_hits = 0
        hybrid_top1_hits = 0
        tfidf_top5_hits = 0
        hybrid_top5_hits = 0
        concept_coverage_hits = 0
        response_quality_hits = 0
        search_latencies = []
        response_latencies = []

        for case in cases:
            expected = (case["pdf_number"], case["page_number"], case["chunk_index"])

            baseline_rows = _baseline_tfidf_results(case["query"], subject)
            baseline_hits = [
                (
                    pdf_number_by_id.get(row["reference_pdf_id"]),
                    row["page_number"],
                    row["chunk_index"],
                )
                for row, _score in baseline_rows
            ]

            if baseline_hits and baseline_hits[0] == expected:
                tfidf_top1_hits += 1
            if expected in baseline_hits:
                tfidf_top5_hits += 1

            search_started = time.perf_counter()
            chunks = search_chunks(case["query"], subject=subject)
            search_latencies.append((time.perf_counter() - search_started) * 1000)

            hybrid_hits = [
                (
                    pdf_number_by_id.get(chunk.reference_pdf_id),
                    chunk.page_number,
                    chunk.chunk_index,
                )
                for chunk in chunks
            ]
            if hybrid_hits and hybrid_hits[0] == expected:
                hybrid_top1_hits += 1
            if expected in hybrid_hits:
                hybrid_top5_hits += 1

            response_started = time.perf_counter()
            response_data = generate_answer(case["query"], chunks)
            response_latencies.append((time.perf_counter() - response_started) * 1000)
            if response_data:
                response_concepts = {
                    concept.lower() for concept in response_data.get("related_concepts", [])
                }
                if any(expected.lower() in response_concepts for expected in case["expected_concepts"]):
                    concept_coverage_hits += 1
                if response_data.get("markdown") and response_data.get("references"):
                    response_quality_hits += 1

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        metrics = {
            "embedding_backend": get_embedding_backend_name(),
            "pdfs": args.pdfs,
            "pages": args.pages,
            "chunks": args.chunks,
            "questions": args.questions,
            "tfidf_top1": tfidf_top1_hits / args.questions,
            "hybrid_top1": hybrid_top1_hits / args.questions,
            "tfidf_top5": tfidf_top5_hits / args.questions,
            "hybrid_top5": hybrid_top5_hits / args.questions,
            "avg_retrieval_ms": sum(search_latencies) / len(search_latencies),
            "p95_retrieval_ms": sorted(search_latencies)[int(len(search_latencies) * 0.95) - 1],
            "avg_response_ms": sum(response_latencies) / len(response_latencies),
            "concept_coverage": concept_coverage_hits / args.questions,
            "response_quality": response_quality_hits / args.questions,
            "current_memory_mb": current_mem / (1024 * 1024),
            "peak_memory_mb": peak_mem / (1024 * 1024),
        }

        print(f"Embedding backend: {metrics['embedding_backend']}")
        print(f"Corpus: {args.pdfs} PDFs x {args.pages} pages x {args.chunks} chunks")
        print(f"Questions: {args.questions}")
        print(f"TF-IDF top-1 accuracy: {metrics['tfidf_top1']:.2%}")
        print(f"Hybrid top-1 accuracy: {metrics['hybrid_top1']:.2%}")
        print(f"TF-IDF top-5 recall: {metrics['tfidf_top5']:.2%}")
        print(f"Hybrid top-5 recall: {metrics['hybrid_top5']:.2%}")
        print(f"Average retrieval latency: {metrics['avg_retrieval_ms']:.2f} ms")
        print(f"P95 retrieval latency: {metrics['p95_retrieval_ms']:.2f} ms")
        print(f"Average response build latency: {metrics['avg_response_ms']:.2f} ms")
        print(f"Concept coverage: {metrics['concept_coverage']:.2%}")
        print(f"Response quality pass rate: {metrics['response_quality']:.2%}")
        print(f"Current traced memory: {metrics['current_memory_mb']:.2f} MB")
        print(f"Peak traced memory: {metrics['peak_memory_mb']:.2f} MB")

        report_path = _write_report(args.report, metrics)
        print(f"Benchmark report: {report_path}")

        transaction.set_rollback(True)
    tracemalloc.stop()


if __name__ == "__main__":
    main()
