"""
evaluate.py
-----------
Patient IQ — Evaluation Report Generator

Computes three core metrics from the dataset and traces:

1. Memory Retrieval Accuracy
   For each patient's most recent visit, retrieve top-2 episodes via FAISS
   and measure what % share the same ICD10 diagnosis code — a precise
   ground-truth match rate using the synthetic dataset.

2. Self-Correction Rate
   Scan all saved observability traces and measure what % of critique
   steps produced a self-correction (revised_reasoning != "Original
   reasoning is adequate").

3. Hallucination Rate
   From the same critique traces, measure what % flagged at least one
   hallucination (hallucination_flags not empty / not "None identified").

Additional metrics:
  - Dataset statistics (patients, visits, guidelines)
  - Approval vs rejection rates from approval_history
  - Confidence score distribution from recommendations
  - Average retrieval hybrid scores
  - Per-step latency from traces

Outputs a rich standalone HTML report at: backend/evaluation_report.html
Run: python evaluate.py
"""

import json
import pickle
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
DB_PATH = BASE / "clinical.db"
PATIENT_DATA = BASE / "patient_data.json"
FAISS_INDEX = BASE / "episodic_faiss.index"
FAISS_STORE = BASE / "episodic_faiss_store.pkl"
TRACES_DIR = BASE / "traces"
REPORT_PATH = BASE / "evaluation_report.html"


# ── DB helpers ────────────────────────────────────────────────────────────────
def db_query(sql: str, params=()) -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


# ── 1. Memory Retrieval Accuracy ──────────────────────────────────────────────
def compute_memory_retrieval_accuracy() -> dict:
    """
    For each patient with >1 visit, take the most recent visit as the query.
    Retrieve top-2 past visits via FAISS and check if they share the same
    ICD10 diagnosis code as the query visit (ground-truth match).

    Returns accuracy %, per-disease breakdown, and average hybrid score.
    """
    print("[Eval] Computing memory retrieval accuracy...")

    if not FAISS_INDEX.exists():
        return {"error": "FAISS index not found. Run memory.py first."}

    try:
        import faiss
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return {"error": "faiss or sentence_transformers not installed"}

    # Load FAISS index + mapping store
    index = faiss.read_index(str(FAISS_INDEX))
    with open(FAISS_STORE, "rb") as f:
        visit_store = pickle.load(f)  # list of {visit_id, patient_id, visit_date}

    # Build visit_id -> icd10_code lookup from DB
    diagnoses = db_query("SELECT visit_id, icd10_code FROM diagnoses")
    icd_map = {d["visit_id"]: d["icd10_code"] for d in diagnoses if d["icd10_code"]}

    # Load patient data for visit texts
    with open(PATIENT_DATA) as f:
        patients = json.load(f)

    encoder = SentenceTransformer("all-MiniLM-L6-v2")

    def format_visit(v: dict) -> str:
        symptoms = ", ".join(v.get("symptoms", [])) if isinstance(v.get("symptoms"), list) else ""
        return (
            f"Complaint: {v.get('chief_complaint', '')}. "
            f"Symptoms: {symptoms}. "
            f"Notes: {v.get('clinical_notes', '')}. "
            f"Diagnosis: {v.get('icd10_description', '')}."
        )

    total_queries = 0
    total_retrieved = 0
    correct_matches = 0
    hybrid_scores_all = []
    disease_breakdown: dict[str, dict] = {}

    for patient in patients:
        visits = sorted(
            patient.get("visits", []),
            key=lambda v: v.get("visit_date", v.get("date", "")),
        )
        if len(visits) < 2:
            continue

        query_visit = visits[-1]  # most recent visit = query
        past_visits = visits[:-1]   # all others = memory pool

        query_icd = icd_map.get(query_visit.get("visit_id"), "")
        if not query_icd:
            continue

        # Encode query
        query_text = format_visit(query_visit)
        qe = encoder.encode([query_text], normalize_embeddings=True).astype(np.float32)

        # Search FAISS
        k_search = min(len(visit_store), 20)
        distances, indices = index.search(qe, k_search)

        # Collect top-2 past visits for THIS patient
        candidates = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(visit_store):
                continue
            mapping = visit_store[idx]
            if (mapping["patient_id"] == patient["patient_id"]
                    and mapping["visit_id"] != query_visit.get("visit_id")):
                sim_score = float(1 / (1 + dist))
                candidates.append({
                    "visit_id": mapping["visit_id"],
                    "sim_score": sim_score,
                    "icd10": icd_map.get(mapping["visit_id"], ""),
                })
                if len(candidates) >= 2:
                    break

        if not candidates:
            continue

        total_queries += 1

        for cand in candidates:
            total_retrieved += 1
            hybrid_scores_all.append(cand["sim_score"])

            # Ground-truth match: retrieved episode has same ICD10 as query
            is_correct = (cand["icd10"] == query_icd and query_icd != "")
            if is_correct:
                correct_matches += 1

            # Per-disease breakdown
            disease = query_icd
            if disease not in disease_breakdown:
                disease_breakdown[disease] = {"retrieved": 0, "correct": 0}
            disease_breakdown[disease]["retrieved"] += 1
            if is_correct:
                disease_breakdown[disease]["correct"] += 1

    accuracy = round(correct_matches / total_retrieved * 100, 1) if total_retrieved else 0
    avg_score = round(float(np.mean(hybrid_scores_all)), 3) if hybrid_scores_all else 0

    # Top 5 diseases by retrieval count
    top_diseases = sorted(
        [
            {
                "icd10": k,
                "retrieved": v["retrieved"],
                "correct": v["correct"],
                "accuracy": round(v["correct"] / v["retrieved"] * 100, 1),
            }
            for k, v in disease_breakdown.items()
        ],
        key=lambda x: x["retrieved"],
        reverse=True,
    )[:8]

    print(f"[Eval] Memory accuracy: {accuracy}% ({correct_matches}/{total_retrieved} matches)")
    return {
        "accuracy_pct": accuracy,
        "correct_matches": correct_matches,
        "total_retrieved": total_retrieved,
        "total_queries": total_queries,
        "avg_similarity_score": avg_score,
        "top_diseases": top_diseases,
    }


# ── 2 & 3. Self-Correction Rate + Hallucination Rate from Traces ──────────────
def compute_critique_metrics() -> dict:
    """
    Parse all saved observability traces to extract critique outcomes.
    Returns self_correction_rate and hallucination_rate.
    """
    print("[Eval] Computing self-correction and hallucination rates from traces...")

    if not TRACES_DIR.exists():
        return {
            "traces_analysed": 0,
            "self_correction_rate": 0.0,
            "hallucination_rate": 0.0,
            "avg_critique_score": 0.0,
            "note": "No traces found. Generate reasoning in the app first.",
        }

    trace_files = list(TRACES_DIR.glob("*.json"))
    if not trace_files:
        return {
            "traces_analysed": 0,
            "self_correction_rate": 0.0,
            "hallucination_rate": 0.0,
            "avg_critique_score": 0.0,
            "note": "No traces found. Generate reasoning in the app first.",
        }

    self_corrected = 0
    hallucinated = 0
    critique_scores = []
    step_latencies: dict[str, list] = {}
    traces_with_critique = 0

    for tf in trace_files:
        try:
            with open(tf) as f:
                trace = json.load(f)
        except Exception:
            continue

        for step in trace.get("steps", []):
            name = step.get("step", "")
            duration = step.get("duration_ms")
            if duration:
                step_latencies.setdefault(name, []).append(duration)

            if name == "self_critique_llm":
                traces_with_critique += 1
                output = step.get("details", {}).get("output", {})

                score = output.get("critique_score", None)
                if score is not None:
                    critique_scores.append(float(score))

                # Self-correction: revised_reasoning provided & meaningful
                if output.get("self_corrected", False):
                    self_corrected += 1

                # Hallucination: any non-None hallucination flag
                if output.get("hallucination_detected", False):
                    hallucinated += 1

    if traces_with_critique == 0:
        return {
            "traces_analysed": len(trace_files),
            "traces_with_critique": 0,
            "self_correction_rate": 0.0,
            "hallucination_rate": 0.0,
            "avg_critique_score": 0.0,
            "avg_step_latencies_ms": {},
            "note": "Traces found but no critique steps yet. Click 'Run Critique' in the app.",
        }

    self_correction_rate = round(self_corrected / traces_with_critique * 100, 1)
    hallucination_rate = round(hallucinated / traces_with_critique * 100, 1)
    avg_critique_score = round(float(np.mean(critique_scores)), 3) if critique_scores else 0

    avg_latencies = {
        step: round(float(np.mean(vals)), 1)
        for step, vals in step_latencies.items()
    }

    print(f"[Eval] Self-correction rate: {self_correction_rate}% | Hallucination rate: {hallucination_rate}%")
    return {
        "traces_analysed": len(trace_files),
        "traces_with_critique": traces_with_critique,
        "self_correction_rate": self_correction_rate,
        "hallucination_rate": hallucination_rate,
        "avg_critique_score": avg_critique_score,
        "avg_step_latencies_ms": avg_latencies,
    }


# ── 4. Dataset & Approval Stats from DB ──────────────────────────────────────
def compute_dataset_stats() -> dict:
    print("[Eval] Computing dataset and approval statistics...")

    patients_count = db_query("SELECT COUNT(*) AS cnt FROM patients")[0]["cnt"]
    visits_count = db_query("SELECT COUNT(*) AS cnt FROM visits")[0]["cnt"]
    recs_count = db_query("SELECT COUNT(*) AS cnt FROM recommendations")[0]["cnt"]

    approvals = db_query("SELECT decision, COUNT(*) AS cnt FROM approval_history GROUP BY decision")
    approval_map = {r["decision"]: r["cnt"] for r in approvals}
    total_decisions = sum(approval_map.values())
    approval_rate = round(approval_map.get("approved", 0) / total_decisions * 100, 1) if total_decisions else 0

    conf_rows = db_query("SELECT confidence, confidence_score FROM recommendations")
    conf_dist = {"High": 0, "Medium": 0, "Low": 0}
    conf_scores = []
    for r in conf_rows:
        conf_dist[r["confidence"]] = conf_dist.get(r["confidence"], 0) + 1
        if r["confidence_score"]:
            conf_scores.append(float(r["confidence_score"]))

    avg_confidence = round(float(np.mean(conf_scores)), 3) if conf_scores else 0

    with open(PATIENT_DATA) as f:
        patients_raw = json.load(f)
    avg_visits_per_patient = round(
        sum(len(p.get("visits", [])) for p in patients_raw) / len(patients_raw), 1
    ) if patients_raw else 0

    return {
        "total_patients": patients_count,
        "total_visits": visits_count,
        "avg_visits_per_patient": avg_visits_per_patient,
        "total_recommendations": recs_count,
        "total_decisions": total_decisions,
        "approved_count": approval_map.get("approved", 0),
        "rejected_count": approval_map.get("rejected", 0),
        "approval_rate_pct": approval_rate,
        "confidence_distribution": conf_dist,
        "avg_confidence_score": avg_confidence,
    }


# ── HTML Report Generator ─────────────────────────────────────────────────────
def generate_html_report(memory: dict, critique: dict, dataset: dict) -> str:
    now = datetime.now().strftime("%B %d, %Y at %H:%M")

    # Memory retrieval accuracy bar chart data
    disease_labels = [d["icd10"] for d in memory.get("top_diseases", [])]
    disease_accs = [d["accuracy"] for d in memory.get("top_diseases", [])]

    conf_dist = dataset.get("confidence_distribution", {})
    approved = dataset.get("approved_count", 0)
    rejected = dataset.get("rejected_count", 0)

    latencies = critique.get("avg_step_latencies_ms", {})
    latency_html = ""
    for step, ms in latencies.items():
        latency_html += f"""
        <div class="latency-row">
          <span class="step-name">{step.replace('_', ' ').title()}</span>
          <div class="latency-bar-wrap">
            <div class="latency-bar" style="width:{min(ms/50, 100):.0f}%"></div>
          </div>
          <span class="latency-ms">{ms:.0f} ms</span>
        </div>"""

    note_html = f'<div class="note-box">ℹ️ {critique.get("note", "")}</div>' if "note" in critique else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Patient IQ — Evaluation Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg: #050a14;
    --surface: #0d1929;
    --card: #112035;
    --border: #1e3a5f;
    --accent: #3b82f6;
    --accent2: #06b6d4;
    --green: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
    --text: #e2e8f0;
    --muted: #64748b;
    --radius: 16px;
  }}

  body {{
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 40px 20px;
  }}

  .container {{ max-width: 1200px; margin: 0 auto; }}

  /* Header */
  .header {{
    text-align: center;
    margin-bottom: 48px;
    padding: 40px;
    background: linear-gradient(135deg, #0d1929 0%, #0a1628 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute;
    top: -50%;
    left: 50%;
    transform: translateX(-50%);
    width: 600px;
    height: 300px;
    background: radial-gradient(ellipse, rgba(59,130,246,0.15) 0%, transparent 70%);
    pointer-events: none;
  }}
  .header h1 {{
    font-size: 2.4rem;
    font-weight: 700;
    background: linear-gradient(135deg, #60a5fa, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }}
  .header p {{ color: var(--muted); font-size: 0.95rem; }}
  .badge {{
    display: inline-block;
    background: rgba(59,130,246,0.15);
    border: 1px solid rgba(59,130,246,0.3);
    color: #60a5fa;
    padding: 4px 14px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 500;
    margin-bottom: 16px;
  }}

  /* Metric cards */
  .metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 20px;
    margin-bottom: 32px;
  }}
  .metric-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 28px 24px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .metric-card:hover {{ transform: translateY(-3px); box-shadow: 0 12px 40px rgba(0,0,0,0.4); }}
  .metric-card::after {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: var(--radius) var(--radius) 0 0;
  }}
  .metric-card.blue::after {{ background: linear-gradient(90deg, #3b82f6, #06b6d4); }}
  .metric-card.green::after {{ background: linear-gradient(90deg, #10b981, #06b6d4); }}
  .metric-card.amber::after {{ background: linear-gradient(90deg, #f59e0b, #ef4444); }}
  .metric-card.purple::after {{ background: linear-gradient(90deg, #8b5cf6, #3b82f6); }}

  .metric-label {{
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    font-weight: 600;
    margin-bottom: 10px;
  }}
  .metric-value {{
    font-size: 3rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 4px;
  }}
  .metric-card.blue .metric-value {{ color: #60a5fa; }}
  .metric-card.green .metric-value {{ color: #34d399; }}
  .metric-card.amber .metric-value {{ color: #fbbf24; }}
  .metric-card.purple .metric-value {{ color: #a78bfa; }}
  .metric-sub {{ font-size: 0.82rem; color: var(--muted); }}

  /* Section layout */
  .section {{ margin-bottom: 32px; }}
  .section-title {{
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .section-title::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }}

  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .three-col {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }}
  @media (max-width: 768px) {{
    .two-col, .three-col {{ grid-template-columns: 1fr; }}
  }}

  .chart-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px;
  }}
  .chart-card h3 {{
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 20px;
  }}

  /* Stat table */
  .stat-table {{ width: 100%; border-collapse: collapse; }}
  .stat-table td {{ padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; }}
  .stat-table td:first-child {{ color: var(--muted); }}
  .stat-table td:last-child {{ text-align: right; font-weight: 600; color: var(--text); }}

  /* Latency bars */
  .latency-row {{
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 12px; font-size: 0.85rem;
  }}
  .step-name {{ color: var(--muted); width: 200px; flex-shrink: 0; }}
  .latency-bar-wrap {{ flex: 1; background: rgba(255,255,255,0.05); border-radius: 4px; height: 8px; overflow: hidden; }}
  .latency-bar {{ height: 100%; background: linear-gradient(90deg, #3b82f6, #06b6d4); border-radius: 4px; transition: width 1s ease; }}
  .latency-ms {{ color: #60a5fa; width: 70px; text-align: right; font-weight: 600; }}

  /* Note */
  .note-box {{
    background: rgba(59,130,246,0.08);
    border: 1px solid rgba(59,130,246,0.25);
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: #93c5fd;
    margin-top: 12px;
  }}

  /* Disease table */
  .disease-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  .disease-table th {{
    text-align: left; padding: 8px 12px;
    color: var(--muted); font-weight: 600;
    text-transform: uppercase; font-size: 0.75rem;
    border-bottom: 1px solid var(--border);
  }}
  .disease-table td {{ padding: 10px 12px; border-bottom: 1px solid rgba(30,58,95,0.5); }}
  .acc-pill {{
    display: inline-block;
    padding: 2px 10px; border-radius: 999px;
    font-weight: 600; font-size: 0.8rem;
  }}
  .acc-high {{ background: rgba(16,185,129,0.15); color: #34d399; }}
  .acc-mid {{ background: rgba(245,158,11,0.15); color: #fbbf24; }}
  .acc-low {{ background: rgba(239,68,68,0.15); color: #f87171; }}

  footer {{ text-align: center; margin-top: 48px; color: var(--muted); font-size: 0.82rem; }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <div class="badge">🏥 Clinical AI Evaluation Report</div>
    <h1>Patient IQ — MedAgents</h1>
    <p>Agentic Clinical Decision Support System &nbsp;·&nbsp; Generated on {now}</p>
  </div>

  <!-- Core Metrics -->
  <div class="section">
    <div class="section-title">📊 Core Evaluation Metrics</div>
    <div class="metrics-grid">
      <div class="metric-card blue">
        <div class="metric-label">Memory Retrieval Accuracy</div>
        <div class="metric-value">{memory.get("accuracy_pct", 0)}%</div>
        <div class="metric-sub">{memory.get("correct_matches", 0)} / {memory.get("total_retrieved", 0)} ICD10 matches</div>
      </div>
      <div class="metric-card green">
        <div class="metric-label">Self-Correction Rate</div>
        <div class="metric-value">{critique.get("self_correction_rate", 0)}%</div>
        <div class="metric-sub">Of {critique.get("traces_with_critique", 0)} critique traces</div>
      </div>
      <div class="metric-card amber">
        <div class="metric-label">Hallucination Rate</div>
        <div class="metric-value">{critique.get("hallucination_rate", 0)}%</div>
        <div class="metric-sub">Flags detected in critique</div>
      </div>
      <div class="metric-card purple">
        <div class="metric-label">Avg Critique Score</div>
        <div class="metric-value">{critique.get("avg_critique_score", 0)}</div>
        <div class="metric-sub">Out of 1.0 (higher = better quality)</div>
      </div>
    </div>
  </div>

  <!-- Charts row 1 -->
  <div class="section">
    <div class="section-title">📈 Retrieval & Approval Analytics</div>
    <div class="two-col">
      <div class="chart-card">
        <h3>Doctor Approval vs Rejection</h3>
        <canvas id="approvalChart" height="200"></canvas>
      </div>
      <div class="chart-card">
        <h3>Confidence Score Distribution</h3>
        <canvas id="confidenceChart" height="200"></canvas>
      </div>
    </div>
  </div>

  <!-- Memory accuracy disease breakdown -->
  <div class="section">
    <div class="section-title">🧠 Memory Retrieval by Diagnosis (ICD10)</div>
    <div class="chart-card">
      <h3>Top Retrieved Diagnoses — Accuracy Breakdown</h3>
      <canvas id="diseaseChart" height="120"></canvas>
    </div>

    {"<br/>" if memory.get("top_diseases") else ""}
    {"" if not memory.get("top_diseases") else f'''
    <div class="chart-card" style="margin-top:16px">
      <table class="disease-table">
        <thead>
          <tr>
            <th>ICD10 Code</th>
            <th>Episodes Retrieved</th>
            <th>Correct Matches</th>
            <th>Accuracy</th>
          </tr>
        </thead>
        <tbody>
          {"".join(f"""
          <tr>
            <td>{d["icd10"]}</td>
            <td>{d["retrieved"]}</td>
            <td>{d["correct"]}</td>
            <td><span class="acc-pill {"acc-high" if d["accuracy"] >= 70 else "acc-mid" if d["accuracy"] >= 40 else "acc-low"}">{d["accuracy"]}%</span></td>
          </tr>""" for d in memory.get("top_diseases", []))}
        </tbody>
      </table>
    </div>'''}
  </div>

  <!-- Step Latencies + Dataset Stats -->
  <div class="section">
    <div class="section-title">⚡ Performance & Dataset Statistics</div>
    <div class="two-col">
      <div class="chart-card">
        <h3>Average Step Latency (ms)</h3>
        {latency_html if latency_html else '<p style="color:var(--muted);font-size:0.88rem">No trace latency data yet. Generate reasoning in the app.</p>'}
        {note_html}
      </div>
      <div class="chart-card">
        <h3>Dataset Overview</h3>
        <table class="stat-table">
          <tr><td>Total Patients</td><td>{dataset.get("total_patients", 0)}</td></tr>
          <tr><td>Total Visits</td><td>{dataset.get("total_visits", 0)}</td></tr>
          <tr><td>Avg Visits / Patient</td><td>{dataset.get("avg_visits_per_patient", 0)}</td></tr>
          <tr><td>Approved Recommendations</td><td>{dataset.get("approved_count", 0)}</td></tr>
          <tr><td>Rejected Decisions</td><td>{dataset.get("rejected_count", 0)}</td></tr>
          <tr><td>Approval Rate</td><td>{dataset.get("approval_rate_pct", 0)}%</td></tr>
          <tr><td>Avg Memory Sim Score</td><td>{memory.get("avg_similarity_score", 0)}</td></tr>
          <tr><td>Traces Analysed</td><td>{critique.get("traces_analysed", 0)}</td></tr>
        </table>
      </div>
    </div>
  </div>

</div>

<footer>
  Patient IQ — MedAgents &nbsp;·&nbsp; Evaluation Report &nbsp;·&nbsp; {now}
</footer>

<script>
// Approval Doughnut
new Chart(document.getElementById('approvalChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['Approved', 'Rejected'],
    datasets: [{{
      data: [{approved}, {rejected}],
      backgroundColor: ['rgba(16,185,129,0.8)', 'rgba(239,68,68,0.7)'],
      borderColor: ['#10b981', '#ef4444'],
      borderWidth: 2,
    }}]
  }},
  options: {{
    plugins: {{
      legend: {{ labels: {{ color: '#94a3b8', font: {{ size: 12 }} }} }},
      tooltip: {{ callbacks: {{ label: (c) => ` ${{c.label}}: ${{c.raw}}` }} }}
    }},
    cutout: '65%',
  }}
}});

// Confidence Bar
new Chart(document.getElementById('confidenceChart'), {{
  type: 'bar',
  data: {{
    labels: ['High', 'Medium', 'Low'],
    datasets: [{{
      label: 'Recommendations',
      data: [{conf_dist.get("High", 0)}, {conf_dist.get("Medium", 0)}, {conf_dist.get("Low", 0)}],
      backgroundColor: ['rgba(16,185,129,0.7)', 'rgba(245,158,11,0.7)', 'rgba(239,68,68,0.7)'],
      borderColor: ['#10b981', '#f59e0b', '#ef4444'],
      borderWidth: 1.5,
      borderRadius: 6,
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
      y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }}, beginAtZero: true }},
    }}
  }}
}});

// Disease accuracy chart
new Chart(document.getElementById('diseaseChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(disease_labels)},
    datasets: [{{
      label: 'Retrieval Accuracy (%)',
      data: {json.dumps(disease_accs)},
      backgroundColor: 'rgba(59,130,246,0.6)',
      borderColor: '#3b82f6',
      borderWidth: 1.5,
      borderRadius: 5,
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#94a3b8', maxRotation: 45 }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
      y: {{ min: 0, max: 100, ticks: {{ color: '#94a3b8', callback: (v) => v + '%' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
    }}
  }}
}});
</script>
</body>
</html>"""
    return html


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Patient IQ — Evaluation Report Generator")
    print("=" * 60 + "\n")

    memory_metrics = compute_memory_retrieval_accuracy()
    critique_metrics = compute_critique_metrics()
    dataset_stats = compute_dataset_stats()

    html = generate_html_report(memory_metrics, critique_metrics, dataset_stats)

    with open(REPORT_PATH, "w") as f:
        f.write(html)

    print(f"\n{'=' * 60}")
    print(f"  ✅ Report saved: {REPORT_PATH}")
    print(f"{'=' * 60}")
    print(f"\n  Memory Retrieval Accuracy : {memory_metrics.get('accuracy_pct', 0)}%")
    print(f"  Self-Correction Rate      : {critique_metrics.get('self_correction_rate', 0)}%")
    print(f"  Hallucination Rate        : {critique_metrics.get('hallucination_rate', 0)}%")
    print(f"  Avg Critique Score        : {critique_metrics.get('avg_critique_score', 0)}")
    print(f"\n  Open: file://{REPORT_PATH}\n")
