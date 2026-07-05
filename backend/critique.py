"""
critique.py
-----------
Self-Critique Agent powered by Google Gemini (direct SDK — fast path).

Checks the reasoning output for:
  - Hallucinations / unsupported claims
  - Contradictions with ground-truth patient data
  - Guideline misalignment
  - Historical inconsistencies (e.g. repeating failed treatments)
"""

import json
import os
import logging
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

from memory_agent import memory_agent

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# ── Configure Gemini SDK ──────────────────────────────────────────────────────
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
_MODEL = "gemini-2.5-flash"
_CONFIG = types.GenerateContentConfig(
    temperature=0.1,
    response_mime_type="application/json",
)


def run_critique_agent(
    patient: dict,
    visit: dict,
    reasoning: str,
    case_summary: str,
    guidelines_used: list[str],
) -> dict:
    vitals = visit.get("vitals", {})
    labs = visit.get("labs", {})

    # Retrieve top-2 episodic memories for historical consistency check
    episodes = memory_agent.retrieve_episodes(
        current_visit=visit,
        patient_id=patient["patient_id"],
        top_k=2,
    )
    episodic_summary = memory_agent.summarize_episodes(episodes)

    patient_info = (
        f"Allergies: {', '.join(patient.get('allergies', ['None']))} | "
        f"PMH: {', '.join(patient.get('past_medical', patient.get('past_medical_history', ['None'])))}"
    )

    vitals_info = (
        f"BP: {vitals.get('blood_pressure', 'N/A')} | "
        f"SpO2: {vitals.get('spo2', 'N/A')} | "
        f"Temp: {vitals.get('temperature', 'N/A')}"
    )

    labs_info = (
        f"HbA1c: {labs.get('Glucose', {}).get('HbA1c', 'N/A')} | "
        f"Creatinine: {labs.get('KFT', {}).get('Creatinine', 'N/A')} | "
        f"WBC: {labs.get('CBC', {}).get('WBC', 'N/A')} | "
        f"CRP: {labs.get('Inflammatory', {}).get('CRP', 'N/A')}"
    )

    guidelines_info = "\n".join(guidelines_used[:2]) if guidelines_used else "None"

    prompt = f"""You are a senior clinical AI reviewer. Critically evaluate the AI-generated summary below.
Check for hallucinations, contradictions, guideline mismatches, and historical inconsistencies.

PATIENT: {patient_info}
VISIT: Complaint: {visit.get('chief_complaint', 'N/A')} | Symptoms: {', '.join(visit.get('symptoms', []))}
VITALS: {vitals_info}
LABS: {labs_info}
HISTORY:
{episodic_summary}
GUIDELINES: {guidelines_info}

AI CASE SUMMARY: {case_summary}
AI REASONING: {reasoning}

Return JSON only:
{{
  "critique_text": "2-3 sentence overall quality assessment",
  "evidence_assessment": "Strong / Moderate / Weak — 1 sentence explanation",
  "missing_info_flags": ["flag 1", "flag 2"],
  "hallucination_flags": ["flag 1 or None identified"],
  "contradiction_flags": ["flag 1 or None identified"],
  "guideline_alignment": "Well-aligned / Partially aligned / Not aligned — 1 sentence",
  "revised_reasoning": "1-2 sentence refined reasoning or 'Original reasoning is adequate'",
  "critique_score": 0.75
}}"""

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
    except Exception as e:
        logger.error(f"Critique agent error: {e}")
        parsed = {
            "critique_text": f"Critique agent encountered an error: {str(e)}",
            "evidence_assessment": "Unable to assess",
            "missing_info_flags": ["Critique unavailable"],
            "hallucination_flags": ["None identified"],
            "contradiction_flags": ["None identified"],
            "guideline_alignment": "Unable to assess",
            "revised_reasoning": "Review original reasoning manually",
            "critique_score": 0.5,
        }

    return {
        "patient_id": patient["patient_id"],
        "visit_id": visit["visit_id"],
        "critique_text": parsed.get("critique_text", ""),
        "evidence_assessment": parsed.get("evidence_assessment", ""),
        "missing_info_flags": parsed.get("missing_info_flags", []),
        "hallucination_flags": parsed.get("hallucination_flags", []),
        "contradiction_flags": parsed.get("contradiction_flags", []),
        "guideline_alignment": parsed.get("guideline_alignment", ""),
        "revised_reasoning": parsed.get("revised_reasoning", ""),
        "critique_score": float(parsed.get("critique_score", 0.5)),
    }
