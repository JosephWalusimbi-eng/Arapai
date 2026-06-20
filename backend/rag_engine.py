import gc
import os
import pickle

import faiss
from sentence_transformers import SentenceTransformer

from backend.memory_utils import log_memory_usage

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INDEX_PATH = os.path.join(_PROJECT_ROOT, "data", "embeddings", "index.faiss")
TEXT_PATH = os.path.join(_PROJECT_ROOT, "data", "embeddings", "texts.pkl")

_embedding_model = None
_index = None
_texts = None
_loaded = False

DEFAULT_TOP_K = 4
MAX_DISTANCE = 1.25  # L2 threshold; filter weak matches


def _load_resources():
    global _embedding_model, _index, _texts, _loaded

    if _loaded:
        return

    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        log_memory_usage("rag_embed_model")

    if _index is None or _texts is None:
        if not os.path.exists(INDEX_PATH) or not os.path.exists(TEXT_PATH):
            raise FileNotFoundError(
                "RAG index not found. Put PDFs in data/raw_pdfs or data/rawpdfs, "
                "then run: python -m ingestion.ingest_pdf"
            )
        if os.path.getsize(INDEX_PATH) == 0 or os.path.getsize(TEXT_PATH) == 0:
            raise FileNotFoundError(
                "RAG index files are empty. Put PDFs in data/raw_pdfs or data/rawpdfs, "
                "then run: python -m ingestion.ingest_pdf"
            )
        _index = faiss.read_index(INDEX_PATH)
        with open(TEXT_PATH, "rb") as f:
            _texts = pickle.load(f)
        if not _texts or _index.ntotal == 0:
            raise FileNotFoundError(
                "RAG index is empty. Add PDFs and run: python -m ingestion.ingest_pdf"
            )
        log_memory_usage("rag_index_loaded")

    _loaded = True


def unload_resources():
    """Free RAG memory when disabled in the UI."""
    global _embedding_model, _index, _texts, _loaded
    _embedding_model = None
    _index = None
    _texts = None
    _loaded = False
    gc.collect()
    log_memory_usage("rag_unloaded")


def _format_chunks(indices, distances):
    parts = []
    for rank, (idx, dist) in enumerate(zip(indices, distances), start=1):
        if idx < 0 or idx >= len(_texts):
            continue
        if dist > MAX_DISTANCE:
            continue
        chunk = _texts[idx].strip()
        if chunk:
            parts.append(f"[Excerpt {rank}] {chunk}")
    return "\n\n".join(parts)


def retrieve(query, top_k=DEFAULT_TOP_K):
    _load_resources()
    top_k = min(top_k, len(_texts))
    if top_k <= 0:
        return ""

    query_vec = _embedding_model.encode([query]).astype("float32")
    distances, indices = _index.search(query_vec, top_k)
    formatted = _format_chunks(indices[0], distances[0])
    log_memory_usage("rag_retrieve")
    return formatted
