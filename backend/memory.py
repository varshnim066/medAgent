"""
memory.py
---------
Patient memory module using FAISS + sentence-transformers.

Purpose:
  - Encodes previous patient visit notes into FAISS
  - Retrieves semantically similar previous visits for a given query
  - Helps the clinical reasoning agent understand patient history

FAISS index is persisted to disk so it doesn't need to be rebuilt on every startup.
"""

import pickle
from pathlib import Path

import numpy as np

# Lazy imports — loaded once at first use
_encoder = None
_index = None
_visit_store = []  # list of {visit_id, patient_id, text} for lookup

FAISS_INDEX_PATH = Path(__file__).parent / "patient_faiss.index"
FAISS_STORE_PATH = Path(__file__).parent / "patient_faiss_store.pkl"


def _get_encoder():
    """Load sentence-transformer model (downloads on first use ~80MB)."""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        print("[Memory] Loading sentence-transformers model...")
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
        print("[Memory] Model loaded.")
    return _encoder


def _get_index_and_store():
    """Return the FAISS index and visit store, loading from disk if available."""
    global _index, _visit_store
    if _index is not None:
        return _index, _visit_store
    if FAISS_INDEX_PATH.exists() and FAISS_STORE_PATH.exists():
        import faiss
        print("[Memory] Loading FAISS index from disk...")
        _index = faiss.read_index(str(FAISS_INDEX_PATH))
        with open(FAISS_STORE_PATH, "rb") as f:
            _visit_store = pickle.load(f)
        print(f"[Memory] Loaded {len(_visit_store)} visit embeddings.")
    return _index, _visit_store


def build_patient_memory(patients: list[dict]):
    """
    Build a FAISS index from all patient visits.
    Called once at application startup after data is loaded.

    Each visit is encoded as:
      "Patient: <name>. Complaint: <chief_complaint>. Notes: <clinical_notes>"
    """
    global _index, _visit_store
    import faiss

    encoder = _get_encoder()
    texts = []
    store = []

    for patient in patients:
        for visit in patient.get("visits", []):
            text = (
                f"Patient: {patient['name']}. Age: {patient['age']}. "
                f"Complaint: {visit.get('chief_complaint', '')}. "
                f"Symptoms: {', '.join(visit.get('symptoms', []))}. "
                f"Notes: {visit.get('clinical_notes', '')}"
            )
            texts.append(text)
            store.append({
                "visit_id": visit["visit_id"],
                "patient_id": visit["patient_id"],
                "patient_name": patient["name"],
                "date": visit.get("date", ""),
                "chief_complaint": visit.get("chief_complaint", ""),
                "clinical_notes": visit.get("clinical_notes", ""),
                "icd10_description": visit.get("icd10_description", ""),
                "text": text,
            })

    print(f"[Memory] Encoding {len(texts)} visit notes...")
    embeddings = encoder.encode(texts, show_progress_bar=True, batch_size=32)
    embeddings = np.array(embeddings, dtype=np.float32)

    # Build flat L2 index (exact search, suitable for <100k vectors)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Persist to disk
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    with open(FAISS_STORE_PATH, "wb") as f:
        pickle.dump(store, f)

    _index = index
    _visit_store = store
    print(f"[Memory] Patient FAISS index built with {index.ntotal} vectors.")


def retrieve_similar_visits(query_text: str, patient_id: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve the most relevant previous visits for a patient.

    Args:
        query_text: The current clinical context (complaint + symptoms)
        patient_id: Only return visits from THIS patient (patient-scoped memory)
        top_k: Number of similar visits to retrieve

    Returns:
        List of visit dicts sorted by relevance
    """
    index, store = _get_index_and_store()
    if index is None or len(store) == 0:
        return []

    encoder = _get_encoder()
    query_embedding = encoder.encode([query_text], normalize_embeddings=True)
    query_embedding = np.array(query_embedding, dtype=np.float32)

    # Search more than top_k because we'll filter by patient_id
    k = min(len(store), top_k * 10)
    distances, indices = index.search(query_embedding, k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(store):
            continue
        visit = store[idx]
        if visit["patient_id"] == patient_id:
            results.append({**visit, "similarity_score": float(1 / (1 + dist))})
        if len(results) >= top_k:
            break

    return results
