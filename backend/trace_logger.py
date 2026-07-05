"""
trace_logger.py
---------------
Observability Tracer for the Clinical Decision Support System.

Records a structured end-to-end trace for every reasoning cycle:
  Step 1: Episodic Memory Retrieval
  Step 2: Guideline RAG Retrieval
  Step 3: Clinical Reasoning (LLM)
  Step 4: Self-Critique (LLM)
  Step 5: Doctor Approval / Rejection

Traces are saved as JSON files in backend/traces/ and exposed
via the GET /traces and GET /traces/{trace_id} API endpoints.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TRACES_DIR = Path(__file__).parent / "traces"
TRACES_DIR.mkdir(exist_ok=True)


class StepTrace:
    def __init__(self, step_name: str, details: dict = None):
        self.step_name = step_name
        self.details = details or {}
        self.start_time = time.perf_counter()
        self.end_time: float = None
        self.duration_ms: float = None
        self.status = "running"

    def finish(self, output: dict = None, status: str = "success"):
        self.end_time = time.perf_counter()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 1)
        self.status = status
        if output:
            self.details["output"] = output

    def to_dict(self) -> dict:
        return {
            "step": self.step_name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


class ObservabilityTrace:
    """
    A single end-to-end trace for one reasoning cycle.
    Thread-safe for a single request lifecycle.
    """

    def __init__(self, patient_id: str, visit_id: str):
        self.trace_id = str(uuid.uuid4())[:12]
        self.patient_id = patient_id
        self.visit_id = visit_id
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.finished_at: str = None
        self.total_duration_ms: float = None
        self.steps: list[StepTrace] = []
        self._start_wall = time.perf_counter()

    def start_step(self, step_name: str, details: dict = None) -> StepTrace:
        step = StepTrace(step_name, details)
        self.steps.append(step)
        return step

    def finish(self):
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.total_duration_ms = round((time.perf_counter() - self._start_wall) * 1000, 1)

    def add_approval(self, decision: str, notes: str = ""):
        """Add the doctor's approval/rejection as the final trace step."""
        step = self.start_step(
            "doctor_approval",
            {
                "decision": decision,
                "notes": notes or "None",
            },
        )
        step.finish(status="success" if decision == "approved" else "rejected")

    def save(self) -> str:
        """Persist trace to disk as JSON. Returns the file path."""
        payload = {
            "trace_id": self.trace_id,
            "patient_id": self.patient_id,
            "visit_id": self.visit_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_duration_ms": self.total_duration_ms,
            "steps": [s.to_dict() for s in self.steps],
        }
        path = TRACES_DIR / f"{self.trace_id}.json"
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        return str(path)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "patient_id": self.patient_id,
            "visit_id": self.visit_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_duration_ms": self.total_duration_ms,
            "steps": [s.to_dict() for s in self.steps],
        }


# ── In-memory store of active / recent traces ─────────────────────────────────
# Maps trace_id -> ObservabilityTrace (kept in memory for the session)
_active_traces: dict[str, ObservabilityTrace] = {}


def create_trace(patient_id: str, visit_id: str) -> ObservabilityTrace:
    trace = ObservabilityTrace(patient_id, visit_id)
    _active_traces[trace.trace_id] = trace
    return trace


def get_trace(trace_id: str) -> ObservabilityTrace | None:
    # Try in-memory first
    if trace_id in _active_traces:
        return _active_traces[trace_id]
    # Fallback: load from disk
    path = TRACES_DIR / f"{trace_id}.json"
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        return data  # Return raw dict if not in memory
    return None


def list_traces(limit: int = 50) -> list[dict]:
    """Return the most recent traces (from disk) as a list of dicts."""
    files = sorted(TRACES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    results = []
    for f in files[:limit]:
        with open(f) as fp:
            try:
                data = json.load(fp)
                # Return summary only
                results.append({
                    "trace_id": data["trace_id"],
                    "patient_id": data["patient_id"],
                    "visit_id": data["visit_id"],
                    "started_at": data["started_at"],
                    "total_duration_ms": data.get("total_duration_ms"),
                    "step_count": len(data.get("steps", [])),
                })
            except Exception:
                pass
    return results
