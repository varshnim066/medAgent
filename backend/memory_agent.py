"""
memory_agent.py
---------------
Episodic Memory Agent using FAISS + sentence-transformers + SQLite.

Purpose:
  - Encodes previous patient visit notes (episodes) into FAISS
  - Retrieves semantically similar previous visits for a given query
  - Ranks memories based on hybrid score (recency + semantic similarity)
  - Summarizes the memories for the LLM
"""

import pickle
import logging
from datetime import datetime
from pathlib import Path
import numpy as np

import database as db

# Configure logging
logger = logging.getLogger(__name__)

FAISS_INDEX_PATH = Path(__file__).parent / "episodic_faiss.index"
FAISS_STORE_PATH = Path(__file__).parent / "episodic_faiss_store.pkl"


class MemoryAgent:
    def __init__(self):
        self._encoder = None
        self._index = None
        self._visit_store = []  # list of {visit_id, patient_id, visit_date} for mapping FAISS rows
        self._load_or_init()

    def _get_encoder(self):
        """Load sentence-transformer model lazily."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            logger.info("[MemoryAgent] Loading sentence-transformers model...")
            print("[MemoryAgent] Loading sentence-transformers model...")
            self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._encoder

    def _load_or_init(self):
        """Load FAISS index and mapping store if they exist."""
        if FAISS_INDEX_PATH.exists() and FAISS_STORE_PATH.exists():
            import faiss
            print("[MemoryAgent] Loading FAISS index from disk...")
            self._index = faiss.read_index(str(FAISS_INDEX_PATH))
            with open(FAISS_STORE_PATH, "rb") as f:
                self._visit_store = pickle.load(f)
            print(f"[MemoryAgent] Loaded {len(self._visit_store)} visit embeddings.")

    def _format_visit_for_embedding(self, visit: dict) -> str:
        """
        Creates a rich textual representation of a visit episode to capture semantics.
        Includes all required fields: chief complaint, symptoms, clinical notes,
        doctor assessment, diagnosis, treatment plan, medications, labs, imaging, etc.
        """
        symptoms = ", ".join(visit.get("symptoms", [])) if isinstance(visit.get("symptoms"), list) else str(visit.get("symptoms", ""))
        medications = ", ".join(visit.get("medications", [])) if isinstance(visit.get("medications"), list) else str(visit.get("medications", ""))
        
        # Summarize labs/imaging loosely for embedding
        labs = visit.get("labs", {})
        imaging = visit.get("imaging", {})
        labs_str = "Present" if labs else "None"
        imaging_str = "Present" if imaging else "None"

        text = (
            f"Visit Date: {visit.get('visit_date', visit.get('date', ''))}. "
            f"Complaint: {visit.get('chief_complaint', '')}. "
            f"Symptoms: {symptoms}. "
            f"Notes: {visit.get('clinical_notes', '')}. "
            f"Diagnosis: {visit.get('icd10_description', '')}. "
            f"Doctor Assessment: {visit.get('doctor_assessment', '')}. "
            f"Treatment Plan: {visit.get('treatment_plan', '')}. "
            f"Medications: {medications}. "
            f"Labs: {labs_str}. Imaging: {imaging_str}. "
            f"Outcome/Follow-up: {visit.get('follow_up_advice', '')}."
        )
        return text

    def build_memory(self, patients: list[dict]):
        """
        Build a FAISS index from all patient visits.
        Called once at application startup or when regenerating dataset.
        """
        import faiss

        encoder = self._get_encoder()
        texts = []
        store = []

        for patient in patients:
            for visit in patient.get("visits", []):
                text = self._format_visit_for_embedding(visit)
                texts.append(text)
                store.append({
                    "visit_id": visit["visit_id"],
                    "patient_id": visit["patient_id"],
                    "visit_date": visit.get("date", visit.get("visit_date", "")),
                })

        print(f"[MemoryAgent] Encoding {len(texts)} visit episodes...")
        embeddings = encoder.encode(texts, show_progress_bar=True, batch_size=32)
        embeddings = np.array(embeddings, dtype=np.float32)

        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)

        faiss.write_index(index, str(FAISS_INDEX_PATH))
        with open(FAISS_STORE_PATH, "wb") as f:
            pickle.dump(store, f)

        self._index = index
        self._visit_store = store
        print(f"[MemoryAgent] Episodic Memory built with {index.ntotal} vectors.")

    def _calculate_recency_score(self, visit_date_str: str) -> float:
        """
        Calculates a recency score from 0.0 to 1.0.
        Assuming 'YYYY-MM-DD', closer to today = higher score.
        """
        try:
            visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            days_diff = (today - visit_date).days
            if days_diff < 0:
                days_diff = 0
            # Decay: 1.0 at 0 days, drops to ~0.1 at 10 years (3650 days)
            score = np.exp(-days_diff / 1000.0)
            return float(score)
        except Exception:
            return 0.5  # fallback if parsing fails

    def retrieve_episodes(self, current_visit: dict, patient_id: str, top_k: int = 5) -> list[dict]:
        """
        Retrieve and rank the most relevant previous visits for a patient.
        Ranks memories by a hybrid score combining semantic similarity and recency.
        """
        if self._index is None or len(self._visit_store) == 0:
            print("[MemoryAgent] Index is empty.")
            return []

        # 1. Create a query text representing the current episode
        query_text = self._format_visit_for_embedding(current_visit)
        
        encoder = self._get_encoder()
        query_embedding = encoder.encode([query_text], normalize_embeddings=True)
        query_embedding = np.array(query_embedding, dtype=np.float32)

        # Retrieve a broad set of candidates (up to 20 for this patient)
        k_search = min(len(self._visit_store), top_k * 10)
        distances, indices = self._index.search(query_embedding, k_search)

        candidates = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._visit_store):
                continue
            visit_mapping = self._visit_store[idx]
            
            # Filter by patient_id AND exclude the exact current visit
            if visit_mapping["patient_id"] == patient_id and visit_mapping["visit_id"] != current_visit["visit_id"]:
                
                # Similarity score: L2 distance -> similarity [0, 1]
                sim_score = float(1 / (1 + dist))
                
                # Recency score
                rec_score = self._calculate_recency_score(visit_mapping.get("visit_date", ""))
                
                # Hybrid Ranking (70% Semantic, 30% Recency)
                hybrid_score = (0.7 * sim_score) + (0.3 * rec_score)
                
                candidates.append({
                    "visit_id": visit_mapping["visit_id"],
                    "hybrid_score": hybrid_score,
                    "sim_score": sim_score,
                    "rec_score": rec_score
                })

        # Sort candidates by hybrid score descending
        candidates = sorted(candidates, key=lambda x: x["hybrid_score"], reverse=True)
        
        # Take Top K
        top_candidates = candidates[:top_k]
        
        # Hydrate candidates with full visit data from SQLite
        results = []
        for cand in top_candidates:
            full_visit = db.get_visit_by_id(cand["visit_id"])
            if full_visit:
                # Attach scores for logging and context
                full_visit["_memory_scores"] = {
                    "hybrid_score": cand["hybrid_score"],
                    "sim_score": cand["sim_score"],
                    "rec_score": cand["rec_score"]
                }
                results.append(full_visit)
                
        return results

    def summarize_episodes(self, episodes: list[dict]) -> str:
        """
        Formats retrieved episodic memories into a structured string for the LLM context.
        """
        if not episodes:
            return "No previous episodic memories found."

        summary = ""
        for i, ep in enumerate(episodes, 1):
            date = ep.get("visit_date", ep.get("date", "Unknown"))
            dx = ep.get("icd10_description", "None")
            complaint = ep.get("chief_complaint", "")
            
            symptoms = ", ".join(ep.get("symptoms", [])) if isinstance(ep.get("symptoms"), list) else str(ep.get("symptoms", ""))
            meds = ", ".join(ep.get("medications", [])) if isinstance(ep.get("medications"), list) else str(ep.get("medications", ""))
            
            assessment = ep.get("doctor_assessment", "None")
            treatment = ep.get("treatment_plan", "None")
            
            summary += f"### Episode {i} ({date})\n"
            summary += f"- **Complaint & Symptoms**: {complaint} | {symptoms}\n"
            summary += f"- **Diagnosis**: {dx}\n"
            summary += f"- **Assessment**: {assessment}\n"
            summary += f"- **Treatment & Meds**: {treatment} | {meds}\n"
            summary += "\n"

        return summary.strip()

# Global singleton instance
memory_agent = MemoryAgent()
