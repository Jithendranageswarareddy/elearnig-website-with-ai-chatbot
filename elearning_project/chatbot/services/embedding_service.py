import hashlib
import math
import re
from functools import lru_cache

from django.conf import settings

from ..models import ChunkEmbedding, PDFPageChunk

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:  # pragma: no cover - optional dependency at runtime
    print("ERROR:", str(e))
    SentenceTransformer = None


DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
FALLBACK_DIMENSION = 192
VECTOR_DECIMALS = 6
BATCH_SIZE = 64

SEMANTIC_ALIASES = {
    "architecture": "architecture",
    "architectural": "architecture",
    "design": "architecture",
    "layout": "architecture",
    "structure": "architecture",
    "structures": "architecture",
    "diagram": "diagram",
    "diagrams": "diagram",
    "figure": "diagram",
    "figures": "diagram",
    "flow": "flowchart",
    "flowchart": "flowchart",
    "workflow": "flowchart",
    "pipeline": "flowchart",
    "process": "flowchart",
    "graph": "graph",
    "graphs": "graph",
    "network": "graph",
    "topology": "graph",
    "queue": "queue",
    "queues": "queue",
    "enqueue": "queue",
    "dequeue": "queue",
    "fifo": "queue",
    "stack": "stack",
    "stacks": "stack",
    "push": "stack",
    "pop": "stack",
    "lifo": "stack",
    "tree": "tree",
    "trees": "tree",
    "hierarchy": "tree",
    "root": "tree",
    "breadth": "bfs",
    "level": "bfs",
    "bfs": "bfs",
    "depth": "dfs",
    "dfs": "dfs",
    "search": "search",
    "traversal": "search",
    "exploration": "search",
    "sort": "sorting",
    "sorting": "sorting",
    "sorted": "sorting",
    "arrange": "sorting",
    "ordering": "sorting",
}

NOISE_PATTERNS = [
    r"(?i)stratford\s+college\s+london",
    r"(?i)dfes\s+registered\s+independent\s+school",
    r"(?i)\b(?:tel|phone)\s*:\s*[+\d\-\s()]{6,}",
    r"(?i)\bemail\s*:\s*\S+",
]


def _model_name():
    return DEFAULT_MODEL_NAME


def _fallback_dimension():
    return getattr(settings, "CHATBOT_FALLBACK_EMBEDDING_DIM", FALLBACK_DIMENSION)


def _normalize_token(token):
    token = token.lower()
    if len(token) <= 3:
        return SEMANTIC_ALIASES.get(token, token)
    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    else:
        for suffix in ("ingly", "edly", "ing", "ed", "es", "s"):
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                token = token[:-len(suffix)]
                break
    return SEMANTIC_ALIASES.get(token, token)


def _tokenize(text):
    return [
        _normalize_token(token)
        for token in re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
        if len(token) > 1
    ]


def _prepare_text_for_embedding(text):
    cleaned = str(text or "")
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _normalize_vector(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


def _serialize_vector(vector):
    return [round(float(value), VECTOR_DECIMALS) for value in vector]


def _fallback_embed_text(text):
    vector = [0.0] * _fallback_dimension()
    tokens = _tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % len(vector)
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0
        if token.isdigit():
            weight = 3.0
        elif token in {"architecture", "diagram", "flowchart", "queue", "stack", "tree", "graph", "sorting", "bfs", "dfs"}:
            weight = 1.5
        vector[index] += sign * weight

    return _normalize_vector(vector)


@lru_cache(maxsize=1)
def _load_sentence_transformer_model():
    if SentenceTransformer is None:
        return None
    try:
        local_only = bool(getattr(settings, "CHATBOT_EMBEDDING_LOCAL_ONLY", True))
        return SentenceTransformer(_model_name(), local_files_only=local_only)
    except Exception as e:
        print("ERROR:", str(e))
        return None


def get_embedding_backend_name():
    if _load_sentence_transformer_model() is not None:
        return _model_name()
    return f"fallback-hash::{_model_name()}"


def embed_texts(texts):
    texts = [text or "" for text in texts]
    if not texts:
        return []

    model = _load_sentence_transformer_model()
    if model is not None:
        vectors = []
        for index in range(0, len(texts), BATCH_SIZE):
            batch_texts = texts[index : index + BATCH_SIZE]
            encoded = model.encode(batch_texts, normalize_embeddings=True)
            for row in encoded:
                if hasattr(row, "tolist"):
                    row = row.tolist()
                vectors.append([float(value) for value in row])
        return vectors

    vectors = []
    for index in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[index : index + BATCH_SIZE]
        for text in batch_texts:
            vectors.append(_fallback_embed_text(text))
    return vectors


@lru_cache(maxsize=256)
def embed_query(text):
    return tuple(embed_texts([text or ""])[0])


def cosine_similarity(left, right):
    if not left or not right:
        return 0.0

    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for left_value, right_value in zip(left, right):
        dot += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value

    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


def store_chunk_embeddings(chunks):
    chunks = [chunk for chunk in chunks if chunk.id and (chunk.text_content or "").strip()]
    if not chunks:
        return 0

    chunk_ids = [chunk.id for chunk in chunks]
    existing_ids = set(
        ChunkEmbedding.objects.filter(chunk_id__in=chunk_ids).values_list("chunk_id", flat=True)
    )
    missing_chunks = [chunk for chunk in chunks if chunk.id not in existing_ids]
    if not missing_chunks:
        return 0

    vectors = embed_texts([_prepare_text_for_embedding(chunk.text_content) for chunk in missing_chunks])
    model_name = get_embedding_backend_name()

    to_create = []
    for chunk, vector in zip(missing_chunks, vectors):
        serialized = _serialize_vector(vector)
        to_create.append(
            ChunkEmbedding(
                chunk=chunk,
                embedding_vector=serialized,
                model_name=model_name,
            )
        )

    if to_create:
        ChunkEmbedding.objects.bulk_create(to_create)
    return len(to_create)


def embedding_map_for_chunk_ids(chunk_ids):
    chunk_ids = [chunk_id for chunk_id in chunk_ids if chunk_id]
    if not chunk_ids:
        return {}

    existing_embeddings = {
        item.chunk_id: item.embedding_vector
        for item in ChunkEmbedding.objects.filter(chunk_id__in=chunk_ids).only(
            "chunk_id",
            "embedding_vector",
        )
    }

    return existing_embeddings
