"""
generate_dataset.py
-------------------
Generates 100 synthetic patients with 3-6 visits each.
Covers 38+ diseases with realistic lab values, vitals, medications,
and imaging reports. Saves output to patient_data.json.

Run:
    python generate_dataset.py
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ── Disease templates ────────────────────────────────────────────────────────
DISEASES = [
    {
        "name": "Diabetes Mellitus Type 2",
        "icd10": "E11.9",
        "snomed": "44054006",
        "symptoms": ["polyuria", "polydipsia", "fatigue", "blurred vision", "weight loss"],
        "labs_template": {"HbA1c": (7.5, 11.0), "RBS": (180, 350), "Creatinine": (0.9, 2.5), "eGFR": (35, 90)},
        "medications": ["Metformin 500mg BD", "Glipizide 5mg OD", "Insulin Glargine 10U HS"],
        "assessment_base": "Patient presents with poorly controlled Type 2 Diabetes. HbA1c remains elevated.",
    },
    {
        "name": "Hypertension",
        "icd10": "I10",
        "snomed": "38341003",
        "symptoms": ["headache", "dizziness", "blurred vision", "palpitations"],
        "labs_template": {"Creatinine": (0.8, 1.8), "eGFR": (50, 100), "Na": (138, 148), "K": (3.8, 5.2)},
        "medications": ["Amlodipine 5mg OD", "Losartan 50mg OD", "Hydrochlorothiazide 12.5mg OD"],
        "assessment_base": "Hypertension with suboptimal blood pressure control.",
    },
    {
        "name": "Asthma",
        "icd10": "J45.9",
        "snomed": "195967001",
        "symptoms": ["wheezing", "shortness of breath", "chest tightness", "cough"],
        "labs_template": {"WBC": (5.0, 12.0), "Eosinophils": (0.3, 1.5)},
        "medications": ["Salbutamol MDI PRN", "Budesonide 200mcg BD", "Montelukast 10mg OD"],
        "assessment_base": "Asthma with intermittent exacerbations.",
    },
    {
        "name": "COPD",
        "icd10": "J44.1",
        "snomed": "13645005",
        "symptoms": ["chronic cough", "sputum production", "dyspnea on exertion", "wheeze"],
        "labs_template": {"WBC": (7.0, 14.0), "HGB": (10.5, 14.5)},
        "medications": ["Tiotropium 18mcg OD", "Formoterol 12mcg BD", "Prednisolone 30mg (acute)"],
        "assessment_base": "COPD with frequent exacerbations. Spirometry shows obstructive pattern.",
    },
    {
        "name": "Tuberculosis",
        "icd10": "A15.0",
        "snomed": "56717001",
        "symptoms": ["productive cough", "hemoptysis", "night sweats", "weight loss", "fever"],
        "labs_template": {"WBC": (10.0, 16.0), "ESR": (60, 120), "CRP": (30, 80), "HGB": (8.0, 12.0)},
        "medications": ["Isoniazid 300mg OD", "Rifampicin 600mg OD", "Pyrazinamide 1500mg OD", "Ethambutol 1200mg OD"],
        "assessment_base": "Pulmonary tuberculosis on DOTS therapy.",
    },
    {
        "name": "COVID-19",
        "icd10": "U07.1",
        "snomed": "840539006",
        "symptoms": ["fever", "dry cough", "fatigue", "loss of taste", "loss of smell", "dyspnea"],
        "labs_template": {"WBC": (3.5, 12.0), "CRP": (20, 150), "LDH": (250, 600), "D-Dimer": (0.5, 5.0)},
        "medications": ["Paracetamol 1g QDS", "Dexamethasone 6mg OD", "Enoxaparin 40mg SC OD"],
        "assessment_base": "COVID-19 pneumonia with moderate severity.",
    },
    {
        "name": "Pneumonia",
        "icd10": "J18.9",
        "snomed": "233604007",
        "symptoms": ["productive cough", "fever", "pleuritic chest pain", "dyspnea", "rigors"],
        "labs_template": {"WBC": (12.0, 22.0), "CRP": (50, 200), "Neutrophils": (75, 90)},
        "medications": ["Amoxicillin-Clavulanate 625mg TDS", "Azithromycin 500mg OD", "Paracetamol 1g QDS"],
        "assessment_base": "Community-acquired pneumonia. CURB-65 score assessed.",
    },
    {
        "name": "Dengue Fever",
        "icd10": "A90",
        "snomed": "38362002",
        "symptoms": ["high fever", "severe headache", "retro-orbital pain", "myalgia", "rash", "petechiae"],
        "labs_template": {"WBC": (2.0, 5.0), "Platelets": (20, 100), "HGB": (12.0, 16.0), "Hematocrit": (40, 55)},
        "medications": ["Paracetamol 500mg QDS", "IV Normal Saline 2L", "Oral rehydration"],
        "assessment_base": "Dengue fever with thrombocytopenia. Monitoring for warning signs.",
    },
    {
        "name": "Typhoid Fever",
        "icd10": "A01.0",
        "snomed": "4834000",
        "symptoms": ["step-ladder fever", "abdominal pain", "constipation", "headache", "rose spots"],
        "labs_template": {"WBC": (3.0, 6.0), "ESR": (30, 80), "CRP": (15, 60)},
        "medications": ["Azithromycin 500mg OD x7 days", "Ceftriaxone 2g IV OD"],
        "assessment_base": "Enteric fever confirmed on Widal/blood culture.",
    },
    {
        "name": "Iron Deficiency Anemia",
        "icd10": "D50.9",
        "snomed": "87522002",
        "symptoms": ["fatigue", "pallor", "pica", "exertional dyspnea", "brittle nails", "angular stomatitis"],
        "labs_template": {"HGB": (5.0, 10.0), "MCV": (60, 78), "MCH": (18, 25), "Ferritin": (3, 15)},
        "medications": ["Ferrous Sulfate 200mg BD", "Vitamin C 500mg OD", "Folic Acid 5mg OD"],
        "assessment_base": "Iron deficiency anemia. Cause under investigation.",
    },
    {
        "name": "Hypothyroidism",
        "icd10": "E03.9",
        "snomed": "40930008",
        "symptoms": ["fatigue", "weight gain", "cold intolerance", "constipation", "dry skin", "hair loss"],
        "labs_template": {"TSH": (5.0, 50.0), "fT4": (0.4, 0.8), "TotalCholesterol": (220, 320)},
        "medications": ["Levothyroxine 50mcg OD", "Levothyroxine 75mcg OD", "Levothyroxine 100mcg OD"],
        "assessment_base": "Primary hypothyroidism on levothyroxine replacement.",
    },
    {
        "name": "Hyperthyroidism",
        "icd10": "E05.9",
        "snomed": "34486009",
        "symptoms": ["weight loss", "palpitations", "heat intolerance", "tremor", "anxiety", "exophthalmos"],
        "labs_template": {"TSH": (0.01, 0.3), "fT4": (2.5, 5.0), "fT3": (7.0, 15.0)},
        "medications": ["Methimazole 10mg BD", "Propranolol 40mg BD"],
        "assessment_base": "Graves' disease with hyperthyroidism.",
    },
    {
        "name": "Chronic Kidney Disease",
        "icd10": "N18.3",
        "snomed": "709044004",
        "symptoms": ["fatigue", "ankle edema", "nausea", "decreased urine output", "pruritus"],
        "labs_template": {"Creatinine": (2.0, 6.0), "eGFR": (15, 45), "K": (4.5, 6.0), "HGB": (8.0, 11.0), "Urea": (40, 120)},
        "medications": ["Erythropoietin 4000U SC weekly", "Calcium Carbonate 500mg TDS", "Furosemide 40mg OD"],
        "assessment_base": "CKD Stage 3-4. Nephrology referral made.",
    },
    {
        "name": "Acute Kidney Injury",
        "icd10": "N17.9",
        "snomed": "14669001",
        "symptoms": ["decreased urine output", "edema", "nausea", "confusion"],
        "labs_template": {"Creatinine": (2.5, 8.0), "Urea": (60, 200), "K": (5.0, 7.0), "eGFR": (10, 30)},
        "medications": ["IV Normal Saline 1L over 4h", "Furosemide 80mg IV", "Sodium Bicarbonate"],
        "assessment_base": "Acute kidney injury. Cause under investigation. Fluid and electrolyte management.",
    },
    {
        "name": "Liver Disease",
        "icd10": "K72.0",
        "snomed": "197321007",
        "symptoms": ["jaundice", "abdominal distension", "fatigue", "easy bruising", "pruritus"],
        "labs_template": {"ALT": (80, 400), "AST": (60, 350), "ALP": (150, 600), "Bilirubin": (2.0, 15.0), "Albumin": (2.0, 3.2)},
        "medications": ["Spironolactone 100mg OD", "Furosemide 40mg OD", "Lactulose 30ml TDS", "Rifaximin 550mg BD"],
        "assessment_base": "Decompensated liver cirrhosis with ascites.",
    },
    {
        "name": "Gallstones",
        "icd10": "K80.2",
        "snomed": "266474003",
        "symptoms": ["right upper quadrant pain", "nausea", "vomiting", "fatty food intolerance", "jaundice"],
        "labs_template": {"ALT": (40, 200), "ALP": (100, 400), "Bilirubin": (1.0, 8.0), "WBC": (8.0, 16.0)},
        "medications": ["Diclofenac 75mg IM PRN", "Omeprazole 20mg OD", "Ursodeoxycholic acid 500mg BD"],
        "assessment_base": "Symptomatic cholelithiasis. Surgical referral considered.",
    },
    {
        "name": "Migraine",
        "icd10": "G43.9",
        "snomed": "37796009",
        "symptoms": ["severe unilateral headache", "nausea", "vomiting", "photophobia", "phonophobia", "aura"],
        "labs_template": {"WBC": (5.0, 10.0), "CRP": (2.0, 8.0)},
        "medications": ["Sumatriptan 50mg PRN", "Propranolol 40mg BD", "Amitriptyline 25mg OD"],
        "assessment_base": "Migraine with and without aura. Preventive therapy initiated.",
    },
    {
        "name": "Ischemic Stroke",
        "icd10": "I63.9",
        "snomed": "422504002",
        "symptoms": ["sudden hemiplegia", "dysarthria", "facial droop", "dysphagia", "confusion"],
        "labs_template": {"Glucose": (100, 250), "WBC": (8.0, 14.0), "INR": (1.0, 3.0)},
        "medications": ["Aspirin 300mg STAT", "Atorvastatin 80mg OD", "Ramipril 5mg OD", "Clopidogrel 75mg OD"],
        "assessment_base": "Acute ischemic stroke. Thrombolysis eligibility assessed.",
    },
    {
        "name": "Heart Failure",
        "icd10": "I50.0",
        "snomed": "84114007",
        "symptoms": ["orthopnea", "paroxysmal nocturnal dyspnea", "ankle edema", "exertional dyspnea", "fatigue"],
        "labs_template": {"BNP": (300, 2000), "Creatinine": (1.0, 2.5), "Na": (128, 138), "HGB": (9.0, 13.0)},
        "medications": ["Furosemide 40mg OD", "Bisoprolol 5mg OD", "Ramipril 10mg OD", "Spironolactone 25mg OD"],
        "assessment_base": "Congestive cardiac failure with reduced ejection fraction.",
    },
    {
        "name": "Coronary Artery Disease",
        "icd10": "I25.1",
        "snomed": "53741008",
        "symptoms": ["chest pain on exertion", "dyspnea", "palpitations", "radiation to left arm"],
        "labs_template": {"Cholesterol": (200, 300), "LDL": (130, 220), "Troponin": (0.01, 0.5), "CK-MB": (10, 80)},
        "medications": ["Aspirin 75mg OD", "Atorvastatin 40mg OD", "Metoprolol 50mg BD", "Isosorbide mononitrate 20mg BD"],
        "assessment_base": "Stable coronary artery disease on optimal medical therapy.",
    },
    {
        "name": "Depression",
        "icd10": "F32.1",
        "snomed": "35489007",
        "symptoms": ["persistent low mood", "anhedonia", "insomnia", "poor concentration", "fatigue", "suicidal ideation"],
        "labs_template": {"TSH": (0.5, 4.0), "Vit_D": (10, 30), "HGB": (10.0, 14.0)},
        "medications": ["Sertraline 50mg OD", "Escitalopram 10mg OD", "Mirtazapine 15mg ON"],
        "assessment_base": "Moderate depressive episode. CBT referral made.",
    },
    {
        "name": "Anxiety Disorder",
        "icd10": "F41.1",
        "snomed": "197480006",
        "symptoms": ["excessive worry", "palpitations", "sweating", "insomnia", "restlessness", "panic attacks"],
        "labs_template": {"TSH": (0.5, 4.0), "Glucose": (80, 120)},
        "medications": ["Sertraline 50mg OD", "Propranolol 20mg PRN", "Clonazepam 0.5mg PRN"],
        "assessment_base": "Generalized anxiety disorder. Psychotherapy recommended.",
    },
    {
        "name": "Leukemia",
        "icd10": "C91.0",
        "snomed": "91861009",
        "symptoms": ["fatigue", "easy bruising", "frequent infections", "bone pain", "lymphadenopathy", "splenomegaly"],
        "labs_template": {"WBC": (30.0, 200.0), "HGB": (6.0, 10.0), "Platelets": (20, 80), "Blasts": (20, 90)},
        "medications": ["Imatinib 400mg OD", "Prednisolone 60mg OD", "Allopurinol 300mg OD"],
        "assessment_base": "Chronic/acute leukemia. Bone marrow biopsy confirmed. Oncology co-management.",
    },
    {
        "name": "Lymphoma",
        "icd10": "C85.9",
        "snomed": "118600007",
        "symptoms": ["painless lymphadenopathy", "B symptoms (fever, night sweats, weight loss)", "pruritus", "splenomegaly"],
        "labs_template": {"WBC": (8.0, 20.0), "LDH": (300, 800), "ESR": (50, 120), "HGB": (8.0, 13.0)},
        "medications": ["CHOP chemotherapy", "Rituximab 375mg/m2 IV", "Ondansetron 8mg TDS"],
        "assessment_base": "Non-Hodgkin lymphoma. Staging with PET-CT completed.",
    },
    {
        "name": "Rheumatoid Arthritis",
        "icd10": "M05.9",
        "snomed": "69896004",
        "symptoms": ["symmetrical joint pain", "morning stiffness >1h", "joint swelling", "fatigue", "subcutaneous nodules"],
        "labs_template": {"CRP": (20, 80), "ESR": (40, 100), "RF": (50, 300), "Anti-CCP": (30, 200)},
        "medications": ["Methotrexate 15mg weekly", "Folic Acid 5mg weekly", "Hydroxychloroquine 200mg BD", "Prednisolone 5mg OD"],
        "assessment_base": "Seropositive rheumatoid arthritis. Disease activity assessed with DAS28.",
    },
    {
        "name": "Systemic Lupus Erythematosus",
        "icd10": "M32.9",
        "snomed": "55464009",
        "symptoms": ["malar rash", "photosensitivity", "joint pain", "fatigue", "oral ulcers", "hair loss", "nephritis"],
        "labs_template": {"ANA": (1, 1), "Anti-dsDNA": (50, 400), "Complement_C3": (50, 90), "WBC": (2.5, 5.0), "Platelets": (80, 150)},
        "medications": ["Hydroxychloroquine 200mg BD", "Prednisolone 20mg OD", "Mycophenolate 1g BD"],
        "assessment_base": "Active SLE with lupus nephritis. Nephrology referral made.",
    },
    {
        "name": "Autoimmune Hepatitis",
        "icd10": "K75.4",
        "snomed": "235890007",
        "symptoms": ["jaundice", "fatigue", "abdominal pain", "dark urine", "arthralgia"],
        "labs_template": {"ALT": (200, 1000), "AST": (180, 900), "ANA": (1, 1), "IgG": (18, 50), "Bilirubin": (2.0, 12.0)},
        "medications": ["Prednisolone 40mg OD", "Azathioprine 50mg OD"],
        "assessment_base": "Autoimmune hepatitis. Liver biopsy confirms interface hepatitis.",
    },
    {
        "name": "Vitamin B12 Deficiency",
        "icd10": "E53.8",
        "snomed": "190634004",
        "symptoms": ["fatigue", "pallor", "glossitis", "peripheral neuropathy", "memory loss", "depression"],
        "labs_template": {"HGB": (7.0, 11.0), "MCV": (100, 130), "Vit_B12": (50, 200)},
        "medications": ["Cyanocobalamin 1000mcg IM weekly x4 then monthly", "Folic Acid 5mg OD"],
        "assessment_base": "Vitamin B12 deficiency megaloblastic anemia. Pernicious anemia suspected.",
    },
    {
        "name": "Obesity",
        "icd10": "E66.9",
        "snomed": "414916001",
        "symptoms": ["weight gain", "exertional dyspnea", "knee pain", "snoring", "fatigue"],
        "labs_template": {"Glucose": (90, 140), "TotalCholesterol": (200, 280), "TG": (150, 400), "HbA1c": (5.7, 7.0)},
        "medications": ["Orlistat 120mg TDS", "Metformin 500mg BD", "Lifestyle counseling"],
        "assessment_base": "Class II/III obesity with metabolic syndrome features.",
    },
    {
        "name": "Urinary Tract Infection",
        "icd10": "N30.0",
        "snomed": "68566005",
        "symptoms": ["dysuria", "frequency", "urgency", "suprapubic pain", "cloudy urine", "fever"],
        "labs_template": {"WBC": (10.0, 18.0), "CRP": (15, 80), "Nitrites": (1, 1)},
        "medications": ["Nitrofurantoin 100mg BD x5d", "Co-amoxiclav 625mg TDS", "Trimethoprim 200mg BD"],
        "assessment_base": "Recurrent urinary tract infection. Urine culture and sensitivity guided treatment.",
    },
    {
        "name": "Kidney Stones",
        "icd10": "N20.0",
        "snomed": "95570007",
        "symptoms": ["severe flank pain", "hematuria", "nausea", "vomiting", "radiating pain to groin"],
        "labs_template": {"Creatinine": (0.8, 2.0), "Uric_Acid": (7.0, 12.0), "Calcium": (2.5, 3.2)},
        "medications": ["Diclofenac 75mg IM PRN", "Tamsulosin 0.4mg OD", "Morphine 10mg IV PRN"],
        "assessment_base": "Renal calculi on CT KUB. Conservative management if <10mm.",
    },
    {
        "name": "Acute Appendicitis",
        "icd10": "K37",
        "snomed": "85189001",
        "symptoms": ["periumbilical pain migrating to RIF", "nausea", "vomiting", "anorexia", "fever", "rebound tenderness"],
        "labs_template": {"WBC": (13.0, 22.0), "CRP": (40, 200), "Neutrophils": (78, 92)},
        "medications": ["Co-amoxiclav 1.2g IV TDS", "Metronidazole 500mg IV TDS", "Morphine 10mg IV PRN"],
        "assessment_base": "Acute appendicitis. Surgical review for laparoscopic appendectomy.",
    },
    {
        "name": "Pancreatitis",
        "icd10": "K85.9",
        "snomed": "75694006",
        "symptoms": ["severe epigastric pain radiating to back", "nausea", "vomiting", "fever", "abdominal rigidity"],
        "labs_template": {"Amylase": (300, 2000), "Lipase": (400, 3000), "WBC": (12.0, 20.0), "CRP": (50, 300)},
        "medications": ["IV Normal Saline 3L/day", "Morphine 10mg IV PRN", "Ondansetron 8mg IV", "Nil by mouth"],
        "assessment_base": "Acute pancreatitis. Ranson's criteria scored. Gallstone etiology suspected.",
    },
    {
        "name": "GERD",
        "icd10": "K21.0",
        "snomed": "235595009",
        "symptoms": ["heartburn", "acid regurgitation", "dysphagia", "chest pain", "nocturnal symptoms"],
        "labs_template": {"Hematocrit": (35, 45), "HGB": (11.0, 15.0)},
        "medications": ["Omeprazole 20mg OD", "Pantoprazole 40mg OD", "Gaviscon PRN", "Domperidone 10mg TDS"],
        "assessment_base": "Gastroesophageal reflux disease. Upper GI endoscopy recommended.",
    },
    {
        "name": "Peptic Ulcer Disease",
        "icd10": "K27.9",
        "snomed": "13200003",
        "symptoms": ["epigastric pain", "nausea", "vomiting", "melena", "hematemesis", "early satiety"],
        "labs_template": {"HGB": (7.0, 12.0), "WBC": (8.0, 14.0), "CRP": (10, 50)},
        "medications": ["Omeprazole 40mg BD", "Amoxicillin 1g BD", "Clarithromycin 500mg BD"],
        "assessment_base": "Peptic ulcer disease. H. pylori testing and eradication therapy.",
    },
    {
        "name": "Dengue Hemorrhagic Fever",
        "icd10": "A91",
        "snomed": "41009002",
        "symptoms": ["high fever", "severe bleeding", "petechiae", "ecchymosis", "plasma leakage", "shock"],
        "labs_template": {"Platelets": (10, 50), "Hematocrit": (45, 60), "WBC": (1.5, 4.0)},
        "medications": ["IV Lactated Ringer's 10 mL/kg/hr", "Platelet transfusion", "Paracetamol PRN"],
        "assessment_base": "Dengue hemorrhagic fever Grade II. ICU monitoring required.",
    },
    {
        "name": "Hyperlipidemia",
        "icd10": "E78.5",
        "snomed": "55822004",
        "symptoms": ["usually asymptomatic", "xanthomas", "xanthelasmas", "corneal arcus"],
        "labs_template": {"TotalCholesterol": (250, 380), "LDL": (160, 280), "TG": (200, 500), "HDL": (25, 40)},
        "medications": ["Atorvastatin 40mg OD", "Rosuvastatin 20mg OD", "Ezetimibe 10mg OD"],
        "assessment_base": "Mixed hyperlipidemia. Cardiovascular risk stratification performed.",
    },
]

FIRST_NAMES = ["Arjun", "Priya", "Mohammed", "Sneha", "Rahul", "Fatima", "Vikram", "Ananya", "Suresh",
               "Meera", "Aditya", "Kavya", "Rohan", "Divya", "Manish", "Pooja", "Rajesh", "Sunita",
               "Deepak", "Lakshmi", "Karthik", "Shalini", "Amit", "Neha", "Vinod", "Radha", "Harish",
               "Geeta", "Sanjay", "Anjali", "Pavan", "Suma", "Girish", "Usha", "Naveen", "Rekha",
               "Vivek", "Sarala", "Krishna", "Asha", "Mohan", "Nirmala", "Sunil", "Geetha", "Arun",
               "Shanti", "Ravi", "Lalitha", "Ganesh", "Padma"]

LAST_NAMES = ["Kumar", "Sharma", "Patel", "Singh", "Reddy", "Nair", "Iyer", "Gupta", "Rao", "Joshi",
              "Pillai", "Menon", "Shah", "Mehta", "Verma", "Choudary", "Naidu", "Rajan", "Bhat",
              "Hegde", "Shetty", "Kamath", "Murthy", "Gowda", "Patil", "Desai", "Jain", "Agarwal",
              "Pandey", "Mishra", "Tiwari", "Chandra", "Dubey", "Tripathi", "Srivastava", "Shukla",
              "Malhotra", "Kapoor", "Khanna", "Bose", "Das", "Sen", "Chatterjee", "Banerjee",
              "Ghosh", "Mukherjee", "Roy", "Paul", "Dutta", "Sarkar"]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

GENDERS = ["Male", "Female"]

GENDER_MAP = {
    "Arjun": "Male", "Priya": "Female", "Mohammed": "Male", "Sneha": "Female", "Rahul": "Male", 
    "Fatima": "Female", "Vikram": "Male", "Ananya": "Female", "Suresh": "Male", "Meera": "Female", 
    "Aditya": "Male", "Kavya": "Female", "Rohan": "Male", "Divya": "Female", "Manish": "Male", 
    "Pooja": "Female", "Rajesh": "Male", "Sunita": "Female", "Deepak": "Male", "Lakshmi": "Female", 
    "Karthik": "Male", "Shalini": "Female", "Amit": "Male", "Neha": "Female", "Vinod": "Male", 
    "Radha": "Female", "Harish": "Male", "Geeta": "Female", "Sanjay": "Male", "Anjali": "Female", 
    "Pavan": "Male", "Suma": "Female", "Girish": "Male", "Usha": "Female", "Naveen": "Male", 
    "Rekha": "Female", "Vivek": "Male", "Sarala": "Female", "Krishna": "Male", "Asha": "Female", 
    "Mohan": "Male", "Nirmala": "Female", "Sunil": "Male", "Geetha": "Female", "Arun": "Male", 
    "Shanti": "Female", "Ravi": "Male", "Lalitha": "Female", "Ganesh": "Male", "Padma": "Female"
}

IMAGING_TYPES = ["X-Ray Chest", "CT Chest", "MRI Brain", "Ultrasound Abdomen", "CT Abdomen",
                 "X-Ray Abdomen", "Ultrasound Pelvis", "MRI Spine", "CT KUB", "Echocardiogram"]

IMAGING_FINDINGS = {
    "Diabetes Mellitus Type 2": {"X-Ray Chest": "No active cardiopulmonary disease", "Ultrasound Abdomen": "Grade 1 fatty liver"},
    "Hypertension": {"X-Ray Chest": "Cardiomegaly. No pulmonary edema", "Echocardiogram": "Concentric LVH. EF 55%"},
    "Asthma": {"X-Ray Chest": "Hyperinflation. No consolidation", "CT Chest": "Air trapping bilaterally"},
    "COPD": {"X-Ray Chest": "Hyperinflation, flattened diaphragm, increased AP diameter", "CT Chest": "Centrilobular emphysema"},
    "Tuberculosis": {"X-Ray Chest": "Right upper lobe cavitating lesion with consolidation", "CT Chest": "Cavitation and tree-in-bud opacities"},
    "COVID-19": {"X-Ray Chest": "Bilateral ground glass opacities", "CT Chest": "Bilateral peripheral consolidations"},
    "Pneumonia": {"X-Ray Chest": "Right lower lobe consolidation", "CT Chest": "Consolidation with air bronchograms"},
    "Dengue Fever": {"X-Ray Chest": "Small right pleural effusion", "Ultrasound Abdomen": "Hepatosplenomegaly, minimal ascites"},
    "Typhoid Fever": {"X-Ray Abdomen": "No bowel perforation", "Ultrasound Abdomen": "Splenomegaly"},
    "Iron Deficiency Anemia": {"X-Ray Chest": "No cardiopulmonary abnormality", "Echocardiogram": "Normal cardiac structure"},
    "Hypothyroidism": {"X-Ray Chest": "Mild cardiomegaly", "Ultrasound Abdomen": "No abnormality"},
    "Hyperthyroidism": {"X-Ray Chest": "Normal heart size", "Echocardiogram": "Hyperdynamic circulation"},
    "Chronic Kidney Disease": {"X-Ray Chest": "Bilateral pleural effusions. Pulmonary edema", "Ultrasound Abdomen": "Bilateral small echogenic kidneys"},
    "Acute Kidney Injury": {"X-Ray Chest": "Pulmonary edema", "Ultrasound Abdomen": "Kidneys enlarged, increased echogenicity"},
    "Liver Disease": {"Ultrasound Abdomen": "Coarse liver echotexture, splenomegaly, ascites", "CT Abdomen": "Cirrhotic liver with portal hypertension"},
    "Gallstones": {"Ultrasound Abdomen": "Multiple gallstones with posterior acoustic shadowing", "CT Abdomen": "Gallbladder distension with calculi"},
    "Migraine": {"MRI Brain": "No structural abnormality detected", "CT Chest": "Normal"},
    "Ischemic Stroke": {"MRI Brain": "Diffusion restriction in left MCA territory", "CT Chest": "Bilateral carotid calcification"},
    "Heart Failure": {"X-Ray Chest": "Cardiomegaly, pulmonary vascular congestion", "Echocardiogram": "Dilated LV, EF 30%, moderate MR"},
    "Coronary Artery Disease": {"X-Ray Chest": "Mild cardiomegaly", "Echocardiogram": "Inferior wall hypokinesia, EF 45%"},
    "Depression": {"MRI Brain": "No structural lesion", "X-Ray Chest": "Normal"},
    "Anxiety Disorder": {"X-Ray Chest": "Normal", "MRI Brain": "No structural abnormality"},
    "Leukemia": {"X-Ray Chest": "Mediastinal lymphadenopathy", "CT Chest": "Mediastinal and hilar lymphadenopathy"},
    "Lymphoma": {"CT Chest": "Bulky mediastinal lymphadenopathy", "CT Abdomen": "Retroperitoneal lymphadenopathy"},
    "Rheumatoid Arthritis": {"X-Ray Chest": "No active disease", "MRI Spine": "Atlantoaxial subluxation"},
    "Systemic Lupus Erythematosus": {"X-Ray Chest": "Bilateral pleural effusions", "Ultrasound Abdomen": "No significant abnormality"},
    "Autoimmune Hepatitis": {"Ultrasound Abdomen": "Hepatomegaly, coarse echotexture", "CT Abdomen": "Heterogeneous liver parenchyma"},
    "Vitamin B12 Deficiency": {"MRI Brain": "Posterior cord signal abnormality", "X-Ray Chest": "Normal"},
    "Obesity": {"X-Ray Chest": "Elevated hemidiaphragm", "Ultrasound Abdomen": "Grade 2 fatty liver"},
    "Urinary Tract Infection": {"Ultrasound Abdomen": "Mild bilateral hydronephrosis", "CT KUB": "No calculi"},
    "Kidney Stones": {"CT KUB": "5mm calculus in right ureter at VUJ", "X-Ray Abdomen": "Radio-opaque calculus"},
    "Acute Appendicitis": {"Ultrasound Abdomen": "Dilated aperistaltic appendix with faecolith", "CT Abdomen": "Perforated appendicitis with periappendiceal fat stranding"},
    "Pancreatitis": {"Ultrasound Abdomen": "Oedematous pancreas, peripancreatic fluid", "CT Abdomen": "Necrotizing pancreatitis with >30% necrosis"},
    "GERD": {"X-Ray Chest": "Normal", "Ultrasound Abdomen": "Sliding hiatus hernia"},
    "Peptic Ulcer Disease": {"X-Ray Abdomen": "No free air under diaphragm", "CT Abdomen": "Gastric wall thickening"},
    "Dengue Hemorrhagic Fever": {"X-Ray Chest": "Bilateral pleural effusions", "Ultrasound Abdomen": "Ascites, hepatosplenomegaly"},
    "Hyperlipidemia": {"X-Ray Chest": "Normal", "Echocardiogram": "Normal LV function"},
}

ECG_FINDINGS = {
    "Heart Failure": "ST depression V4-V6, LBBB",
    "Coronary Artery Disease": "ST depression leads II, III, aVF. T-wave inversion V4-V6",
    "Hypertension": "LVH voltage criteria. Strain pattern",
    "Atrial Fibrillation": "Irregularly irregular rhythm, no P waves",
    "Default": "Normal sinus rhythm. Rate 75 bpm. No ST-T changes",
}

ALLERGIES_LIST = [
    "Penicillin", "Sulfonamides", "NSAIDs", "Aspirin", "Ibuprofen",
    "Contrast dye", "Latex", "NKDA (No Known Drug Allergy)",
    "Sulfa drugs", "Codeine", "Erythromycin", "Tetracycline"
]

PMH_LIST = [
    "Hypertension", "Diabetes Mellitus Type 2", "Asthma", "Hypothyroidism",
    "Dyslipidemia", "Ischemic Heart Disease", "Stroke", "Depression",
    "GERD", "Peptic Ulcer Disease", "Chronic Kidney Disease", "Tuberculosis (treated)"
]

PSH_LIST = [
    "Appendectomy", "Cholecystectomy", "Hernia repair", "Cesarean Section",
    "Tonsillectomy", "CABG", "Hip replacement", "Knee replacement",
    "Hysterectomy", "Thyroidectomy", "None"
]

FAMILY_HX_LIST = [
    "Father: Diabetes Mellitus", "Mother: Hypertension", "Sibling: Asthma",
    "Father: Ischemic Heart Disease", "Mother: Thyroid Disease",
    "Grandfather: Stroke", "No significant family history",
    "Mother: Breast Cancer", "Father: Colon Cancer", "Sibling: SLE"
]


def get_vitals(disease_name: str, visit_num: int) -> dict:
    """Generate realistic vitals based on disease."""
    base_bp_sys = 120
    base_bp_dia = 80
    base_pulse = 72
    base_temp = 98.6
    base_rr = 16
    base_spo2 = 98

    if disease_name == "Hypertension":
        base_bp_sys = random.randint(145, 180)
        base_bp_dia = random.randint(90, 110)
    elif disease_name in ["COVID-19", "Pneumonia", "Tuberculosis", "Dengue Fever", "Typhoid Fever"]:
        base_temp = round(random.uniform(101, 104), 1)
        base_pulse = random.randint(90, 120)
        base_rr = random.randint(20, 30)
        base_spo2 = random.randint(85, 95)
    elif disease_name == "Heart Failure":
        base_spo2 = random.randint(88, 94)
        base_rr = random.randint(22, 28)
    elif disease_name in ["COPD", "Asthma"]:
        base_spo2 = random.randint(88, 95)
        base_rr = random.randint(20, 28)
    elif disease_name in ["Acute Appendicitis", "Pancreatitis"]:
        base_temp = round(random.uniform(100, 103), 1)
        base_pulse = random.randint(85, 110)

    height = random.randint(150, 185)
    weight = random.randint(50, 120)
    bmi = round(weight / ((height / 100) ** 2), 1)

    return {
        "blood_pressure": {
            "systolic": base_bp_sys + random.randint(-5, 5),
            "diastolic": base_bp_dia + random.randint(-5, 5)
        },
        "pulse": base_pulse + random.randint(-5, 5),
        "temperature": round(base_temp + round(random.uniform(-0.5, 0.5), 1), 1),
        "respiratory_rate": base_rr + random.randint(-2, 2),
        "spo2": base_spo2 + random.randint(-2, 2),
        "height": height,
        "weight": weight,
        "bmi": bmi,
    }


def get_labs(disease: dict, visit_num: int) -> dict:
    """Generate realistic lab values for a disease."""
    labs = {}
    template = disease.get("labs_template", {})

    # Default CBC
    labs["CBC"] = {
        "HGB": round(random.uniform(*template.get("HGB", (11.0, 16.0))), 1),
        "RBC": round(random.uniform(3.5, 5.5), 2),
        "WBC": round(random.uniform(*template.get("WBC", (4.5, 10.0))), 1),
        "Platelets": random.randint(*template.get("Platelets", (150, 400))),
        "MCV": random.randint(*template.get("MCV", (80, 100))),
        "MCH": round(random.uniform(*template.get("MCH", (27, 33))), 1),
        "MCHC": random.randint(32, 36),
        "Neutrophils_pct": round(random.uniform(*template.get("Neutrophils", (55, 75))), 1),
        "Lymphocytes_pct": round(random.uniform(20, 40), 1),
    }

    # Inflammatory markers
    labs["Inflammatory"] = {
        "ESR": random.randint(*template.get("ESR", (5, 30))),
        "CRP": round(random.uniform(*template.get("CRP", (0.5, 5.0))), 1),
    }

    # LFT
    labs["LFT"] = {
        "AST": random.randint(*template.get("AST", (15, 40))),
        "ALT": random.randint(*template.get("ALT", (10, 40))),
        "ALP": random.randint(*template.get("ALP", (44, 147))),
        "Bilirubin_Total": round(random.uniform(*template.get("Bilirubin", (0.3, 1.2))), 1),
        "Albumin": round(random.uniform(*template.get("Albumin", (3.5, 5.0))), 1),
    }

    # KFT
    labs["KFT"] = {
        "Creatinine": round(random.uniform(*template.get("Creatinine", (0.6, 1.2))), 2),
        "Urea": random.randint(*template.get("Urea", (15, 40))),
        "eGFR": random.randint(*template.get("eGFR", (60, 120))),
    }

    # Electrolytes
    labs["Electrolytes"] = {
        "Na": random.randint(*template.get("Na", (135, 145))),
        "K": round(random.uniform(*template.get("K", (3.5, 5.0))), 1),
        "Cl": random.randint(98, 107),
    }

    # Glucose & HbA1c
    labs["Glucose"] = {
        "HbA1c": round(random.uniform(*template.get("HbA1c", (4.5, 6.4))), 1),
        "RBS": random.randint(*template.get("RBS", (80, 140))),
    }

    # Lipid profile
    labs["Lipid_Profile"] = {
        "Total_Cholesterol": random.randint(*template.get("Cholesterol", (150, 200))),
        "LDL": random.randint(*template.get("LDL", (80, 130))),
        "HDL": random.randint(*template.get("HDL", (40, 60))),
        "Triglycerides": random.randint(*template.get("TG", (80, 150))),
    }

    # Urine analysis
    labs["Urine_Analysis"] = {
        "Color": "Yellow",
        "Clarity": random.choice(["Clear", "Cloudy"]),
        "Protein": random.choice(["Negative", "Trace", "+1", "+2"]),
        "Glucose": "Negative" if disease["name"] not in ["Diabetes Mellitus Type 2"] else random.choice(["+1", "+2", "+3"]),
        "Nitrites": "Positive" if disease["name"] == "Urinary Tract Infection" else "Negative",
        "RBC": random.choice(["0-2", "2-5", "5-10"]),
        "WBC": random.choice(["0-2", "2-5"]),
    }

    return labs


def get_imaging(disease_name: str) -> dict:
    """Generate imaging findings for a disease."""
    findings = IMAGING_FINDINGS.get(disease_name, {})
    if not findings:
        findings = {"X-Ray Chest": "No acute cardiopulmonary abnormality detected"}

    imaging = {}
    for modality, finding in findings.items():
        imaging[modality] = {"finding": finding, "impression": finding}

    # Add ECG
    imaging["ECG"] = {"finding": ECG_FINDINGS.get(disease_name, ECG_FINDINGS["Default"])}

    return imaging


def generate_clinical_notes(disease: dict, visit_num: int, patient_name: str, age: int) -> str:
    """Generate a 100-300 word clinical note."""
    visits_text = ["first", "second", "third", "fourth", "fifth", "sixth"]
    visit_label = visits_text[min(visit_num, len(visits_text) - 1)]

    notes = (
        f"Patient {patient_name}, {age}-year-old, presenting for {visit_label} visit. "
        f"Chief complaint: {disease['symptoms'][0]}. "
        f"Patient reports {', '.join(random.sample(disease['symptoms'], min(3, len(disease['symptoms']))))}. "
        f"Symptoms have been present for {random.randint(1, 14)} days. "
        f"On examination, patient is {random.choice(['alert and oriented', 'mildly distressed', 'comfortable at rest'])}. "
        f"Vitals as documented. Systemic examination performed. "
        f"Cardiovascular: {random.choice(['S1 S2 heard, no murmurs', 'S1 S2 with grade 2/6 systolic murmur'])}. "
        f"Respiratory: {random.choice(['Clear bilaterally', 'Reduced air entry on right base', 'Bilateral crackles'])}. "
        f"Abdomen: {random.choice(['Soft, non-tender', 'Mild epigastric tenderness', 'Guarding present'])}. "
        f"Assessment: {disease['assessment_base']} "
        f"Treatment plan reviewed and adjusted for visit {visit_num + 1}. "
        f"Laboratory investigations ordered. Patient counselled on medications and lifestyle. "
        f"Follow-up advised in {random.choice(['2 weeks', '4 weeks', '6 weeks', '3 months'])}."
    )
    return notes


def generate_patient_data() -> list[dict]:
    """Generate 100 synthetic patients with 3-6 visits each."""
    patients = []
    disease_pool = DISEASES * 3  # Ensure enough variety
    random.shuffle(disease_pool)

    used_names = set()

    for i in range(100):
        # Pick disease
        disease = disease_pool[i % len(disease_pool)]

        # Generate unique name
        while True:
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break

        age = random.randint(18, 80)
        _ = random.choice(GENDERS)  # Consume random value to preserve seed sequence
        first_name = name.split()[0]
        gender = GENDER_MAP.get(first_name, "Male")
        patient_id = f"PAT{str(i + 1).zfill(3)}"

        # Allergies (1-2 allergies or NKDA)
        num_allergies = random.randint(0, 2)
        allergies = random.sample(ALLERGIES_LIST[:-1], num_allergies) if num_allergies else ["NKDA (No Known Drug Allergy)"]

        # Medical history (1-3 conditions, not same as primary disease)
        pmh_options = [p for p in PMH_LIST if p.lower() not in disease["name"].lower()]
        past_medical = random.sample(pmh_options, random.randint(1, 3))

        # Surgical history
        past_surgical = random.sample(PSH_LIST, random.randint(1, 2))

        # Family history
        family_hx = random.sample(FAMILY_HX_LIST, random.randint(1, 3))

        # Lifestyle
        lifestyle = {
            "smoking": random.choice(["Non-smoker", "Ex-smoker (20 pack-years)", "Current smoker (10 cigarettes/day)"]),
            "alcohol": random.choice(["Non-drinker", "Occasional", "Regular (2-3 units/week)"]),
            "exercise": random.choice(["Sedentary", "Light (30 min walking daily)", "Moderate (3x/week)", "Active (daily gym)"])
        }

        # Generate 3-6 visits
        num_visits = random.randint(3, 6)
        visits = []

        # Generate visit dates spread over 12-18 months
        start_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 180))

        for j in range(num_visits):
            visit_date = start_date + timedelta(days=j * random.randint(30, 90))
            visit_id = f"VIS{patient_id[3:]}{str(j + 1).zfill(2)}"

            medications_count = random.randint(1, len(disease["medications"]))
            medications = disease["medications"][:medications_count]

            visit = {
                "visit_id": visit_id,
                "patient_id": patient_id,
                "date": visit_date.strftime("%Y-%m-%d"),
                "chief_complaint": disease["symptoms"][0],
                "hpi": (
                    f"Patient presents with {disease['symptoms'][0]} for {random.randint(1, 21)} days. "
                    f"Associated symptoms include {', '.join(random.sample(disease['symptoms'][1:], min(2, len(disease['symptoms']) - 1)))}. "
                    f"No improvement with previous medications."
                ),
                "clinical_notes": generate_clinical_notes(disease, j, name, age),
                "symptoms": random.sample(disease["symptoms"], min(random.randint(2, 4), len(disease["symptoms"]))),
                "vitals": get_vitals(disease["name"], j),
                "labs": get_labs(disease, j),
                "imaging": get_imaging(disease["name"]),
                "medications": medications,
                "doctor_assessment": disease["assessment_base"],
                "treatment_plan": f"Continue current medications. {random.choice(['Increase dose', 'Add new medication', 'Monitor closely', 'Refer to specialist'])}. Lifestyle counselling.",
                "follow_up_advice": f"Return in {random.choice(['2 weeks', '4 weeks', '6 weeks', '3 months'])} or sooner if symptoms worsen.",
                "icd10_code": disease["icd10"],
                "icd10_description": disease["name"],
                "snomed_concept": disease["snomed"],
                "doctor_approval": random.random() > 0.3,
            }
            visits.append(visit)

        patient = {
            "patient_id": patient_id,
            "name": name,
            "age": age,
            "gender": gender,
            "blood_group": random.choice(BLOOD_GROUPS),
            "allergies": allergies,
            "past_medical_history": past_medical,
            "past_surgical_history": past_surgical,
            "family_history": family_hx,
            "lifestyle": lifestyle,
            "primary_disease": disease["name"],
            "visits": visits,
        }
        patients.append(patient)

    return patients


def main():
    """Generate and save dataset."""
    print("Generating synthetic patient dataset...")
    patients = generate_patient_data()

    output_path = Path(__file__).parent / "patient_data.json"
    with open(output_path, "w") as f:
        json.dump(patients, f, indent=2)

    total_visits = sum(len(p["visits"]) for p in patients)
    diseases = set(p["primary_disease"] for p in patients)

    print(f"✅ Generated {len(patients)} patients")
    print(f"✅ Generated {total_visits} total visits")
    print(f"✅ Disease variety: {len(diseases)} unique diseases")
    print(f"✅ Saved to: {output_path}")


if __name__ == "__main__":
    main()
