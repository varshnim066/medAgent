"""
agents.py
---------
Clinical Reasoning Agent powered by Google Gemini and LangChain.

This agent:
  1. Takes the current patient visit data
  2. Retrieves previous visit history via FAISS Episodic Memory
  3. Retrieves relevant medical guidelines via RAG
  4. Maintains ConversationBufferMemory for the patient's active session
  5. Calls Gemini via LangChain to generate structured clinical reasoning
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from memory_agent import memory_agent
from rag import retrieve_guidelines

# LangChain Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.memory import ConversationBufferMemory
from langchain_classic.prompts import PromptTemplate
from langchain_classic.chains import LLMChain

load_dotenv(Path(__file__).parent.parent / ".env")

# Global dictionary to store ConversationBufferMemory per patient
_patient_memories = {}

def get_patient_memory(patient_id: str) -> ConversationBufferMemory:
    if patient_id not in _patient_memories:
        _patient_memories[patient_id] = ConversationBufferMemory(
            memory_key="chat_history"
        )
    return _patient_memories[patient_id]

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    api_key=os.getenv("GEMINI_API_KEY", ""),
    temperature=0.2
)

def _compute_confidence(
    previous_visits: list,
    labs: dict,
    guidelines: list,
) -> tuple[float, str]:
    score = 0.0

    visit_score = min(len(previous_visits) / 5.0, 1.0) * 0.40
    score += visit_score

    expected_lab_sections = ["CBC", "LFT", "KFT", "Electrolytes", "Glucose", "Lipid_Profile"]
    available = sum(1 for s in expected_lab_sections if s in labs)
    lab_score = (available / len(expected_lab_sections)) * 0.40
    score += lab_score

    guideline_score = min(len(guidelines) / 5.0, 1.0) * 0.20
    score += guideline_score

    if score >= 0.70:
        label = "High"
    elif score >= 0.40:
        label = "Medium"
    else:
        label = "Low"

    return round(score, 2), label


def run_reasoning_agent(patient: dict, visit: dict, all_patient_visits: list[dict]) -> dict:
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"\n--- Running Coordinator Agent for Patient: {patient.get('name')} | Visit: {visit.get('visit_id')} ---")

    # ── Step 1: Retrieve relevant episodic memories (Phase 6) ──────────
    episodes = memory_agent.retrieve_episodes(
        current_visit=visit,
        patient_id=patient["patient_id"],
        top_k=3,
    )
    
    episodic_summary = memory_agent.summarize_episodes(episodes)
    logger.info(f"Generated Episodic Summary:\n{episodic_summary}\n")

    # ── Step 2: Retrieve relevant guidelines (Dual RAG - Phase 5) ──────
    query = f"{visit.get('chief_complaint', '')} {', '.join(visit.get('symptoms', []))}"
    guidelines = retrieve_guidelines(query=query, top_k=5)
    guideline_texts = [
        f"[{g['id']}] {g['disease']} ({g['source']}): {g['snippet']}"
        for g in guidelines
    ]

    # ── Step 3: Compute confidence score ───────────────────────────────
    confidence_score, confidence_label = _compute_confidence(
        previous_visits=all_patient_visits,
        labs=visit.get("labs", {}),
        guidelines=guidelines,
    )

    # ── Step 4: Construct the LangChain Prompt ─────────────────────────
    vitals = visit.get("vitals", {})
    labs = visit.get("labs", {})

    prompt_template = PromptTemplate(
        input_variables=["chat_history", "patient_info", "current_visit", "vitals", "labs", "episodic_summary", "guidelines"],
        template="""
You are a clinical decision support AI assistant. Your role is to help doctors by providing structured clinical summaries and suggestions. You must NEVER make a diagnosis or prescribe treatment. Your output must always be reviewed and approved by a licensed physician.

## PREVIOUS CONVERSATION (Working Memory)
{chat_history}

## PATIENT INFORMATION
{patient_info}

## CURRENT VISIT
{current_visit}

## VITALS
{vitals}

## LABORATORY RESULTS (Selected)
{labs}

## EPISODIC MEMORY (Relevant Previous Visits)
{episodic_summary}

## RELEVANT CLINICAL GUIDELINES (Evidence-Based)
{guidelines}

## YOUR TASK
Based on all the above information, provide a structured clinical support summary. Do NOT diagnose. Use clinical language appropriate for a physician audience.

Respond ONLY in the following JSON format without markdown code blocks:
{{
  "case_summary": "A concise 3-5 sentence summary of the clinical presentation and key findings",
  "considerations": [
    "Consideration 1: ...",
    "Consideration 2: ..."
  ],
  "missing_information": [
    "Missing info 1: ..."
  ],
  "suggested_investigations": [
    "Investigation 1: ..."
  ],
  "follow_up_recommendations": [
    "Follow-up 1: ..."
  ],
  "reasoning_trace": "Step-by-step clinical reasoning walkthrough (3-6 sentences explaining how you arrived at the considerations)"
}}
"""
    )

    # Format context blocks
    patient_info = f"""
Name: {patient.get('name')}
Age: {patient.get('age')} years
Gender: {patient.get('gender')}
Allergies: {', '.join(patient.get('allergies', ['None']))}
Past Medical History: {', '.join(patient.get('past_medical', patient.get('past_medical_history', ['None'])))}
    """.strip()

    current_visit = f"""
Date: {visit.get('date', visit.get('visit_date', 'Unknown'))}
Chief Complaint: {visit.get('chief_complaint', 'Unknown')}
HPI: {visit.get('hpi', 'Not provided')}
Symptoms: {', '.join(visit.get('symptoms', []))}
Clinical Notes: {visit.get('clinical_notes', 'Not provided')}
    """.strip()

    labs_info = f"""
CBC: HGB {labs.get('CBC', {}).get('HGB', 'N/A')} g/dL, WBC {labs.get('CBC', {}).get('WBC', 'N/A')} x10³/μL
KFT: Creatinine {labs.get('KFT', {}).get('Creatinine', 'N/A')} mg/dL, Urea {labs.get('KFT', {}).get('Urea', 'N/A')} mg/dL
LFT: AST {labs.get('LFT', {}).get('AST', 'N/A')} U/L, ALT {labs.get('LFT', {}).get('ALT', 'N/A')} U/L
    """.strip()

    vitals_info = json.dumps(vitals, indent=2)
    guidelines_info = chr(10).join(guideline_texts)

    # ── Step 5: Execute LangChain Agent (Phase 7) ──────────────────────
    memory = get_patient_memory(patient["patient_id"])
    
    chain = LLMChain(
        llm=llm,
        prompt=prompt_template,
        memory=memory,
        verbose=True
    )

    try:
        response_text = chain.run(
            patient_info=patient_info,
            current_visit=current_visit,
            vitals=vitals_info,
            labs=labs_info,
            episodic_summary=episodic_summary,
            guidelines=guidelines_info
        )
        
        raw_text = response_text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(raw_text)

    except Exception as e:
        logger.error(f"LangChain Agent Error: {e}")
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
    }
