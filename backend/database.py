"""
database.py
-----------
SQLite database setup and all query functions.
Fully normalized tables with strict foreign keys.
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "clinical.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    # Enable foreign keys in SQLite
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Patients Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            blood_group TEXT,
            smoking TEXT,
            alcohol TEXT,
            exercise TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # 2. Allergies Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allergies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            allergy TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_allergies_patient ON allergies(patient_id)")

    # 3. Past Medical History
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS past_medical_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            condition TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
        )
    """)

    # 4. Past Surgical History
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS past_surgical_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            surgery TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
        )
    """)

    # 5. Family History
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            history TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
        )
    """)

    # 6. Visits Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            visit_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            visit_date TEXT,
            chief_complaint TEXT,
            hpi TEXT,
            clinical_notes TEXT,
            doctor_assessment TEXT,
            treatment_plan TEXT,
            follow_up_advice TEXT,
            doctor_approval INTEGER DEFAULT 0,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_visits_patient ON visits(patient_id)")

    # 7. Symptoms
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS symptoms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id TEXT NOT NULL,
            symptom TEXT NOT NULL,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE CASCADE
        )
    """)

    # 8. Medications
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id TEXT NOT NULL,
            medication TEXT NOT NULL,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE CASCADE
        )
    """)

    # 9. Diagnoses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnoses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id TEXT NOT NULL,
            icd10_code TEXT,
            icd10_description TEXT,
            snomed_concept TEXT,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE CASCADE
        )
    """)

    # 10. Vitals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vitals (
            visit_id TEXT PRIMARY KEY,
            systolic INTEGER,
            diastolic INTEGER,
            pulse INTEGER,
            temperature REAL,
            respiratory_rate INTEGER,
            spo2 INTEGER,
            height INTEGER,
            weight INTEGER,
            bmi REAL,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE CASCADE
        )
    """)

    # 11. Labs (JSON fallback for complex categories or fully relational)
    # Storing category, test_name, value
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS labs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id TEXT NOT NULL,
            category TEXT,
            test_name TEXT,
            test_value TEXT,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE CASCADE
        )
    """)

    # 12. Imaging
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS imaging (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id TEXT NOT NULL,
            modality TEXT,
            finding TEXT,
            impression TEXT,
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id) ON DELETE CASCADE
        )
    """)
    
    # ── Recommendations table (approved only) ──────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            rec_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id      TEXT NOT NULL,
            visit_id        TEXT NOT NULL,
            case_summary    TEXT,
            considerations  TEXT,
            missing_info    TEXT,
            investigations  TEXT,
            follow_up       TEXT,
            confidence      TEXT,
            confidence_score REAL,
            reasoning_trace TEXT,
            critique_text   TEXT,
            guidelines_used TEXT,
            approved_by     TEXT DEFAULT 'Doctor',
            approved_at     TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id)
        )
    """)

    # ── Approval history (all decisions, approved + rejected) ──────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approval_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id  TEXT NOT NULL,
            visit_id    TEXT NOT NULL,
            decision    TEXT NOT NULL,
            decided_at  TEXT DEFAULT (datetime('now')),
            notes       TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (visit_id) REFERENCES visits(visit_id)
        )
    """)

    conn.commit()
    conn.close()


def insert_patient(patient: dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM patients WHERE patient_id = ?", (patient["patient_id"],))
    if cursor.fetchone():
        conn.close()
        return  # Skip if exists

    lifestyle = patient.get("lifestyle", {})
    cursor.execute("""
        INSERT INTO patients (patient_id, name, age, gender, blood_group, smoking, alcohol, exercise)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        patient["patient_id"], patient["name"], patient["age"], patient["gender"], patient.get("blood_group", ""),
        lifestyle.get("smoking", ""), lifestyle.get("alcohol", ""), lifestyle.get("exercise", "")
    ))

    for allergy in patient.get("allergies", []):
        cursor.execute("INSERT INTO allergies (patient_id, allergy) VALUES (?, ?)", (patient["patient_id"], allergy))
        
    for pmh in patient.get("past_medical_history", []):
        cursor.execute("INSERT INTO past_medical_history (patient_id, condition) VALUES (?, ?)", (patient["patient_id"], pmh))

    for psh in patient.get("past_surgical_history", []):
        cursor.execute("INSERT INTO past_surgical_history (patient_id, surgery) VALUES (?, ?)", (patient["patient_id"], psh))

    for fh in patient.get("family_history", []):
        cursor.execute("INSERT INTO family_history (patient_id, history) VALUES (?, ?)", (patient["patient_id"], fh))

    conn.commit()
    conn.close()


def insert_visit(visit: dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM visits WHERE visit_id = ?", (visit["visit_id"],))
    if cursor.fetchone():
        conn.close()
        return

    cursor.execute("""
        INSERT INTO visits (visit_id, patient_id, visit_date, chief_complaint, hpi, clinical_notes, 
                            doctor_assessment, treatment_plan, follow_up_advice, doctor_approval)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        visit["visit_id"], visit["patient_id"], visit["date"], visit["chief_complaint"], visit.get("hpi", ""),
        visit.get("clinical_notes", ""), visit.get("doctor_assessment", ""), visit.get("treatment_plan", ""),
        visit.get("follow_up_advice", ""), 1 if visit.get("doctor_approval", False) else 0
    ))

    for sym in visit.get("symptoms", []):
        cursor.execute("INSERT INTO symptoms (visit_id, symptom) VALUES (?, ?)", (visit["visit_id"], sym))
        
    for med in visit.get("medications", []):
        cursor.execute("INSERT INTO medications (visit_id, medication) VALUES (?, ?)", (visit["visit_id"], med))

    cursor.execute("""
        INSERT INTO diagnoses (visit_id, icd10_code, icd10_description, snomed_concept)
        VALUES (?, ?, ?, ?)
    """, (visit["visit_id"], visit.get("icd10_code", ""), visit.get("icd10_description", ""), visit.get("snomed_concept", "")))

    v = visit.get("vitals", {})
    bp = v.get("blood_pressure", {})
    if isinstance(bp, str):
        # Fallback for old string format if it ever appears
        systolic, diastolic = 120, 80
    else:
        systolic = bp.get("systolic")
        diastolic = bp.get("diastolic")

    cursor.execute("""
        INSERT INTO vitals (visit_id, systolic, diastolic, pulse, temperature, respiratory_rate, spo2, height, weight, bmi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        visit["visit_id"], systolic, diastolic,
        v.get("pulse"), v.get("temperature"), v.get("respiratory_rate"),
        v.get("spo2"), v.get("height"), v.get("weight"), v.get("bmi")
    ))

    labs = visit.get("labs", {})
    for category, tests in labs.items():
        if isinstance(tests, dict):
            for test_name, value in tests.items():
                cursor.execute("INSERT INTO labs (visit_id, category, test_name, test_value) VALUES (?, ?, ?, ?)",
                               (visit["visit_id"], category, test_name, str(value)))
                               
    imaging = visit.get("imaging", {})
    for modality, details in imaging.items():
        if isinstance(details, dict):
            cursor.execute("INSERT INTO imaging (visit_id, modality, finding, impression) VALUES (?, ?, ?, ?)",
                           (visit["visit_id"], modality, details.get("finding", ""), details.get("impression", "")))

    conn.commit()
    conn.close()

def _hydrate_patient(conn, row):
    p = dict(row)
    cursor = conn.cursor()
    
    p["lifestyle"] = {
        "smoking": p.pop("smoking"),
        "alcohol": p.pop("alcohol"),
        "exercise": p.pop("exercise")
    }
    
    cursor.execute("SELECT allergy FROM allergies WHERE patient_id = ?", (p["patient_id"],))
    p["allergies"] = [r["allergy"] for r in cursor.fetchall()]
    
    cursor.execute("SELECT condition FROM past_medical_history WHERE patient_id = ?", (p["patient_id"],))
    p["past_medical_history"] = [r["condition"] for r in cursor.fetchall()]
    # Keep past_medical for backward compatibility in the app
    p["past_medical"] = p["past_medical_history"]
    
    cursor.execute("SELECT surgery FROM past_surgical_history WHERE patient_id = ?", (p["patient_id"],))
    p["past_surgical_history"] = [r["surgery"] for r in cursor.fetchall()]
    
    cursor.execute("SELECT history FROM family_history WHERE patient_id = ?", (p["patient_id"],))
    p["family_history"] = [r["history"] for r in cursor.fetchall()]
    
    return p

def _hydrate_visit(conn, row):
    v = dict(row)
    # Remap visit_date to date for backward compatibility
    v["date"] = v.pop("visit_date")
    cursor = conn.cursor()
    vid = v["visit_id"]
    
    cursor.execute("SELECT symptom FROM symptoms WHERE visit_id = ?", (vid,))
    v["symptoms"] = [r["symptom"] for r in cursor.fetchall()]
    
    cursor.execute("SELECT medication FROM medications WHERE visit_id = ?", (vid,))
    v["medications"] = [r["medication"] for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM diagnoses WHERE visit_id = ?", (vid,))
    diag = cursor.fetchone()
    if diag:
        v["icd10_code"] = diag["icd10_code"]
        v["icd10_description"] = diag["icd10_description"]
        v["snomed_concept"] = diag["snomed_concept"]
        
    cursor.execute("SELECT * FROM vitals WHERE visit_id = ?", (vid,))
    vit = cursor.fetchone()
    if vit:
        v["vitals"] = {
            "blood_pressure": {"systolic": vit["systolic"], "diastolic": vit["diastolic"]},
            "pulse": vit["pulse"],
            "temperature": vit["temperature"],
            "respiratory_rate": vit["respiratory_rate"],
            "spo2": vit["spo2"],
            "height": vit["height"],
            "weight": vit["weight"],
            "bmi": vit["bmi"]
        }
    else:
        v["vitals"] = {}

    cursor.execute("SELECT category, test_name, test_value FROM labs WHERE visit_id = ?", (vid,))
    labs = {}
    for r in cursor.fetchall():
        cat = r["category"]
        if cat not in labs:
            labs[cat] = {}
        # Try to parse numeric
        val = r["test_value"]
        try:
            if "." in val:
                val = float(val)
            else:
                val = int(val)
        except:
            pass
        labs[cat][r["test_name"]] = val
    v["labs"] = labs
    
    cursor.execute("SELECT modality, finding, impression FROM imaging WHERE visit_id = ?", (vid,))
    img = {}
    for r in cursor.fetchall():
        img[r["modality"]] = {"finding": r["finding"], "impression": r["impression"]}
    v["imaging"] = img
    
    return v


def get_all_patients() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, COUNT(v.visit_id) AS visit_count
        FROM patients p
        LEFT JOIN visits v ON p.patient_id = v.patient_id
        GROUP BY p.patient_id
        ORDER BY p.name
    """)
    rows = cursor.fetchall()
    
    patients = []
    for r in rows:
        p = _hydrate_patient(conn, r)
        p["visit_count"] = dict(r).get("visit_count", 0)
        patients.append(p)
        
    conn.close()
    return patients


def get_patient_by_id(patient_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    p = _hydrate_patient(conn, row)
    conn.close()
    return p


def get_visits_by_patient(patient_id: str) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM visits WHERE patient_id = ? ORDER BY visit_date ASC", (patient_id,))
    rows = cursor.fetchall()
    
    visits = []
    for r in rows:
        visits.append(_hydrate_visit(conn, r))
        
    conn.close()
    return visits


def get_visit_by_id(visit_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM visits WHERE visit_id = ?", (visit_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    v = _hydrate_visit(conn, row)
    conn.close()
    return v


def save_recommendation(rec: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recommendations
        (patient_id, visit_id, case_summary, considerations, missing_info,
         investigations, follow_up, confidence, confidence_score,
         reasoning_trace, critique_text, guidelines_used)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        rec["patient_id"],
        rec["visit_id"],
        rec.get("case_summary", ""),
        json.dumps(rec.get("considerations", [])),
        json.dumps(rec.get("missing_info", [])),
        json.dumps(rec.get("investigations", [])),
        json.dumps(rec.get("follow_up", [])),
        rec.get("confidence", "Low"),
        rec.get("confidence_score", 0.0),
        rec.get("reasoning_trace", ""),
        rec.get("critique_text", ""),
        json.dumps(rec.get("guidelines_used", [])),
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_all_recommendations() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, p.name AS patient_name
        FROM recommendations r
        JOIN patients p ON r.patient_id = p.patient_id
        ORDER BY r.approved_at DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        for field in ["considerations", "missing_info", "investigations", "follow_up", "guidelines_used"]:
            r[field] = json.loads(r.get(field) or "[]")
    return rows


def log_approval(patient_id: str, visit_id: str, decision: str, notes: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO approval_history (patient_id, visit_id, decision, notes)
        VALUES (?,?,?,?)
    """, (patient_id, visit_id, decision, notes))
    conn.commit()
    conn.close()


def get_dashboard_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS cnt FROM patients")
    total_patients = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM visits")
    total_visits = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) AS cnt FROM recommendations")
    approved_recs = cursor.fetchone()["cnt"]

    cursor.execute("""
        SELECT COUNT(*) AS cnt FROM visits v
        WHERE NOT EXISTS (
            SELECT 1 FROM recommendations r
            WHERE r.visit_id = v.visit_id
        )
    """)
    pending_reviews = cursor.fetchone()["cnt"]

    cursor.execute("""
        SELECT icd10_description AS disease, COUNT(*) AS count
        FROM diagnoses
        WHERE icd10_description IS NOT NULL AND icd10_description != ''
        GROUP BY icd10_description
        ORDER BY count DESC
        LIMIT 15
    """)
    disease_dist = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT strftime('%Y-%m', visit_date) AS month, COUNT(*) AS count
        FROM visits
        GROUP BY month
        ORDER BY month
    """)
    visit_trend = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "total_patients": total_patients,
        "total_visits": total_visits,
        "approved_recommendations": approved_recs,
        "pending_reviews": pending_reviews,
        "disease_distribution": disease_dist,
        "visit_trend": visit_trend,
    }
