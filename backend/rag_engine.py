import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer

INDEX_PATH = "data/embeddings/index.faiss"
TEXT_PATH = "data/embeddings/texts.pkl"

_embedding_model = None
_index = None
_texts = None


def _load_resources():
    global _embedding_model, _index, _texts

    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    if _index is None or _texts is None:
        if not os.path.exists(INDEX_PATH) or not os.path.exists(TEXT_PATH):
            raise FileNotFoundError(
                "RAG index not found. Put PDFs in data/raw_pdfs or data/rawpdfs, "
                "then run: python -m ingestion.ingest_pdf"
            )
        _index = faiss.read_index(INDEX_PATH)
        with open(TEXT_PATH, "rb") as f:
            _texts = pickle.load(f)
        if not _texts or _index.ntotal == 0:
            raise FileNotFoundError(
                "RAG index is empty. Add PDFs and run: python -m ingestion.ingest_pdf"
            )


def retrieve(query, top_k=3):
    """
    Retrieve top-k relevant text chunks for a query.
    """
    _load_resources()
    top_k = min(top_k, len(_texts))
    if top_k <= 0:
        return ""
    query_vec = _embedding_model.encode([query]).astype("float32")
    _, indices = _index.search(query_vec, top_k)
    return "\n".join(_texts[i] for i in indices[0] if i < len(_texts))
