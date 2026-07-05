"""
api.py
------
All FastAPI route handlers for the Clinical Decision Support System.

Endpoints:
  GET  /patients              — List all patients
  GET  /patient/{id}          — Patient detail
  GET  /timeline/{id}         — Patient visit timeline
  POST /reason                — Run clinical reasoning agent
  POST /critique              — Run self-critique agent
  POST /approve               — Doctor approval/rejection
  GET  /history               — All approved recommendations
  GET  /dashboard/stats       — Dashboard statistics
  GET  /traces                — List all observability traces
  GET  /traces/{trace_id}     — Get a specific trace detail
"""

from fastapi import APIRouter, HTTPException

import database as db
from agents import run_reasoning_agent, get_patient_memory
from critique import run_critique_agent
from trace_logger import create_trace, get_trace, list_traces
from models import (
    ReasonRequest,
    CritiqueRequest,
    ApproveRequest, ApproveResponse,
)

router = APIRouter()

# In-memory cache of loaded patient data (set by main.py at startup)
_patients_cache: dict[str, dict] = {}  # patient_id -> patient dict


def set_patients_cache(patients: list[dict]):
    """Called at startup to populate the in-memory cache."""
    for p in patients:
        _patients_cache[p["patient_id"]] = p


# ── Patient Endpoints ────────────────────────────────────────────────────────

@router.get("/patients")
def list_patients():
    """Return all patients with visit counts."""
    patients = db.get_all_patients()
    return {"patients": patients, "total": len(patients)}


@router.get("/patient/{patient_id}")
def get_patient(patient_id: str):
    """Return a single patient's full profile including latest visit."""
    patient = db.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    visits = db.get_visits_by_patient(patient_id)
    patient["visits"] = visits
    patient["visit_count"] = len(visits)
    patient["latest_visit"] = visits[-1] if visits else None

    return patient


@router.get("/timeline/{patient_id}")
def get_timeline(patient_id: str):
    """Return all visits for a patient in chronological order."""
    patient = db.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")

    visits = db.get_visits_by_patient(patient_id)
    return {
        "patient_id": patient_id,
        "patient_name": patient["name"],
        "visits": visits,
        "total_visits": len(visits),
    }


# ── Agent Endpoints ──────────────────────────────────────────────────────────

@router.post("/reason")
def run_reasoning(req: ReasonRequest):
    """
    Run the Clinical Reasoning Agent for a specific patient visit.

    Flow:
      1. Load patient + visit data
      2. Create observability trace
      3. Retrieve previous visits via FAISS (traced)
      4. Retrieve guidelines via RAG (traced)
      5. Call Gemini for structured reasoning (traced)
      6. Return reasoning with confidence score + trace_id
    """
    patient = db.get_patient_by_id(req.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {req.patient_id} not found")

    cached = _patients_cache.get(req.patient_id, {})
    patient = {**cached, **patient}

    visit = db.get_visit_by_id(req.visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail=f"Visit {req.visit_id} not found")

    all_visits = db.get_visits_by_patient(req.patient_id)

    # Create observability trace for this reasoning cycle
    trace = create_trace(patient_id=req.patient_id, visit_id=req.visit_id)

    result = run_reasoning_agent(
        patient=patient,
        visit=visit,
        all_patient_visits=all_visits,
        trace=trace,
    )

    trace.finish()
    trace.save()

    return result


@router.post("/critique")
def run_critique(req: CritiqueRequest):
    """
    Run the Self-Critique Agent on an existing reasoning output.
    Critique step is appended to the existing trace for this visit.
    """
    patient = db.get_patient_by_id(req.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {req.patient_id} not found")

    cached = _patients_cache.get(req.patient_id, {})
    patient = {**cached, **patient}

    visit = db.get_visit_by_id(req.visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail=f"Visit {req.visit_id} not found")

    # Create a new trace for the critique step
    trace = create_trace(req.patient_id, req.visit_id)

    result = run_critique_agent(
        patient=patient,
        visit=visit,
        reasoning=req.reasoning,
        case_summary=req.case_summary,
        guidelines_used=[],
        trace=trace,
    )

    trace.finish()
    trace.save()

    return result


@router.post("/approve")
def approve_recommendation(req: ApproveRequest):
    """
    Doctor approves or rejects a clinical recommendation.

    - If approved: saves the full recommendation to the database
                   AND updates the patient's agent memory
    - If rejected: only logs the decision for audit purposes
    - Either way: logs to approval_history
    """
    if req.decision not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'approved' or 'rejected'"
        )

    # Log the decision regardless
    db.log_approval(
        patient_id=req.patient_id,
        visit_id=req.visit_id,
        decision=req.decision,
        notes=req.notes or "",
    )

    rec_id = None

    if req.decision == "approved":
        # HITL: Inject doctor's feedback into memory ONLY on approval
        # This ensures the agent only learns from validated clinical decisions
        memory = get_patient_memory(req.patient_id)
        feedback_msg = "HUMAN DOCTOR REVIEW: Recommendation was APPROVED."
        if req.notes:
            feedback_msg += f" Doctor's notes: {req.notes}"
        memory.save_context(
            {"input": "What is the result of my previous recommendation?"},
            {"output": feedback_msg}
        )

        # Save recommendation to database
        rec_id = db.save_recommendation({
            "patient_id": req.patient_id,
            "visit_id": req.visit_id,
            "case_summary": req.case_summary or "",
            "considerations": req.considerations or [],
            "missing_info": req.missing_info or [],
            "investigations": req.investigations or [],
            "follow_up": req.follow_up or [],
            "confidence": req.confidence or "Low",
            "confidence_score": req.confidence_score or 0.0,
            "reasoning_trace": req.reasoning_trace or "",
            "critique_text": req.critique_text or "",
            "guidelines_used": req.guidelines_used or [],
        })
        message = "Recommendation approved and saved successfully."
    else:
        message = "Recommendation rejected. No data was saved."

    return ApproveResponse(
        success=True,
        decision=req.decision,
        message=message,
        rec_id=rec_id,
    )


# ── History & Stats Endpoints ────────────────────────────────────────────────

@router.get("/history")
def get_history():
    """Return all approved recommendations (full approval history)."""
    recommendations = db.get_all_recommendations()
    return {
        "recommendations": recommendations,
        "total": len(recommendations),
    }


@router.get("/dashboard/stats")
def get_dashboard_stats():
    """Return aggregated statistics for the dashboard."""
    stats = db.get_dashboard_stats()

    age_buckets = {"18-30": 0, "31-45": 0, "46-60": 0, "61-80": 0}
    for patient in _patients_cache.values():
        age = patient.get("age", 0)
        if age <= 30:
            age_buckets["18-30"] += 1
        elif age <= 45:
            age_buckets["31-45"] += 1
        elif age <= 60:
            age_buckets["46-60"] += 1
        else:
            age_buckets["61-80"] += 1

    stats["age_distribution"] = [
        {"range": k, "count": v} for k, v in age_buckets.items()
    ]

    return stats


# ── Observability Trace Endpoints ────────────────────────────────────────────

@router.get("/traces")
def get_all_traces():
    """List the 50 most recent observability traces."""
    return {"traces": list_traces(limit=50)}


@router.get("/traces/{trace_id}")
def get_trace_detail(trace_id: str):
    """Return full step-level detail for a specific trace."""
    trace = get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
    if isinstance(trace, dict):
        return trace
    return trace.to_dict()
