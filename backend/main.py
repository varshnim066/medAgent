"""
main.py
-------
FastAPI application entry point.

Startup sequence:
  1. Initialize SQLite database tables
  2. Load patient_data.json into SQLite (if not already loaded)
  3. Build FAISS index for patient memory
  4. Build FAISS index for medical guidelines (RAG)
  5. Pre-warm the sentence-transformer encoder
  6. Start the API server

Run:
    uvicorn main:app --reload --port 8000
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import database as db
from api import router, set_patients_cache
from memory_agent import memory_agent
from rag import build_guideline_index

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Create FastAPI app ───────────────────────────────────────────────────────
app = FastAPI(
    title="Agentic Clinical Decision Support System",
    description=(
        "AI-powered clinical decision support with patient memory, "
        "RAG over medical guidelines, self-critique, and HITL doctor approval."
    ),
    version="1.0.0",
)

# ── CORS — allow React dev server ────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include all API routes ───────────────────────────────────────────────────
app.include_router(router)


# ── Startup event ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """
    Called once when the server starts.
    Initializes the database, loads data, and builds FAISS indexes.
    """
    print("\n" + "=" * 60)
    print("  Clinical Decision Support System — Starting Up")
    print("=" * 60)

    # 1. Initialize SQLite tables
    print("[Startup] Initializing database...")
    db.init_db()

    # 2. Load patient data from JSON
    data_path = Path(__file__).parent / "patient_data.json"
    if not data_path.exists():
        print("[Startup] ⚠️  patient_data.json not found!")
        print("[Startup]     Run: python generate_dataset.py")
        return

    print(f"[Startup] Loading patient data from {data_path}...")
    with open(data_path) as f:
        patients = json.load(f)

    # 3. Insert patients and visits into SQLite (idempotent)
    inserted_patients = 0
    inserted_visits = 0
    for patient in patients:
        existing = db.get_patient_by_id(patient["patient_id"])
        if not existing:
            db.insert_patient(patient)
            inserted_patients += 1
        for visit in patient.get("visits", []):
            db.insert_visit(visit)
            inserted_visits += 1

    print(f"[Startup] Patients loaded: {len(patients)} ({inserted_patients} new)")
    print(f"[Startup] Visits loaded:   {inserted_visits}")

    # 4. Populate in-memory cache (for lifestyle/history fields not fully in DB)
    set_patients_cache(patients)

    # 5. Build patient FAISS memory index using MemoryAgent
    faiss_index_path = Path(__file__).parent / "episodic_faiss.index"
    if not faiss_index_path.exists():
        print("[Startup] Building episodic memory FAISS index...")
        memory_agent.build_memory(patients)
    else:
        print("[Startup] Episodic FAISS index found on disk — skipping rebuild.")

    # 6. Build guideline FAISS index
    guideline_index_path = Path(__file__).parent / "guideline_faiss.index"
    if not guideline_index_path.exists():
        print("[Startup] Building guideline FAISS index...")
        build_guideline_index()
    else:
        print("[Startup] Guideline FAISS index found on disk — skipping rebuild.")

    # 7. Pre-warm the sentence-transformer encoder so the first request is fast
    print("[Startup] Pre-warming sentence-transformer encoder...")
    memory_agent._get_encoder()
    print("[Startup] ✅ Encoder ready!")

    print("[Startup] ✅ System ready!")
    print("=" * 60 + "\n")


# ── Root endpoint ─────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "service": "Agentic Clinical Decision Support System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }
