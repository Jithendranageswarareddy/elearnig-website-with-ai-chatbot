import json
from pathlib import Path

import numpy as np
from django.conf import settings

from ..models import ChunkEmbedding

try:
    import faiss
except Exception as e:  # pragma: no cover
    print("ERROR:", str(e))
    faiss = None


DATA_DIR = Path(settings.BASE_DIR) / "data"
INDEX_PATH = DATA_DIR / "faiss_index.bin"
META_PATH = DATA_DIR / "faiss_index_meta.json"

INDEX_CACHE = None
META_CACHE = None
INDEX_LOADED = False


def build_index():
    global INDEX_CACHE, META_CACHE, INDEX_LOADED

    if faiss is None:
        INDEX_CACHE = None
        META_CACHE = {"enabled": False, "vector_count": 0, "dimension": 0, "mapping": []}
        INDEX_LOADED = True
        return {"enabled": False, "vector_count": 0, "dimension": 0}

    rows = list(ChunkEmbedding.objects.only("chunk_id", "embedding_vector"))
    valid = [row for row in rows if row.embedding_vector]
    if not valid:
        meta = {"enabled": True, "vector_count": 0, "dimension": 0, "mapping": []}
        _persist_meta(meta)
        INDEX_CACHE = None
        META_CACHE = meta
        INDEX_LOADED = True
        return meta

    dimension = len(valid[0].embedding_vector)
    vectors = []
    mapping = []
    for row in valid:
        vector = [float(value) for value in (row.embedding_vector or [])]
        if len(vector) != dimension:
            continue
        vectors.append(vector)
        mapping.append(int(row.chunk_id))

    if not vectors:
        meta = {"enabled": True, "vector_count": 0, "dimension": 0, "mapping": []}
        _persist_meta(meta)
        INDEX_CACHE = None
        META_CACHE = meta
        INDEX_LOADED = True
        return meta

    index = faiss.IndexFlatIP(dimension)
    matrix = np.asarray(vectors, dtype="float32")
    faiss.normalize_L2(matrix)
    index.add(matrix)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    meta = {
        "enabled": True,
        "vector_count": len(mapping),
        "dimension": dimension,
        "mapping": mapping,
    }
    _persist_meta(meta)
    INDEX_CACHE = index
    META_CACHE = meta
    INDEX_LOADED = True
    return meta


def load_index():
    global INDEX_CACHE, META_CACHE, INDEX_LOADED

    if INDEX_LOADED:
        return INDEX_CACHE, META_CACHE

    if faiss is None:
        INDEX_CACHE = None
        META_CACHE = {"enabled": False, "vector_count": 0, "dimension": 0, "mapping": []}
        INDEX_LOADED = True
        return INDEX_CACHE, META_CACHE

    if not INDEX_PATH.exists() or not META_PATH.exists():
        meta = build_index()
        return INDEX_CACHE, meta

    INDEX_CACHE = faiss.read_index(str(INDEX_PATH)) if INDEX_PATH.exists() else None
    META_CACHE = json.loads(META_PATH.read_text(encoding="utf-8"))
    INDEX_LOADED = True
    return INDEX_CACHE, META_CACHE


def upsert_index_for_chunk_ids(chunk_ids):
    global INDEX_CACHE, META_CACHE, INDEX_LOADED

    chunk_ids = [int(chunk_id) for chunk_id in (chunk_ids or []) if chunk_id]
    if not chunk_ids:
        return {"enabled": faiss is not None, "vector_count": int((META_CACHE or {}).get("vector_count", 0) or 0), "added": 0}

    if faiss is None:
        return {"enabled": False, "vector_count": 0, "added": 0}

    rows = list(
        ChunkEmbedding.objects.filter(chunk_id__in=chunk_ids).values_list("chunk_id", "embedding_vector")
    )
    rows = [(int(chunk_id), embedding_vector or []) for chunk_id, embedding_vector in rows if embedding_vector]
    if not rows:
        return {"enabled": True, "vector_count": int((META_CACHE or {}).get("vector_count", 0) or 0), "added": 0}

    index, meta = load_index()
    meta = dict(meta or {"enabled": True, "vector_count": 0, "dimension": 0, "mapping": []})
    mapping = list(meta.get("mapping") or [])

    existing_chunk_ids = set(ChunkEmbedding.objects.values_list("chunk_id", flat=True))
    if any(mapped_id not in existing_chunk_ids for mapped_id in mapping):
        rebuilt = build_index()
        rebuilt["added"] = 0
        return rebuilt

    target_dim = len(rows[0][1])
    if index is None or not int(meta.get("vector_count", 0)):
        index = faiss.IndexFlatIP(target_dim)
        mapping = []
        meta = {
            "enabled": True,
            "vector_count": 0,
            "dimension": target_dim,
            "mapping": mapping,
        }

    if int(meta.get("dimension", 0)) != target_dim:
        rebuilt = build_index()
        rebuilt["added"] = 0
        return rebuilt

    mapping_set = set(mapping)
    new_rows = [(chunk_id, vector) for chunk_id, vector in rows if chunk_id not in mapping_set]
    if not new_rows:
        return {
            "enabled": True,
            "vector_count": int(meta.get("vector_count", 0)),
            "dimension": int(meta.get("dimension", 0)),
            "added": 0,
        }

    matrix = np.asarray([vector for _chunk_id, vector in new_rows], dtype="float32")
    faiss.normalize_L2(matrix)
    index.add(matrix)

    mapping.extend([chunk_id for chunk_id, _vector in new_rows])
    meta["mapping"] = mapping
    meta["vector_count"] = len(mapping)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    _persist_meta(meta)

    INDEX_CACHE = index
    META_CACHE = meta
    INDEX_LOADED = True

    return {
        "enabled": True,
        "vector_count": int(meta.get("vector_count", 0)),
        "dimension": int(meta.get("dimension", 0)),
        "added": len(new_rows),
    }


def search_index(query_vector, top_k=5):
    if not query_vector:
        return []
    index, meta = load_index()
    if index is None or not meta.get("vector_count"):
        return []

    vector = np.asarray([list(query_vector)], dtype="float32")
    if vector.shape[1] != int(meta.get("dimension", 0)):
        return []
    faiss.normalize_L2(vector)
    scores, ids = index.search(vector, max(1, int(top_k)))

    mapping = list(meta.get("mapping") or [])
    results = []
    for internal_id, score in zip(ids[0], scores[0]):
        if internal_id < 0 or internal_id >= len(mapping):
            continue
        results.append({"chunk_id": int(mapping[internal_id]), "score": float(score)})
    return results


def _persist_meta(meta):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
