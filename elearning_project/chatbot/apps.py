import threading

from django.apps import AppConfig


_WARMUP_STARTED = False
_WARMUP_LOCK = threading.Lock()


def _warmup_retrieval_stack():
    from .services.embedding_service import embed_query
    from .services.faiss_service import load_index

    load_index()
    embed_query("test")


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'

    def ready(self):
        global _WARMUP_STARTED
        with _WARMUP_LOCK:
            if _WARMUP_STARTED:
                return
            _WARMUP_STARTED = True

        threading.Thread(target=_warmup_retrieval_stack, daemon=True).start()
