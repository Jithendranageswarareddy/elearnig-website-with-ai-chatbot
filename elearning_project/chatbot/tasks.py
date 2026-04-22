from accounts.audit import log_system_event

from .models import ReferencePDF
from .services.chunk_service import create_chunks_for_pdf
from .services.embedding_service import store_chunk_embeddings
from .services.faiss_service import upsert_index_for_chunk_ids
from .services.pdf_processor import process_pdf

try:
    from celery import shared_task

    CELERY_AVAILABLE = True
except Exception as e:  # pragma: no cover - optional dependency at runtime
    print("ERROR:", str(e))
    CELERY_AVAILABLE = False

    class _FallbackTask:
        def __init__(self, func):
            self.func = func
            self.__name__ = getattr(func, "__name__", "task")

        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)

        def delay(self, *args, **kwargs):
            return self.func(*args, **kwargs)

    def shared_task(*task_args, **task_kwargs):  # pragma: no cover - runtime fallback
        def decorator(func):
            return _FallbackTask(func)

        if task_args and callable(task_args[0]) and not task_kwargs:
            return decorator(task_args[0])
        return decorator


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def process_reference_pdf_task(reference_pdf_id, replace_existing=True):
    try:
        reference_pdf = ReferencePDF.objects.select_related("uploaded_by", "subject").get(id=reference_pdf_id)
    except ReferencePDF.DoesNotExist:
        return {"status": "missing", "reference_pdf_id": reference_pdf_id}

    try:
        process_pdf(reference_pdf, replace_existing=replace_existing)
        chunks = create_chunks_for_pdf(reference_pdf, reference_pdf.extracted_text or "")
        store_chunk_embeddings(chunks)
        upsert_index_for_chunk_ids([chunk.id for chunk in chunks])
        reference_pdf.chunk_count = len(chunks)
        reference_pdf.save(update_fields=["chunk_count"])
    except Exception as exc:
        log_system_event(
            user=reference_pdf.uploaded_by,
            action_type="UPLOAD",
            object_type="ReferencePDF",
            object_id=reference_pdf.id,
            metadata={"event": "process_reference_pdf_failed", "error": str(exc)[:500]},
        )
        raise

    log_system_event(
        user=reference_pdf.uploaded_by,
        action_type="UPLOAD",
        object_type="ReferencePDF",
        object_id=reference_pdf.id,
        metadata={
            "event": "process_reference_pdf_ready",
            "chunk_count": reference_pdf.chunk_count,
            "diagram_count": reference_pdf.diagram_count,
        },
    )
    return {
        "status": reference_pdf.processing_status,
        "reference_pdf_id": reference_pdf.id,
        "chunk_count": reference_pdf.chunk_count,
        "diagram_count": reference_pdf.diagram_count,
    }
