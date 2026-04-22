import json
import time
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from chatbot.models import ChunkEmbedding, PDFPageChunk
from chatbot.services.embedding_service import embed_texts, get_embedding_backend_name, store_chunk_embeddings
from chatbot.services.faiss_service import build_index
from chatbot.services.search_service import _base_queryset


class Command(BaseCommand):
    help = "Rebuild all chunk embeddings using the active embedding backend in batches."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=128)
        parser.add_argument(
            "--output",
            default=str(Path(settings.BASE_DIR) / "test_logs" / "embedding_reindex_report.json"),
            help="Path for embedding reindex JSON report",
        )

    def handle(self, *args, **options):
        batch_size = max(1, int(options["batch_size"]))
        started_at = time.perf_counter()

        target_dimension = self._detect_target_dimension()
        existing_total = ChunkEmbedding.objects.count()
        before_coverage = self._active_chunk_embedding_coverage()
        existing_dimension_counts = self._dimension_counts()
        invalid_dimension_counts = {
            dimension: count
            for dimension, count in existing_dimension_counts.items()
            if dimension != target_dimension
        }
        invalid_total = sum(invalid_dimension_counts.values())

        self.stdout.write(
            " | ".join(
                [
                    f"target_dimension={target_dimension}",
                    f"existing_embeddings={existing_total}",
                    f"invalid_embeddings={invalid_total}",
                    f"active_coverage_before={before_coverage['coverage_percent']}%",
                ]
            )
        )
        if existing_dimension_counts:
            self.stdout.write(f"existing_dimension_counts={json.dumps(existing_dimension_counts, sort_keys=True)}")

        if invalid_total > 0:
            self.stdout.write(
                self.style.WARNING(
                    "Stored embeddings do not match the active model dimension and are being treated as invalid."
                )
            )

        deleted_count, _ = ChunkEmbedding.objects.all().delete()
        self.stdout.write(self.style.WARNING(f"Deleted existing ChunkEmbedding rows: {deleted_count}"))

        total_chunks = PDFPageChunk.objects.count()
        processed_chunks = 0
        batch_reports = []
        model_name = get_embedding_backend_name()

        self.stdout.write(f"total_chunks={total_chunks} | batch_size={batch_size} | model_name={model_name}")

        current_batch = []
        batch_number = 0
        for chunk in PDFPageChunk.objects.only("id", "text_content").order_by("id").iterator(chunk_size=batch_size):
            if not chunk.id or not (chunk.text_content or "").strip():
                continue
            current_batch.append(chunk)
            if len(current_batch) < batch_size:
                continue
            batch_number += 1
            report = self._process_batch(current_batch, batch_number, processed_chunks, total_chunks)
            processed_chunks += report["stored_count"]
            batch_reports.append(report)
            current_batch = []

        if current_batch:
            batch_number += 1
            report = self._process_batch(current_batch, batch_number, processed_chunks, total_chunks)
            processed_chunks += report["stored_count"]
            batch_reports.append(report)

        final_total = ChunkEmbedding.objects.count()
        after_coverage = self._active_chunk_embedding_coverage()
        faiss_meta = build_index()
        final_dimension_counts = self._dimension_counts()
        valid_total = sum(count for dimension, count in final_dimension_counts.items() if dimension == target_dimension)
        mismatched_total = final_total - valid_total
        elapsed_seconds = round(time.perf_counter() - started_at, 2)

        report = {
            "target_dimension": target_dimension,
            "model_name": model_name,
            "batch_size": batch_size,
            "before": {
                "embedding_count": existing_total,
                "active_chunk_embedding_coverage": before_coverage,
                "dimension_counts": existing_dimension_counts,
                "invalid_dimension_counts": invalid_dimension_counts,
            },
            "after": {
                "embedding_count": final_total,
                "active_chunk_embedding_coverage": after_coverage,
                "dimension_counts": final_dimension_counts,
                "valid_embeddings": valid_total,
                "mismatched_embeddings": mismatched_total,
                "faiss": faiss_meta,
            },
            "processing": {
                "total_chunks": total_chunks,
                "processed_chunks": processed_chunks,
                "batch_count": len(batch_reports),
                "elapsed_seconds": elapsed_seconds,
            },
            "batch_reports": batch_reports,
        }

        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        status_style = self.style.SUCCESS if mismatched_total == 0 and final_total == processed_chunks else self.style.WARNING
        self.stdout.write(status_style(f"Embedding reindex report written to {output_path}"))
        self.stdout.write(
            " | ".join(
                [
                    f"total_chunks={total_chunks}",
                    f"processed_chunks={processed_chunks}",
                    f"final_embeddings={final_total}",
                    f"active_coverage_after={after_coverage['coverage_percent']}%",
                    f"target_dimension={target_dimension}",
                    f"mismatched_embeddings={mismatched_total}",
                    f"faiss_vectors={faiss_meta.get('vector_count', 0)}",
                    f"elapsed_seconds={elapsed_seconds}",
                ]
            )
        )

    def _active_chunk_embedding_coverage(self):
        active_chunk_ids = list(_base_queryset().values_list("id", flat=True))
        if not active_chunk_ids:
            return {
                "active_chunks": 0,
                "embedded_active_chunks": 0,
                "coverage_percent": 0.0,
            }
        embedded = ChunkEmbedding.objects.filter(chunk_id__in=active_chunk_ids).values_list("chunk_id", flat=True).distinct().count()
        coverage = round((embedded / len(active_chunk_ids)) * 100, 2)
        return {
            "active_chunks": len(active_chunk_ids),
            "embedded_active_chunks": embedded,
            "coverage_percent": coverage,
        }

    def _detect_target_dimension(self):
        sample_vector = embed_texts(["dimension probe"])[0]
        return len(sample_vector or [])

    def _dimension_counts(self):
        counts = Counter()
        for embedding in ChunkEmbedding.objects.only("embedding_vector").iterator(chunk_size=512):
            counts[len(embedding.embedding_vector or [])] += 1
        return dict(sorted(counts.items()))

    def _process_batch(self, chunks, batch_number, processed_so_far, total_chunks):
        batch_started = time.perf_counter()
        stored_count = store_chunk_embeddings(chunks)
        batch_elapsed = round(time.perf_counter() - batch_started, 2)
        processed_total = processed_so_far + stored_count
        self.stdout.write(
            " | ".join(
                [
                    f"batch={batch_number}",
                    f"batch_size={len(chunks)}",
                    f"stored={stored_count}",
                    f"processed_chunks={processed_total}/{total_chunks}",
                    f"batch_seconds={batch_elapsed}",
                ]
            )
        )
        return {
            "batch": batch_number,
            "batch_size": len(chunks),
            "stored_count": stored_count,
            "processed_total": processed_total,
            "total_chunks": total_chunks,
            "batch_seconds": batch_elapsed,
        }