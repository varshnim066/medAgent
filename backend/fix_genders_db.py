"""
fix_genders_db.py
-----------------
Updates the existing clinical.db and patient_data.json to ensure 
that the gender assignment matches the first name.
"""

import json
import sqlite3
from pathlib import Path
from generate_dataset import GENDER_MAP

def get_connection():
    db_path = Path(__file__).parent / "clinical.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def fix_database():
    print("Fixing gender in clinical.db...")
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT patient_id, name, gender FROM patients")
    patients = cursor.fetchall()
    
    updated_count = 0
    for p in patients:
        first_name = p["name"].split()[0]
        correct_gender = GENDER_MAP.get(first_name, "Male")
        
        if p["gender"] != correct_gender:
            cursor.execute("UPDATE patients SET gender = ? WHERE patient_id = ?", (correct_gender, p["patient_id"]))
            updated_count += 1
            
    conn.commit()
    conn.close()
    print(f"Updated {updated_count} records in database.")

def fix_json():
    print("Fixing gender in patient_data.json...")
    json_path = Path(__file__).parent / "patient_data.json"
    if not json_path.exists():
        print("patient_data.json not found.")
        return
        
    with open(json_path, "r") as f:
        data = json.load(f)
        
    updated_count = 0
    for p in data:
        first_name = p["name"].split()[0]
        correct_gender = GENDER_MAP.get(first_name, "Male")
        
        if p["gender"] != correct_gender:
            p["gender"] = correct_gender
            updated_count += 1
            
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"Updated {updated_count} records in JSON.")

if __name__ == "__main__":
    fix_database()
    fix_json()
    print("Gender fix complete.")
