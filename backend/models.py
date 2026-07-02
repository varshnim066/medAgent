"""
models.py
---------
Pydantic v2 request and response models for all API endpoints.
These define the data contracts between frontend and backend.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any


# ── Nested Models for Vitals, Labs, Imaging ──────────────────────────────────

class BloodPressure(BaseModel):
    systolic: int
    diastolic: int

class VitalsModel(BaseModel):
    blood_pressure: Optional[BloodPressure] = None
    pulse: Optional[int] = None
    temperature: Optional[float] = None
    respiratory_rate: Optional[int] = None
    spo2: Optional[int] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    bmi: Optional[float] = None

class LabCategory(BaseModel):
    # This handles dynamic keys like "HGB": 14.5, "WBC": 8.5
    pass

class ImagingFinding(BaseModel):
    finding: str
    impression: str


# ── Request Models ───────────────────────────────────────────────────────────

class ReasonRequest(BaseModel):
    """Request body for POST /reason"""
    patient_id: str = Field(..., description="The patient's unique ID")
    visit_id: str = Field(..., description="The current visit ID to reason about")


class CritiqueRequest(BaseModel):
    """Request body for POST /critique"""
    patient_id: str
    visit_id: str
    reasoning: str = Field(..., description="The initial clinical reasoning text to critique")
    case_summary: str = Field(default="", description="The generated case summary")


class ApproveRequest(BaseModel):
    """Request body for POST /approve"""
    patient_id: str
    visit_id: str
    decision: str = Field(..., description="'approved' or 'rejected'")
    notes: Optional[str] = Field(default="", description="Optional doctor notes")

    # Full recommendation payload (only used when decision = 'approved')
    case_summary: Optional[str] = None
    considerations: Optional[List[str]] = []
    missing_info: Optional[List[str]] = []
    investigations: Optional[List[str]] = []
    follow_up: Optional[List[str]] = []
    confidence: Optional[str] = "Low"
    confidence_score: Optional[float] = 0.0
    reasoning_trace: Optional[str] = None
    critique_text: Optional[str] = None
    guidelines_used: Optional[List[str]] = []


# ── Response Models ──────────────────────────────────────────────────────────

class ReasoningResponse(BaseModel):
    """Response from POST /reason"""
    patient_id: str
    visit_id: str
    case_summary: str
    considerations: List[str]
    missing_info: List[str]
    investigations: List[str]
    follow_up: List[str]
    confidence: str             # "Low" | "Medium" | "High"
    confidence_score: float     # 0.0 – 1.0
    reasoning_trace: str
    guidelines_used: List[str]
    previous_visits_count: int


class CritiqueResponse(BaseModel):
    """Response from POST /critique"""
    patient_id: str
    visit_id: str
    critique_text: str
    evidence_assessment: str
    missing_info_flags: List[str]
    hallucination_flags: List[str]
    contradiction_flags: List[str]
    guideline_alignment: str
    revised_reasoning: Optional[str] = None
    critique_score: float       # 0.0 – 1.0 (quality of original reasoning)


class ApproveResponse(BaseModel):
    """Response from POST /approve"""
    success: bool
    decision: str
    message: str
    rec_id: Optional[int] = None


class DashboardStats(BaseModel):
    """Response from GET /dashboard/stats"""
    total_patients: int
    total_visits: int
    approved_recommendations: int
    pending_reviews: int
    disease_distribution: List[dict]
    visit_trend: List[dict]

