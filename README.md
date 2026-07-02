# Patient IQ — Agentic Clinical Decision Support System

Patient IQ (MedAgents) is a production-grade, Multi-Agent Clinical Decision Support System. It utilizes LangChain and Google's Gemini LLMs to process complex patient histories, synthesize real-time clinical notes, retrieve medical guidelines, and orchestrate automated clinical reasoning to assist doctors in making accurate, fast, and grounded medical decisions.

## Architecture & Features

This system goes beyond standard RAG or zero-shot generation by incorporating a sophisticated, multi-layer AI architecture:

### 1. Dual Retrieval-Augmented Generation (RAG)
- **Medical Guidelines:** Utilizes FAISS vector stores to retrieve the most semantically relevant clinical protocols (e.g., ADA guidelines for Diabetes, ACC/AHA for Hypertension).
- **Episodic Patient Memory:** Retrieves semantically similar past patient visits (episodes), weighted by a hybrid ranking algorithm combining semantic similarity and chronological recency. This ensures the AI remembers historical contexts and previous treatments that failed or succeeded.

### 2. Multi-Agent Workflow
Instead of a single monolithic LLM call, Patient IQ utilizes a LangChain-powered multi-agent flow:
- **Coordinator Agent:** Orchestrates data gathering, formats the clinical presentation, and generates the initial reasoning trace, including considerations and investigation suggestions.
- **Critique Agent:** Acts as an adversarial reviewer. It cross-references the Coordinator's output against the ground truth data (Vitals, Labs, Patient History) to actively flag contradictions, hallucinations, or guideline mismatches before the doctor sees the final result.

### 3. Human-In-The-Loop (HITL) Context Buffer
The system never makes automated autonomous diagnoses. It operates strictly under Human-in-the-Loop review.
- The React frontend provides an intuitive "Doctor Review" workflow (Approve/Reject).
- **Continuous Learning:** When a doctor approves or rejects a recommendation and provides notes, the backend dynamically injects this decision into the patient's LangChain `ConversationBufferMemory`. The agents literally learn and adapt to the specific doctor's feedback for that patient in future iterations.

### 4. Normalized Relational Database
Unlike prototyping systems that rely on flat JSON blobs, Patient IQ uses a fully normalized SQLite schema (12 tables) separating Patients, Visits, Vitals, Labs, Medications, and Approval History. This ensures zero data loss, strict type-safety via Pydantic, and high-performance querying.

### 5. Premium Glassmorphism UI
The React frontend (Vite + TailwindCSS) features state-of-the-art UI/UX, including deep glassmorphism aesthetics, dynamic micro-animations, radial gradient glows, and translucent backdrop blurring for a visually stunning and highly responsive clinical dashboard.

## Setup Instructions

### Backend (FastAPI + LangChain + FAISS)
1. Navigate to `backend/`.
2. Ensure you have Python 3.10+ installed.
3. Install dependencies: `pip install -r requirements.txt`.
4. Create a `.env` file containing your `GEMINI_API_KEY=your_key`.
5. Run the database seed and FAISS indexer:
   - `python generate_dataset.py` (Generates synthetic patients).
   - `python memory.py` (Builds the FAISS vector stores).
6. Start the API server:
   - `uvicorn main:app --reload --port 8000`.

### Frontend (React + Vite + TailwindCSS)
1. Navigate to `frontend/`.
2. Install dependencies: `npm install`.
3. Start the development server:
   - `npm run dev`.
4. Open `http://localhost:5173` (or the port specified by Vite) in your browser.

## Tech Stack
- **AI/LLM:** LangChain, Google Gemini-2.0-Flash, SentenceTransformers, FAISS.
- **Backend:** FastAPI, Python, SQLite, Pydantic.
- **Frontend:** React, Vite, TailwindCSS, Lucide Icons, Axios.
