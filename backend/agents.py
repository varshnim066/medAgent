"""
agents.py
---------
Clinical Reasoning Agent powered by Google Gemini (direct SDK — fast path).

Optimizations:
  - Direct google.genai SDK call (no LangChain overhead)
  - Sentence-transformer encoder pre-warmed at startup
  - top_k=2 FAISS retrievals (fewer tokens, faster)
  - Compact prompt to minimise output tokens and generation time
  - Integrated ObservabilityTrace for full step-level logging
"""

import json
import os
import logging
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

# Keep ConversationBufferMemory for HITL doctor-feedback injection
from langchain_classic.memory import ConversationBufferMemory

from memory_agent import memory_agent
from rag import retrieve_guidelines
from trace_logger import ObservabilityTrace

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# ── Configure Gemini SDK (google.genai — latest, non-deprecated) ─────────────
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
_MODEL = "gemini-2.5-flash"
_CONFIG = types.GenerateContentConfig(
    temperature=0.1,
    response_mime_type="application/json",
)

# ── Per-patient conversation memory (used by HITL approve/reject) ────────────
_patient_memories: dict[str, ConversationBufferMemory] = {}


def get_patient_memory(patient_id: str) -> ConversationBufferMemory:
    if patient_id not in _patient_memories:
        _patient_memories[patient_id] = ConversationBufferMemory(
            memory_key="chat_history"
        )
    return _patient_memories[patient_id]


# ── Confidence scorer ────────────────────────────────────────────────────────
def _compute_confidence(
    previous_visits: list,
    labs: dict,
    guidelines: list,
) -> tuple[float, str]:
    score = 0.0
    score += min(len(previous_visits) / 5.0, 1.0) * 0.40

    expected = ["CBC", "LFT", "KFT", "Electrolytes", "Glucose", "Lipid_Profile"]
    score += (sum(1 for s in expected if s in labs) / len(expected)) * 0.40
    score += min(len(guidelines) / 5.0, 1.0) * 0.20

    label = "High" if score >= 0.70 else ("Medium" if score >= 0.40 else "Low")
    return round(score, 2), label


# ── Main reasoning agent ─────────────────────────────────────────────────────
def run_reasoning_agent(
    patient: dict,
    visit: dict,
    all_patient_visits: list[dict],
    trace: ObservabilityTrace = None,
) -> dict:
    logger.info(
        f"--- Reasoning Agent | Patient: {patient.get('name')} | Visit: {visit.get('visit_id')} ---"
    )

    # ── Step 1: Episodic Memory Retrieval ──────────────────────────────
    step1 = trace.start_step("episodic_memory_retrieval", {
        "patient_id": patient["patient_id"],
        "query_visit_id": visit.get("visit_id"),
        "top_k": 2,
    }) if trace else None

    episodes = memory_agent.retrieve_episodes(
        current_visit=visit,
        patient_id=patient["patient_id"],
        top_k=2,
    )
    episodic_summary = memory_agent.summarize_episodes(episodes)

    if step1:
        step1.finish(output={
            "episodes_retrieved": len(episodes),
            "episode_ids": [e.get("visit_id") for e in episodes],
            "hybrid_scores": [
                round(e.get("_memory_scores", {}).get("hybrid_score", 0), 3)
                for e in episodes
            ],
        })

    # ── Step 2: Guideline RAG Retrieval ───────────────────────────────
    step2 = trace.start_step("guideline_rag_retrieval", {
        "query": f"{visit.get('chief_complaint', '')} {', '.join(visit.get('symptoms', []))}",
        "top_k": 2,
    }) if trace else None

    query = f"{visit.get('chief_complaint', '')} {', '.join(visit.get('symptoms', []))}"
    guidelines = retrieve_guidelines(query=query, top_k=2)
    guideline_texts = [
        f"[{g['id']}] {g['disease']} ({g['source']}): {g['snippet']}"
        for g in guidelines
    ]

    if step2:
        step2.finish(output={
            "guidelines_retrieved": len(guidelines),
            "guideline_ids": [g.get("id") for g in guidelines],
            "relevance_scores": [round(g.get("relevance_score", 0), 3) for g in guidelines],
        })

    # ── Step 3: Confidence Score ───────────────────────────────────────
    confidence_score, confidence_label = _compute_confidence(
        previous_visits=all_patient_visits,
        labs=visit.get("labs", {}),
        guidelines=guidelines,
    )

    # ── Step 4: Build Prompt ───────────────────────────────────────────
    vitals = visit.get("vitals", {})
    labs = visit.get("labs", {})

    patient_info = (
        f"Name: {patient.get('name')} | Age: {patient.get('age')} | "
        f"Gender: {patient.get('gender')} | "
        f"Allergies: {', '.join(patient.get('allergies', ['None']))} | "
        f"PMH: {', '.join(patient.get('past_medical', patient.get('past_medical_history', ['None'])))}"
    )

    visit_info = (
        f"Date: {visit.get('date', visit.get('visit_date', 'Unknown'))} | "
        f"Complaint: {visit.get('chief_complaint', 'Unknown')} | "
        f"Symptoms: {', '.join(visit.get('symptoms', []))} | "
        f"HPI: {visit.get('hpi', 'N/A')}"
    )

    vitals_info = (
        f"BP: {vitals.get('blood_pressure', 'N/A')} | "
        f"HR: {vitals.get('heart_rate', 'N/A')} | "
        f"Temp: {vitals.get('temperature', 'N/A')} | "
        f"SpO2: {vitals.get('spo2', 'N/A')}"
    )

    labs_info = (
        f"HGB: {labs.get('CBC', {}).get('HGB', 'N/A')} | "
        f"WBC: {labs.get('CBC', {}).get('WBC', 'N/A')} | "
        f"Creatinine: {labs.get('KFT', {}).get('Creatinine', 'N/A')} | "
        f"HbA1c: {labs.get('Glucose', {}).get('HbA1c', 'N/A')} | "
        f"AST: {labs.get('LFT', {}).get('AST', 'N/A')} | "
        f"ALT: {labs.get('LFT', {}).get('ALT', 'N/A')}"
    )

    guidelines_info = "\n".join(guideline_texts) if guideline_texts else "None"

    # Include doctor's prior feedback from HITL memory
    memory = get_patient_memory(patient["patient_id"])
    chat_history = memory.load_memory_variables({}).get("chat_history", "")

    prompt = f"""You are a clinical decision support AI. Be concise. Do NOT diagnose.
{f"PRIOR DOCTOR FEEDBACK: {chat_history}" if chat_history else ""}

PATIENT: {patient_info}
VISIT: {visit_info}
VITALS: {vitals_info}
LABS: {labs_info}
HISTORY:
{episodic_summary}
GUIDELINES:
{guidelines_info}

Return JSON only:
{{
  "case_summary": "1-2 sentence clinical summary",
  "considerations": ["consideration 1", "consideration 2", "consideration 3"],
  "missing_information": ["missing 1", "missing 2"],
  "suggested_investigations": ["investigation 1", "investigation 2"],
  "follow_up_recommendations": ["follow-up 1", "follow-up 2"],
  "reasoning_trace": "1-2 sentence clinical reasoning"
}}"""

    # ── Step 5: LLM Clinical Reasoning ────────────────────────────────
    step3 = trace.start_step("clinical_reasoning_llm", {
        "model": _MODEL,
        "prompt_length_chars": len(prompt),
    }) if trace else None

    try:
        response = _client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=_CONFIG,
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)

        if step3:
            step3.finish(output={
                "case_summary_preview": parsed.get("case_summary", "")[:100],
                "considerations_count": len(parsed.get("considerations", [])),
                "confidence_score": confidence_score,
                "confidence_label": confidence_label,
            })

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        if step3:
            step3.finish(output={"error": str(e)}, status="error")
        parsed = {
            "case_summary": f"Unable to generate AI summary. Error: {str(e)}",
            "considerations": ["Review clinical data manually"],
            "missing_information": ["Gemini API unavailable"],
            "suggested_investigations": ["Standard workup based on clinical presentation"],
            "follow_up_recommendations": ["Follow up as clinically indicated"],
            "reasoning_trace": f"Agent error: {str(e)}",
        }

    return {
        "patient_id": patient["patient_id"],
        "visit_id": visit["visit_id"],
        "case_summary": parsed.get("case_summary", ""),
        "considerations": parsed.get("considerations", []),
        "missing_info": parsed.get("missing_information", []),
        "investigations": parsed.get("suggested_investigations", []),
        "follow_up": parsed.get("follow_up_recommendations", []),
        "confidence": confidence_label,
        "confidence_score": confidence_score,
        "reasoning_trace": parsed.get("reasoning_trace", ""),
        "guidelines_used": guideline_texts,
        "previous_visits_count": len(all_patient_visits),
        "trace_id": trace.trace_id if trace else None,
    }
