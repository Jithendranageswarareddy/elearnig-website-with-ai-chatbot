from django.core.management.base import BaseCommand

from chatbot.services.embedding_service import embed_query
from chatbot.services.faiss_service import load_index, search_index


class Command(BaseCommand):
    help = "Embed a sample query and test FAISS vector retrieval."

    def add_arguments(self, parser):
        parser.add_argument(
            "--query",
            default="Explain encapsulation in object oriented programming.",
            help="Query text to embed and search through the FAISS index",
        )
        parser.add_argument("--top-k", type=int, default=5)

    def handle(self, *args, **options):
        query = (options["query"] or "").strip()
        top_k = max(1, int(options["top_k"]))

        index, meta = load_index()
        if index is None or meta is None:
            self.stdout.write(self.style.WARNING("FAISS index is unavailable."))
            return
        if not meta.get("vector_count"):
            self.stdout.write(self.style.WARNING("FAISS index is empty."))
            return

        query_vector = embed_query(query)
        results = search_index(query_vector, top_k=top_k)

        self.stdout.write(
            " | ".join(
                [
                    f"query={query}",
                    f"top_k={top_k}",
                    f"index_dimension={meta.get('dimension', 0)}",
                    f"vector_count={meta.get('vector_count', 0)}",
                ]
            )
        )
        if not results:
            self.stdout.write(self.style.WARNING("No FAISS results returned."))
            return

        for item in results:
            self.stdout.write(
                " | ".join(
                    [
                        f"chunk_id={item['chunk_id']}",
                        f"score={round(item['score'], 6)}",
                    ]
                )
            )