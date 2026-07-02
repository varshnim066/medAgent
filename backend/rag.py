"""
rag.py
------
Retrieval-Augmented Generation (RAG) for medical guidelines.

Purpose:
  - Loads 100 clinical guideline snippets from guidelines.json
  - Encodes them into a FAISS index using sentence-transformers
  - Retrieves the most relevant guidelines for a given clinical query

This is used by the Clinical Reasoning Agent to ground its reasoning
in evidence-based guidelines.
"""

import json
import pickle
from pathlib import Path

import numpy as np

_guideline_index = None
_guideline_store = []

GUIDELINES_PATH = Path(__file__).parent / "guidelines.json"
GUIDELINE_INDEX_PATH = Path(__file__).parent / "guideline_faiss.index"
GUIDELINE_STORE_PATH = Path(__file__).parent / "guideline_faiss_store.pkl"

_encoder = None


def _get_encoder():
    """Shared encoder — reuse if already loaded by memory.py."""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        print("[RAG] Loading sentence-transformers model...")
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder


def build_guideline_index():
    """
    Build and persist a FAISS index for all medical guidelines.
    Called once at application startup.
    """
    global _guideline_index, _guideline_store
    import faiss

    # Load guidelines
    with open(GUIDELINES_PATH) as f:
        guidelines = json.load(f)

    encoder = _get_encoder()

    # Each guideline is encoded as "Disease: <name>. Source: <source>. Guideline: <snippet>"
    texts = [
        f"Disease: {g['disease']}. Source: {g['source']}. Guideline: {g['snippet']}"
        for g in guidelines
    ]

    print(f"[RAG] Encoding {len(texts)} guidelines...")
    embeddings = encoder.encode(texts, show_progress_bar=False, batch_size=32)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, str(GUIDELINE_INDEX_PATH))
    _guideline_store = guidelines
    with open(GUIDELINE_STORE_PATH, "wb") as f:
        pickle.dump(guidelines, f)

    _guideline_index = index
    print(f"[RAG] Guideline FAISS index built with {index.ntotal} vectors.")


def _load_guideline_index():
    """Load guideline index from disk if not already loaded."""
    global _guideline_index, _guideline_store
    if _guideline_index is not None:
        return
    if GUIDELINE_INDEX_PATH.exists() and GUIDELINE_STORE_PATH.exists():
        import faiss
        _guideline_index = faiss.read_index(str(GUIDELINE_INDEX_PATH))
        with open(GUIDELINE_STORE_PATH, "rb") as f:
            _guideline_store = pickle.load(f)
        print(f"[RAG] Loaded guideline index ({len(_guideline_store)} guidelines).")
    else:
        build_guideline_index()


def retrieve_guidelines(query: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve the top-k most relevant guidelines for a clinical query.

    Args:
        query: Clinical context string (e.g., complaint + symptoms + disease name)
        top_k: Number of guidelines to retrieve

    Returns:
        List of guideline dicts with keys: id, disease, source, snippet
    """
    _load_guideline_index()

    if _guideline_index is None:
        return []

    encoder = _get_encoder()
    query_embedding = encoder.encode([query])
    query_embedding = np.array(query_embedding, dtype=np.float32)

    k = min(top_k, len(_guideline_store))
    distances, indices = _guideline_index.search(query_embedding, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if 0 <= idx < len(_guideline_store):
            guideline = _guideline_store[idx]
            results.append({
                **guideline,
                "relevance_score": float(1 / (1 + dist)),
            })

    return results
