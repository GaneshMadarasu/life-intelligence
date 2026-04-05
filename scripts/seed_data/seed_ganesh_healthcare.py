#!/usr/bin/env python3
"""
Healthcare seed data for Ganesh Madarasu (DOB 1998-09-15), 27-year-old Male.
Covers 2003–2026 across all 4 healthcare verticals.
Run: python scripts/seed_data/seed_ganesh_healthcare.py
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()


def main():
    try:
        from rich.console import Console
        from rich.progress import track
        console = Console()
    except ImportError:
        import types
        console = types.SimpleNamespace(print=print, rule=print)
        track = lambda x, description="": x

    console.print("[bold cyan]Life Intelligence — Ganesh Healthcare Seed Data[/bold cyan]")
    console.print("[dim]Seeding healthcare data for Ganesh Madarasu (DOB 1998-09-15, Male)...[/dim]\n")

    from src.core.neo4j_client import get_client
    from src.core.vector_store import get_vector_store
    from src.core.person import get_person_manager

    try:
        neo4j = get_client()
        vector = get_vector_store()
    except Exception as e:
        console.print(f"[red]Could not connect to services: {e}[/red]")
        console.print("[yellow]Run: docker-compose up -d[/yellow]")
        sys.exit(1)

    # Ensure Person node
    pm = get_person_manager(neo4j)
    pm.ensure_person(
        name="Ganesh Madarasu",
        dob="1998-09-15",
        sex="Male",
        blood_type="B+",
    )
    console.print("[green]✓ Person: Ganesh Madarasu (DOB 1998-09-15, Male, B+)[/green]")

    # Register domain
    from src.domains.healthcare.domain import HealthcareDomain
    hc = HealthcareDomain(neo4j, vector)
    hc.register()

    # ── MEDICAL VERTICAL ──────────────────────────────────────────────────────

    console.rule("[bold]Medical Vertical[/bold]")

    from src.domains.healthcare.verticals.medical.graph_builder import MedicalGraphBuilder
    med_builder = MedicalGraphBuilder(neo4j)

    # 1. Childhood records — allergies, vaccines, early conditions
    med_builder.build(
        {
            "conditions": [],
            "medications": [],
            "symptoms": [],
            "lab_results": [],
            "vitals": [],
            "allergies": [
                {"allergen": "Dust mites", "reaction": "Rhinitis and sneezing",
                 "severity": "moderate", "discovered_date": "2006-04-10"},
                {"allergen": "Shellfish", "reaction": "Hives and stomach cramps",
                 "severity": "moderate", "discovered_date": "2008-09-22"},
                {"allergen": "Sulfa antibiotics", "reaction": "Skin rash",
                 "severity": "mild", "discovered_date": "2011-03-14"},
            ],
            "procedures": [],
            "vaccines": [
                {"name": "BCG", "date": "1998-09-16", "lot_number": "BCG1998A", "provider": "Apollo Hospital, Chennai"},
                {"name": "Hepatitis B (birth)", "date": "1998-09-16", "lot_number": "HB1998B", "provider": "Apollo Hospital, Chennai"},
                {"name": "DTP + Hib + IPV (6-week)", "date": "1998-10-27", "lot_number": "DTP1998C", "provider": "Apollo Hospital, Chennai"},
                {"name": "OPV", "date": "1999-04-15", "lot_number": "OPV1999A", "provider": "National Pulse Polio Programme"},
                {"name": "MMR", "date": "1999-10-15", "lot_number": "MMR1999A", "provider": "Apollo Hospital, Chennai"},
                {"name": "Typhoid", "date": "2001-07-10", "lot_number": "TYP2001A", "provider": "Apollo Hospital, Chennai"},
                {"name": "Varicella", "date": "2003-09-20", "lot_number": "VAR2003A", "provider": "Apollo Hospital, Chennai"},
                {"name": "Hepatitis A (dose 1)", "date": "2004-01-15", "lot_number": "HA2004A", "provider": "Apollo Hospital, Chennai"},
                {"name": "Hepatitis A (dose 2)", "date": "2004-07-15", "lot_number": "HA2004B", "provider": "Apollo Hospital, Chennai"},
                {"name": "MMR booster", "date": "2006-03-10", "lot_number": "MMR2006A", "provider": "School Health Programme"},
                {"name": "HPV (Gardasil, dose 1)", "date": "2013-06-10", "lot_number": "HPV2013A", "provider": "Apollo Clinic"},
                {"name": "HPV (Gardasil, dose 2)", "date": "2013-09-10", "lot_number": "HPV2013B", "provider": "Apollo Clinic"},
                {"name": "HPV (Gardasil, dose 3)", "date": "2014-01-10", "lot_number": "HPV2014A", "provider": "Apollo Clinic"},
                {"name": "Tdap", "date": "2015-08-01", "lot_number": "TDAP2015A", "provider": "Apollo Clinic"},
                {"name": "Meningococcal ACWY", "date": "2016-07-20", "lot_number": "MEN2016A", "provider": "University Health Services"},
                {"name": "Influenza", "date": "2019-10-15", "lot_number": "FL2019A", "provider": "CVS Pharmacy"},
                {"name": "Influenza", "date": "2020-10-10", "lot_number": "FL2020A", "provider": "CVS Pharmacy"},
                {"name": "COVID-19 mRNA (Pfizer, dose 1)", "date": "2021-04-05", "lot_number": "EW0199", "provider": "State Vaccination Centre"},
                {"name": "COVID-19 mRNA (Pfizer, dose 2)", "date": "2021-04-26", "lot_number": "EW0312", "provider": "State Vaccination Centre"},
                {"name": "COVID-19 mRNA Booster", "date": "2021-12-18", "lot_number": "FK4021", "provider": "CVS Pharmacy"},
                {"name": "COVID-19 Bivalent Booster", "date": "2022-10-20", "lot_number": "BV2022X", "provider": "CVS Pharmacy"},
                {"name": "Influenza", "date": "2023-10-05", "lot_number": "FL2023A", "provider": "Walgreens"},
                {"name": "Influenza", "date": "2024-10-08", "lot_number": "FL2024A", "provider": "Walgreens"},
                {"name": "Influenza", "date": "2025-10-06", "lot_number": "FL2025A", "provider": "CVS Pharmacy"},
            ],
            "hospitalizations": [],
            "providers": [
                {"name": "Dr. Rajesh Patel", "specialty": "Pediatrics",
                 "institution": "Apollo Hospital, Chennai", "contact": "+91-44-2829-0200"},
            ],
        },
        "seed://childhood_records",
        {"date": "2011-03-14", "title": "Childhood Medical Records 1998-2011", "doc_type": "medical_history"},
    )
    console.print("[green]✓ Childhood records (allergies: dust mites, shellfish, sulfa; 20 vaccines)[/green]")

    # 2. Conditions diagnosed — adolescence to present
    med_builder.build(
        {
            "conditions": [
                {"name": "Allergic Rhinitis (Seasonal)", "icd_code": "J30.1", "status": "chronic",
                 "diagnosed_date": "2008-03-10", "severity": "mild"},
                {"name": "ADHD — Combined Presentation", "icd_code": "F90.2", "status": "managed",
                 "diagnosed_date": "2012-08-20", "severity": "moderate"},
                {"name": "Vitamin D Deficiency", "icd_code": "E55.9", "status": "resolved",
                 "diagnosed_date": "2019-01-15", "severity": "mild"},
                {"name": "Mild Anxiety Disorder", "icd_code": "F41.1", "status": "managed",
                 "diagnosed_date": "2021-06-10", "severity": "mild"},
                {"name": "Exercise-Induced Knee Pain (Patellofemoral Syndrome)", "icd_code": "M25.361",
                 "status": "resolved", "diagnosed_date": "2023-02-15", "severity": "mild"},
                {"name": "Elevated LDL (Borderline)", "icd_code": "E78.00", "status": "monitored",
                 "diagnosed_date": "2025-01-20", "severity": "mild"},
            ],
            "medications": [
                {"name": "Cetirizine", "dosage": "10mg", "frequency": "once daily (seasonal)",
                 "prescribed_date": "2008-03-10", "prescriber": "Dr. Rajesh Patel",
                 "indication": "Allergic Rhinitis"},
                {"name": "Fluticasone nasal spray", "dosage": "50mcg/spray, 2 sprays each nostril",
                 "frequency": "once daily (seasonal)", "prescribed_date": "2014-04-01",
                 "prescriber": "Dr. Anika Sharma", "indication": "Allergic Rhinitis"},
                {"name": "Methylphenidate ER", "dosage": "18mg", "frequency": "once daily (school days)",
                 "prescribed_date": "2012-08-20", "prescriber": "Dr. Anika Sharma",
                 "indication": "ADHD"},
                {"name": "Amphetamine salts (Adderall XR)", "dosage": "20mg",
                 "frequency": "once daily", "prescribed_date": "2019-09-01",
                 "prescriber": "Dr. Priya Nair", "indication": "ADHD — transitioned from Methylphenidate"},
                {"name": "Vitamin D3", "dosage": "2000IU", "frequency": "once daily",
                 "prescribed_date": "2019-01-15", "prescriber": "Dr. Priya Nair",
                 "indication": "Vitamin D Deficiency"},
                {"name": "Sertraline", "dosage": "25mg", "frequency": "once daily",
                 "prescribed_date": "2021-06-10", "prescriber": "Dr. Priya Nair",
                 "indication": "Mild Anxiety Disorder"},
            ],
            "symptoms": [
                {"name": "Nasal congestion", "severity": "mild",
                 "onset_date": "2008-03-01", "resolved_date": ""},
                {"name": "Knee pain (anterior)", "severity": "moderate",
                 "onset_date": "2023-01-10", "resolved_date": "2023-06-01"},
            ],
            "lab_results": [],
            "vitals": [],
            "allergies": [],
            "procedures": [
                {"name": "Allergy skin prick test", "date": "2014-04-01",
                 "provider": "Dr. Anika Sharma", "location": "Chennai Allergy Clinic",
                 "notes": "Positive for dust mites, grass pollen, mold. Negative for tree nuts."},
                {"name": "Sports physical — varsity cricket", "date": "2015-06-10",
                 "provider": "Dr. Anika Sharma", "location": "Apollo Clinic",
                 "notes": "Cleared for competitive sports. BMI 22.1, BP 118/74."},
                {"name": "Pre-college health screening", "date": "2016-07-15",
                 "provider": "University Health Services", "location": "University Health Services",
                 "notes": "Comprehensive physical. Blood work normal. ADHD medications documented."},
                {"name": "Neuropsychological evaluation — ADHD re-assessment", "date": "2019-07-10",
                 "provider": "Dr. Priya Nair", "location": "Northeastern Psychiatry",
                 "notes": "ADHD-combined confirmed in adult. Transitioned to Adderall XR 20mg."},
                {"name": "Knee MRI (right)", "date": "2023-02-20",
                 "provider": "Dr. Kevin O'Brien", "location": "Sports Medicine & Orthopedics",
                 "notes": "No structural damage. Patellofemoral syndrome. PT recommended."},
                {"name": "Physical therapy — knee (12 sessions)", "date": "2023-03-01",
                 "provider": "Dr. Maria Gonzalez PT", "location": "Back Bay Sports PT",
                 "notes": "VMO strengthening protocol. Full resolution by June 2023. Cleared to run."},
                {"name": "Annual physical", "date": "2025-01-20",
                 "provider": "Dr. Priya Nair", "location": "Boston Medical Associates",
                 "notes": "Overall healthy. LDL borderline at 118 mg/dL. Lifestyle modification advised. Adderall XR continued. Sertraline dose stable."},
            ],
            "vaccines": [],
            "hospitalizations": [],
            "providers": [
                {"name": "Dr. Anika Sharma", "specialty": "Allergy & Immunology",
                 "institution": "Chennai Allergy Clinic", "contact": "+91-44-2829-3300"},
                {"name": "Dr. Priya Nair", "specialty": "Internal Medicine & Psychiatry",
                 "institution": "Boston Medical Associates", "contact": "617-555-0210"},
                {"name": "Dr. Kevin O'Brien", "specialty": "Orthopedics / Sports Medicine",
                 "institution": "Sports Medicine & Orthopedics, Boston", "contact": "617-555-0410"},
                {"name": "Dr. Maria Gonzalez", "specialty": "Physical Therapy",
                 "institution": "Back Bay Sports PT", "contact": "617-555-0510"},
            ],
        },
        "seed://conditions_medications",
        {"date": "2025-01-20", "title": "Medical History 2008-2025", "doc_type": "medical_history"},
    )
    console.print("[green]✓ Conditions (Allergic Rhinitis, ADHD, Vitamin D deficiency, Anxiety, Knee injury)[/green]")
    console.print("[green]✓ Medications (Cetirizine, Fluticasone, Adderall XR, Sertraline, Vit D3)[/green]")
    console.print("[green]✓ Procedures (allergy testing, knee MRI + PT, neuro eval)[/green]")

    # 3. Lab results — CBC, metabolic panel, lipids (annual from 2019)
    # HbA1c — tracking pre-diabetes risk (South Asian elevated baseline risk)
    hba1c_data = [
        ("2019-01-15", "5.3", "normal"),
        ("2020-08-10", "5.4", "normal"),
        ("2021-06-10", "5.4", "normal"),
        ("2022-07-15", "5.5", "normal — monitoring due to family history"),
        ("2023-07-20", "5.5", "normal, stable"),
        ("2024-07-18", "5.6", "upper normal — lifestyle note"),
        ("2025-01-20", "5.6", "stable, continue monitoring annually"),
    ]
    for (lab_date, value, notes) in track(hba1c_data, description="HbA1c labs"):
        neo4j.run_query(
            """
            MERGE (l:LabResult {id: $id})
            SET l.test_name = 'HbA1c',
                l.value = $value,
                l.unit = '%',
                l.reference_range = '<5.7 normal, 5.7-6.4 pre-diabetes, >=6.5 diabetes',
                l.date = $date,
                l.is_abnormal = $abnormal,
                l.notes = $notes
            WITH l
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_LAB_RESULT]->(l)
            """,
            {
                "id": f"lab_hba1c_{lab_date}",
                "value": value,
                "date": lab_date,
                "abnormal": float(value) >= 5.7,
                "notes": notes,
            },
        )

    # Lipid panel — trending upward slightly (sedentary work + diet)
    lipid_data = [
        ("2019-01-15", "Total Cholesterol", "165", "mg/dL", "<200", False),
        ("2019-01-15", "LDL", "90", "mg/dL", "<100", False),
        ("2019-01-15", "HDL", "55", "mg/dL", ">40", False),
        ("2019-01-15", "Triglycerides", "95", "mg/dL", "<150", False),
        ("2021-06-10", "Total Cholesterol", "178", "mg/dL", "<200", False),
        ("2021-06-10", "LDL", "102", "mg/dL", "<100", True),
        ("2021-06-10", "HDL", "52", "mg/dL", ">40", False),
        ("2021-06-10", "Triglycerides", "108", "mg/dL", "<150", False),
        ("2023-07-20", "Total Cholesterol", "185", "mg/dL", "<200", False),
        ("2023-07-20", "LDL", "110", "mg/dL", "<100", True),
        ("2023-07-20", "HDL", "58", "mg/dL", ">40", False),
        ("2023-07-20", "Triglycerides", "88", "mg/dL", "<150", False),
        ("2025-01-20", "Total Cholesterol", "192", "mg/dL", "<200", False),
        ("2025-01-20", "LDL", "118", "mg/dL", "<100", True),
        ("2025-01-20", "HDL", "56", "mg/dL", ">40", False),
        ("2025-01-20", "Triglycerides", "90", "mg/dL", "<150", False),
    ]
    for (date_, test, value, unit, ref, abnormal) in lipid_data:
        neo4j.run_query(
            """
            MERGE (l:LabResult {id: $id})
            SET l.test_name = $test, l.value = $value, l.unit = $unit,
                l.reference_range = $ref, l.date = $date, l.is_abnormal = $abnormal
            WITH l
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_LAB_RESULT]->(l)
            """,
            {"id": f"lab_{test.lower().replace(' ','_')}_{date_}", "test": test,
             "value": value, "unit": unit, "ref": ref, "date": date_, "abnormal": abnormal},
        )

    # Vitamin D levels
    vit_d_data = [
        ("2019-01-15", "Vitamin D (25-OH)", "16", "ng/mL", "30-100", True, "deficient"),
        ("2019-07-15", "Vitamin D (25-OH)", "28", "ng/mL", "30-100", True, "improving with supplementation"),
        ("2020-01-20", "Vitamin D (25-OH)", "38", "ng/mL", "30-100", False, "normal — continue 2000 IU maintenance"),
        ("2021-06-10", "Vitamin D (25-OH)", "42", "ng/mL", "30-100", False, "good level"),
        ("2023-07-20", "Vitamin D (25-OH)", "44", "ng/mL", "30-100", False, "sustained"),
        ("2025-01-20", "Vitamin D (25-OH)", "41", "ng/mL", "30-100", False, "stable on 2000 IU daily"),
    ]
    for (date_, test, value, unit, ref, abnormal, notes) in vit_d_data:
        neo4j.run_query(
            """
            MERGE (l:LabResult {id: $id})
            SET l.test_name = $test, l.value = $value, l.unit = $unit,
                l.reference_range = $ref, l.date = $date, l.is_abnormal = $abnormal, l.notes = $notes
            WITH l
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_LAB_RESULT]->(l)
            """,
            {"id": f"lab_vitd_{date_}", "test": test, "value": value, "unit": unit,
             "ref": ref, "date": date_, "abnormal": abnormal, "notes": notes},
        )
    console.print("[green]✓ HbA1c trend (2019-2025, all normal range, monitoring)[/green]")
    console.print("[green]✓ Lipid panels (LDL trending upward: 90→118 mg/dL)[/green]")
    console.print("[green]✓ Vitamin D: deficient 2019 → normalized by 2020[/green]")

    # Blood pressure vitals
    bp_data = [
        ("2015-06-10", "118/74"),
        ("2016-07-15", "116/72"),
        ("2019-01-15", "120/76"),
        ("2020-08-10", "122/78"),
        ("2021-06-10", "124/80"),
        ("2022-07-15", "126/80"),
        ("2023-07-20", "122/78"),
        ("2024-07-18", "124/80"),
        ("2025-01-20", "128/82"),
    ]
    for (date_, bp) in bp_data:
        neo4j.run_query(
            """
            MERGE (v:Vital {id: $id})
            SET v.type = 'blood_pressure', v.value = $value,
                v.unit = 'mmHg', v.date = $date
            WITH v
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_VITAL]->(v)
            """,
            {"id": f"vital_bp_{date_}", "value": bp, "date": date_},
        )
    console.print("[green]✓ Blood pressure vitals 2015-2025 (consistently normal, slight upward trend)[/green]")

    # ── FITNESS VERTICAL ──────────────────────────────────────────────────────

    console.rule("[bold]Fitness Vertical[/bold]")

    from src.domains.healthcare.verticals.fitness.graph_builder import FitnessGraphBuilder
    fit_builder = FitnessGraphBuilder(neo4j)

    # Body weight progression (quarterly 2014-2026)
    weight_data = [
        ("2014-09-15", "132", "lbs"),   # 16yo — lean, cricket
        ("2015-09-15", "138", "lbs"),   # 17yo — growing
        ("2016-07-15", "145", "lbs"),   # 18yo — pre-college
        ("2017-06-01", "155", "lbs"),   # Freshman 15
        ("2018-01-01", "158", "lbs"),   # Sophomore
        ("2019-01-01", "162", "lbs"),   # Junior, inconsistent gym
        ("2019-09-01", "165", "lbs"),   # Started consistent gym
        ("2020-06-01", "168", "lbs"),   # Pandemic bulk
        ("2021-01-01", "170", "lbs"),   # Post-grad
        ("2021-09-01", "168", "lbs"),   # First job, structured routine
        ("2022-06-01", "172", "lbs"),   # Lean bulk
        ("2023-01-01", "175", "lbs"),   # Peak bulk
        ("2023-06-01", "170", "lbs"),   # Cut cycle (knee injury resolved)
        ("2024-01-01", "168", "lbs"),   # Maintenance
        ("2024-09-15", "167", "lbs"),   # Stable
        ("2025-09-15", "169", "lbs"),   # Slight increase
        ("2026-01-01", "170", "lbs"),   # Current
    ]
    for (date_, weight, unit) in weight_data:
        neo4j.run_query(
            """
            MERGE (bm:BodyMetric {id: $id})
            SET bm.type = 'weight', bm.value = $value, bm.unit = $unit, bm.date = $date
            WITH bm
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_BODY_METRIC]->(bm)
            """,
            {"id": f"bm_weight_{date_}", "value": weight, "unit": unit, "date": date_},
        )

    # Body fat % (DEXA / calipers)
    body_fat_data = [
        ("2019-09-01", "16.2", "%"),
        ("2020-09-01", "17.5", "%"),  # Pandemic sedentary
        ("2021-09-01", "15.8", "%"),  # Back to gym
        ("2022-09-01", "14.2", "%"),  # Lean bulk
        ("2023-09-01", "13.5", "%"),  # Cut phase
        ("2024-09-15", "14.0", "%"),  # Maintenance
        ("2025-09-15", "14.8", "%"),
    ]
    for (date_, value, unit) in body_fat_data:
        neo4j.run_query(
            """
            MERGE (bm:BodyMetric {id: $id})
            SET bm.type = 'body_fat_percentage', bm.value = $value, bm.unit = $unit, bm.date = $date
            WITH bm
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_BODY_METRIC]->(bm)
            """,
            {"id": f"bm_bodyfat_{date_}", "value": value, "unit": unit, "date": date_},
        )
    console.print("[green]✓ Body metrics 2014-2026 (132→170 lbs; body fat 16%→14%)[/green]")

    # Supplements
    supplements = [
        ("Whey Protein Isolate", "30g per serving", "post-workout", "Optimum Nutrition",
         "Muscle protein synthesis, started 2019", "2019-09-01"),
        ("Creatine Monohydrate", "5g", "once daily", "Optimum Nutrition",
         "Strength and power, started 2020", "2020-01-15"),
        ("Vitamin D3", "2000IU", "once daily", "NOW Foods",
         "Deficiency treatment, started 2019", "2019-01-15"),
        ("Omega-3 Fish Oil", "2000mg", "once daily", "Nordic Naturals",
         "Cardiovascular health, anti-inflammatory, started 2021", "2021-06-10"),
        ("Magnesium Glycinate", "300mg", "once daily at night", "Doctor's Best",
         "Sleep quality and muscle recovery, started 2022", "2022-04-01"),
        ("L-Theanine", "200mg", "as needed", "Jarrow",
         "Anxiety management with Adderall, started 2022", "2022-01-10"),
        ("Ashwagandha (KSM-66)", "300mg", "once daily", "Ixoreal",
         "Stress and cortisol regulation, started 2023", "2023-03-15"),
    ]
    for (name, dosage, freq, brand, purpose, date_) in supplements:
        neo4j.run_query(
            """
            MERGE (s:Supplement {name: $name})
            SET s.dosage = $dosage, s.frequency = $freq,
                s.brand = $brand, s.purpose = $purpose, s.start_date = $date
            WITH s
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:TAKES_SUPPLEMENT]->(s)
            """,
            {"name": name, "dosage": dosage, "freq": freq,
             "brand": brand, "purpose": purpose, "date": date_},
        )
    console.print("[green]✓ Supplements: Protein, Creatine, Vit D3, Omega-3, Mg, L-Theanine (⚠ +Adderall), Ashwagandha[/green]")

    # Workout history
    workouts = [
        # High school — cricket + gym beginnings
        ("2015-03-10", "cricket", 120, 380, "high"),
        ("2015-07-20", "cricket", 120, 360, "high"),
        ("2016-04-15", "cricket", 120, 400, "high"),
        # College — gym
        ("2017-03-10", "strength_training", 60, 310, "moderate"),
        ("2017-09-15", "strength_training", 65, 330, "moderate"),
        ("2018-03-20", "strength_training", 60, 320, "moderate"),
        ("2018-09-10", "running", 30, 280, "moderate"),
        ("2019-01-15", "strength_training", 60, 340, "moderate"),
        ("2019-06-01", "strength_training", 70, 360, "high"),
        ("2019-09-10", "running", 40, 340, "moderate"),
        # Pandemic — home workouts
        ("2020-04-10", "calisthenics", 45, 250, "moderate"),
        ("2020-07-15", "running", 50, 380, "moderate"),
        ("2020-11-20", "strength_training", 60, 310, "moderate"),
        # Post-grad — structured training
        ("2021-02-10", "strength_training", 75, 390, "high"),
        ("2021-06-15", "running", 45, 380, "high"),
        ("2021-10-20", "strength_training", 75, 400, "high"),
        ("2022-02-15", "strength_training", 80, 420, "high"),
        ("2022-06-10", "cycling", 60, 440, "high"),
        ("2022-10-15", "strength_training", 80, 410, "high"),
        # Knee injury period — low impact
        ("2023-01-10", "swimming", 45, 320, "moderate"),
        ("2023-04-15", "cycling", 60, 430, "moderate"),  # PT cleared
        ("2023-07-20", "strength_training", 75, 400, "high"),  # Back to lifting
        ("2023-10-10", "running", 50, 420, "high"),  # Running resumed
        ("2024-02-15", "strength_training", 80, 430, "high"),
        ("2024-06-10", "running", 55, 450, "high"),
        ("2024-10-20", "strength_training", 85, 440, "high"),
        ("2025-01-15", "strength_training", 80, 420, "high"),
        ("2025-05-10", "running", 50, 430, "high"),
        ("2025-10-15", "strength_training", 85, 450, "high"),
        ("2026-01-20", "strength_training", 80, 420, "high"),
        ("2026-03-10", "running", 50, 440, "high"),
    ]
    for (date_, wtype, duration, calories, intensity) in workouts:
        neo4j.run_query(
            """
            MERGE (w:Workout {id: $id})
            SET w.type = $type, w.date = $date, w.duration_mins = $duration,
                w.calories_burned = $calories, w.intensity = $intensity
            WITH w
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_WORKOUT]->(w)
            """,
            {"id": f"workout_{date_}", "type": wtype, "date": date_,
             "duration": duration, "calories": calories, "intensity": intensity},
        )
    console.print("[green]✓ Workout history 2015-2026 (cricket → gym → structured training)[/green]")

    # Sleep records
    sleep_data = [
        # High school — decent sleep
        ("2015-06-01", 7.5, 7, 1.8),
        ("2016-06-01", 7.2, 7, 1.7),
        # College — irregular schedule
        ("2017-03-01", 6.5, 5, 1.3),
        ("2017-09-01", 6.2, 5, 1.2),
        ("2018-03-01", 6.0, 4, 1.1),
        ("2018-09-01", 5.8, 4, 1.0),
        ("2019-03-01", 6.5, 5, 1.3),
        ("2019-09-01", 7.0, 6, 1.6),  # Senior year, settling down
        # Pandemic
        ("2020-04-01", 8.5, 7, 1.8),  # Extra sleep during lockdown
        ("2020-10-01", 7.5, 6, 1.5),
        # First job — stressful start
        ("2021-03-01", 6.5, 5, 1.2),
        ("2021-09-01", 6.8, 6, 1.4),
        # Routine improving
        ("2022-03-01", 7.0, 7, 1.6),
        ("2022-09-01", 7.2, 7, 1.7),
        ("2023-03-01", 7.1, 7, 1.6),
        ("2023-09-01", 7.3, 8, 1.8),
        ("2024-03-01", 7.2, 7, 1.7),
        ("2024-09-01", 7.5, 8, 1.9),
        ("2025-03-01", 7.3, 8, 1.8),
        ("2025-09-01", 7.4, 8, 1.9),
        ("2026-01-01", 7.2, 7, 1.7),
    ]
    for (date_, duration, quality, deep) in sleep_data:
        neo4j.run_query(
            """
            MERGE (sr:SleepRecord {id: $id})
            SET sr.date = $date, sr.duration_hours = $duration,
                sr.quality = $quality, sr.deep_sleep_hours = $deep
            WITH sr
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_SLEEP_RECORD]->(sr)
            """,
            {"id": f"sleep_{date_}", "date": date_, "duration": duration,
             "quality": quality, "deep": deep},
        )
    console.print("[green]✓ Sleep records 2015-2026 (7.5→5.8 college dip→7.4 recovery)[/green]")

    # ── MENTAL HEALTH VERTICAL ────────────────────────────────────────────────

    console.rule("[bold]Mental Health Vertical[/bold]")

    from src.domains.healthcare.verticals.mental_health.graph_builder import MentalHealthGraphBuilder
    mh_builder = MentalHealthGraphBuilder(neo4j)

    mh_builder.build(
        {
            "therapy_sessions": [
                # College counseling — academic pressure + ADHD
                {"date": "2018-10-08", "therapist": "Dr. Monica Hayes",
                 "type": "Supportive", "notes_summary": "Initial visit: academic stress, ADHD management, imposter syndrome",
                 "mood_at_session": 5},
                {"date": "2019-02-14", "therapist": "Dr. Monica Hayes",
                 "type": "CBT", "notes_summary": "ADHD coping strategies, procrastination patterns",
                 "mood_at_session": 5},
                {"date": "2019-05-10", "therapist": "Dr. Monica Hayes",
                 "type": "CBT", "notes_summary": "Finishing strong academically, reduced anxiety",
                 "mood_at_session": 6},
                # Pandemic anxiety
                {"date": "2020-04-20", "therapist": "Dr. Daniel Cho",
                 "type": "CBT (telehealth)", "notes_summary": "Pandemic adjustment, isolation, WFH transition anxiety",
                 "mood_at_session": 4},
                {"date": "2020-07-15", "therapist": "Dr. Daniel Cho",
                 "type": "CBT (telehealth)", "notes_summary": "Routine building, behavioral activation",
                 "mood_at_session": 5},
                # First job burnout
                {"date": "2021-06-10", "therapist": "Dr. Daniel Cho",
                 "type": "CBT", "notes_summary": "Work anxiety, tech industry pressure, started Sertraline 25mg",
                 "mood_at_session": 4},
                {"date": "2021-09-15", "therapist": "Dr. Daniel Cho",
                 "type": "CBT", "notes_summary": "Sertraline response positive. Boundary-setting at work.",
                 "mood_at_session": 5},
                {"date": "2021-12-08", "therapist": "Dr. Daniel Cho",
                 "type": "CBT", "notes_summary": "Good progress. Year-end review anxiety managed.",
                 "mood_at_session": 6},
                {"date": "2022-04-20", "therapist": "Dr. Daniel Cho",
                 "type": "CBT", "notes_summary": "Maintaining gains. Reduced session frequency.",
                 "mood_at_session": 7},
                {"date": "2022-10-05", "therapist": "Dr. Daniel Cho",
                 "type": "CBT", "notes_summary": "Stable. Injury setback managed well.",
                 "mood_at_session": 7},
                {"date": "2023-06-15", "therapist": "Dr. Daniel Cho",
                 "type": "CBT", "notes_summary": "Annual check-in. Excellent progress. Monthly sessions.",
                 "mood_at_session": 8},
                {"date": "2024-06-10", "therapist": "Dr. Daniel Cho",
                 "type": "CBT", "notes_summary": "Maintaining well. Discussing tapering Sertraline.",
                 "mood_at_session": 8},
                {"date": "2025-03-15", "therapist": "Dr. Daniel Cho",
                 "type": "CBT", "notes_summary": "Stable on Sertraline 25mg. Career growth stress, well-managed.",
                 "mood_at_session": 8},
            ],
            "mood_entries": [
                # High school
                {"date": "2015-09-01", "score": 7, "energy_level": 8, "anxiety_level": 3, "triggers": ""},
                {"date": "2016-06-01", "score": 7, "energy_level": 7, "anxiety_level": 3, "triggers": "college prep stress"},
                # College — ups and downs
                {"date": "2017-03-01", "score": 6, "energy_level": 6, "anxiety_level": 5, "triggers": "college adjustment, ADHD"},
                {"date": "2017-09-01", "score": 5, "energy_level": 5, "anxiety_level": 6, "triggers": "coursework difficulty"},
                {"date": "2018-03-01", "score": 5, "energy_level": 5, "anxiety_level": 6, "triggers": "internship search anxiety"},
                {"date": "2018-09-01", "score": 5, "energy_level": 6, "anxiety_level": 5, "triggers": "senior year pressure"},
                {"date": "2019-01-01", "score": 6, "energy_level": 6, "anxiety_level": 5, "triggers": "job search"},
                {"date": "2019-06-01", "score": 7, "energy_level": 7, "anxiety_level": 3, "triggers": "graduated, first job offer"},
                # Pandemic
                {"date": "2020-03-15", "score": 4, "energy_level": 4, "anxiety_level": 7, "triggers": "pandemic lockdown, remote start"},
                {"date": "2020-07-01", "score": 5, "energy_level": 5, "anxiety_level": 6, "triggers": "isolation, uncertainty"},
                {"date": "2020-12-01", "score": 5, "energy_level": 5, "anxiety_level": 5, "triggers": ""},
                # First job stress
                {"date": "2021-03-01", "score": 4, "energy_level": 4, "anxiety_level": 7, "triggers": "work overload, imposter syndrome"},
                {"date": "2021-06-01", "score": 4, "energy_level": 4, "anxiety_level": 7, "triggers": "burnout signs, started therapy"},
                {"date": "2021-09-01", "score": 5, "energy_level": 5, "anxiety_level": 5, "triggers": "Sertraline positive effect"},
                {"date": "2021-12-01", "score": 6, "energy_level": 6, "anxiety_level": 4, "triggers": "meditation started"},
                # Recovery and growth
                {"date": "2022-03-01", "score": 7, "energy_level": 7, "anxiety_level": 3, "triggers": ""},
                {"date": "2022-09-01", "score": 7, "energy_level": 7, "anxiety_level": 3, "triggers": "knee pain frustrating"},
                {"date": "2023-03-01", "score": 7, "energy_level": 8, "anxiety_level": 3, "triggers": ""},
                {"date": "2023-09-01", "score": 8, "energy_level": 8, "anxiety_level": 2, "triggers": "promotion at work"},
                {"date": "2024-03-01", "score": 8, "energy_level": 8, "anxiety_level": 2, "triggers": ""},
                {"date": "2024-09-01", "score": 8, "energy_level": 8, "anxiety_level": 2, "triggers": ""},
                {"date": "2025-03-01", "score": 8, "energy_level": 8, "anxiety_level": 2, "triggers": "new project pressure, managed well"},
                {"date": "2026-01-01", "score": 8, "energy_level": 8, "anxiety_level": 2, "triggers": ""},
            ],
            "mental_conditions": [
                {"name": "Mild Anxiety Disorder", "diagnosed_date": "2021-06-10",
                 "status": "managed", "treating_provider": "Dr. Daniel Cho / Dr. Priya Nair"},
                {"name": "ADHD — Combined Presentation", "diagnosed_date": "2012-08-20",
                 "status": "managed", "treating_provider": "Dr. Priya Nair"},
            ],
            "stressors": [
                {"description": "College academic pressure combined with unmanaged ADHD",
                 "category": "academic", "intensity": 6,
                 "start_date": "2017-09-01", "resolved_date": "2019-05-15"},
                {"description": "COVID-19 pandemic — social isolation and remote work anxiety",
                 "category": "other", "intensity": 7,
                 "start_date": "2020-03-15", "resolved_date": "2021-06-01"},
                {"description": "First tech job — imposter syndrome and 60-hour weeks",
                 "category": "work", "intensity": 8,
                 "start_date": "2021-01-15", "resolved_date": "2022-03-01"},
                {"description": "Knee injury — workout disruption and identity as athlete",
                 "category": "health", "intensity": 5,
                 "start_date": "2023-01-10", "resolved_date": "2023-06-01"},
            ],
            "journal_entries": [
                {"date": "2018-10-15",
                 "text_summary": "Starting therapy for the first time. Hard to admit I needed help. ADHD has been wrecking my focus all semester. Hoping CBT helps.",
                 "sentiment": "neutral", "key_themes": "ADHD, academic struggle, help-seeking"},
                {"date": "2020-03-25",
                 "text_summary": "Day 10 of quarantine. Can't believe my first real job starts remotely. Never met my team. Feel anxious all the time.",
                 "sentiment": "negative", "key_themes": "pandemic, isolation, work anxiety"},
                {"date": "2021-06-20",
                 "text_summary": "Started Sertraline and back in therapy. The work pressure has been overwhelming. Tech moves so fast. Feeling behind all the time.",
                 "sentiment": "negative", "key_themes": "burnout, imposter syndrome, medication"},
                {"date": "2021-12-10",
                 "text_summary": "6 months on Sertraline + therapy. Sleep is better. Still in the deep end at work but not drowning. Meditation is helping.",
                 "sentiment": "neutral", "key_themes": "progress, medication response, meditation"},
                {"date": "2023-09-10",
                 "text_summary": "Got promoted to Senior Engineer. Knee is fully healed — ran a 5K last month! Therapy monthly now. Feeling the most stable and confident I ever have.",
                 "sentiment": "positive", "key_themes": "career growth, physical recovery, confidence"},
                {"date": "2025-03-20",
                 "text_summary": "27 this year. LDL crept up slightly at last physical — need to clean up diet. But overall, life feels very manageable. ADHD is part of me, not a barrier.",
                 "sentiment": "positive", "key_themes": "health monitoring, acceptance, adulthood"},
            ],
            "meditation_sessions": [
                {"date": "2021-09-01", "duration_mins": 5, "type": "mindfulness",
                 "app_used": "Headspace", "notes": "Started daily practice"},
                {"date": "2021-12-01", "duration_mins": 10, "type": "mindfulness",
                 "app_used": "Headspace", "notes": "Building consistency"},
                {"date": "2022-04-01", "duration_mins": 10, "type": "breathwork",
                 "app_used": "Wim Hof Method", "notes": "Added breathwork for focus"},
                {"date": "2022-09-01", "duration_mins": 12, "type": "mindfulness",
                 "app_used": "Calm", "notes": "Switched to Calm"},
                {"date": "2023-03-01", "duration_mins": 15, "type": "mindfulness",
                 "app_used": "Calm", "notes": "Daily for 18 months"},
                {"date": "2023-09-01", "duration_mins": 15, "type": "body_scan",
                 "app_used": "Calm", "notes": "Added body scan before sleep"},
                {"date": "2024-03-01", "duration_mins": 15, "type": "mindfulness",
                 "app_used": "Calm", "notes": "Consistent daily practice"},
                {"date": "2024-09-01", "duration_mins": 15, "type": "mindfulness",
                 "app_used": "Calm", "notes": "3 years daily"},
                {"date": "2025-09-01", "duration_mins": 15, "type": "mindfulness",
                 "app_used": "Calm", "notes": "4 years daily"},
            ],
        },
        "seed://mental_health_history",
        {"date": "2025-03-15", "title": "Mental Health History 2018-2025", "doc_type": "mental_health_record"},
    )
    console.print("[green]✓ Therapy sessions (college 2018-2019, pandemic 2020, work burnout 2021-2025)[/green]")
    console.print("[green]✓ Mood entries 2015-2026 (7→4 dip→8 sustained recovery)[/green]")
    console.print("[green]✓ Stressors, journal entries, meditation (4+ years daily)[/green]")

    # ── GENETICS VERTICAL ─────────────────────────────────────────────────────

    console.rule("[bold]Genetics Vertical[/bold]")

    from src.domains.healthcare.verticals.genetics.graph_builder import GeneticsGraphBuilder
    gen_builder = GeneticsGraphBuilder(neo4j)

    gen_builder.build(
        {
            "genes": [
                {"name": "APOE", "chromosome": "19",
                 "function": "Lipid transport and Alzheimer's risk modulation"},
                {"name": "TCF7L2", "chromosome": "10",
                 "function": "Transcription factor — highest-impact T2D risk gene"},
                {"name": "SLC30A8", "chromosome": "8",
                 "function": "Zinc transporter — insulin secretion, T2D risk"},
                {"name": "CYP2D6", "chromosome": "22",
                 "function": "Drug metabolism enzyme — antidepressants, stimulants, opioids"},
                {"name": "CYP2C19", "chromosome": "10",
                 "function": "Drug metabolism enzyme — antidepressants, PPIs, clopidogrel"},
                {"name": "MTHFR", "chromosome": "1",
                 "function": "Folate metabolism — homocysteine regulation, cardiovascular risk"},
                {"name": "ALDH2", "chromosome": "12",
                 "function": "Alcohol metabolism — East/South Asian flush reaction"},
                {"name": "LCT", "chromosome": "2",
                 "function": "Lactase persistence — lactose tolerance in adulthood"},
                {"name": "HLA-DQ2/DQ8", "chromosome": "6",
                 "function": "Immune receptor — celiac disease and autoimmune T1D risk"},
            ],
            "genetic_variants": [
                {"rsid": "rs429358", "gene": "APOE", "variant_type": "SNP",
                 "genotype": "ε3/ε3", "significance": "benign"},
                {"rsid": "rs7903146", "gene": "TCF7L2", "variant_type": "SNP",
                 "genotype": "CT (heterozygous)", "significance": "risk_factor"},
                {"rsid": "rs13266634", "gene": "SLC30A8", "variant_type": "SNP",
                 "genotype": "CT", "significance": "risk_factor"},
                {"rsid": "rs1065852", "gene": "CYP2D6", "variant_type": "SNP",
                 "genotype": "*4 allele (reduced function)", "significance": "uncertain"},
                {"rsid": "rs4244285", "gene": "CYP2C19", "variant_type": "SNP",
                 "genotype": "*2/*1 (intermediate metabolizer)", "significance": "uncertain"},
                {"rsid": "rs1801133", "gene": "MTHFR", "variant_type": "SNP",
                 "genotype": "CT (C677T heterozygous)", "significance": "uncertain"},
                {"rsid": "rs671", "gene": "ALDH2", "variant_type": "SNP",
                 "genotype": "GG (normal — no flush variant)", "significance": "benign"},
                {"rsid": "rs4988235", "gene": "LCT", "variant_type": "SNP",
                 "genotype": "CC (lactase non-persistent)", "significance": "uncertain"},
                {"rsid": "rs2395182", "gene": "HLA-DQ2/DQ8", "variant_type": "SNP",
                 "genotype": "DQ8 negative, DQ2 partial", "significance": "benign"},
            ],
            "genetic_risks": [
                {"condition_name": "Type 2 Diabetes",
                 "risk_level": "moderate",
                 "genes_involved": ["TCF7L2", "SLC30A8"],
                 "recommendations": "Monitor HbA1c annually. Maintain healthy weight and exercise. South Asian ethnicity further elevates baseline risk. TCF7L2 CT variant reduces insulin secretion efficacy."},
                {"condition_name": "Alzheimer's Disease",
                 "risk_level": "low",
                 "genes_involved": ["APOE"],
                 "recommendations": "APOE ε3/ε3 — population-average risk. Maintain cardiovascular health and cognitive engagement. No specific additional monitoring required."},
                {"condition_name": "Cardiovascular Disease (Hyperhomocysteinemia)",
                 "risk_level": "moderate",
                 "genes_involved": ["MTHFR"],
                 "recommendations": "MTHFR C677T heterozygous — mildly elevated homocysteine possible. Take methylfolate (not folic acid) supplementation. Recheck homocysteine levels. Avoid high alcohol intake."},
                {"condition_name": "Lactose Intolerance",
                 "risk_level": "high",
                 "genes_involved": ["LCT"],
                 "recommendations": "LCT CC — high likelihood of lactase non-persistence (common in South Asians). Consider lactase enzyme supplements with dairy. Prioritize calcium through non-dairy sources."},
                {"condition_name": "ADHD Medication Response (Stimulant Metabolism)",
                 "risk_level": "moderate",
                 "genes_involved": ["CYP2D6"],
                 "recommendations": "CYP2D6 reduced function allele — may metabolize amphetamine-based stimulants (Adderall) more slowly than average. Monitor for elevated plasma levels and side effects at standard doses."},
            ],
            "pharmacogenes": [
                {"gene": "CYP2D6",
                 "drug_metabolism": "intermediate",
                 "affected_drugs": ["Adderall (amphetamine)", "Sertraline", "Codeine",
                                    "Tramadol", "Metoprolol", "Atomoxetine", "Duloxetine"]},
                {"gene": "CYP2C19",
                 "drug_metabolism": "intermediate",
                 "affected_drugs": ["Sertraline", "Escitalopram", "Citalopram",
                                    "Omeprazole", "Clopidogrel", "Diazepam"]},
                {"gene": "MTHFR",
                 "drug_metabolism": "reduced",
                 "affected_drugs": ["Methotrexate", "Folic acid (prefer methylfolate form)"]},
            ],
            "ancestry_segments": [
                {"population": "South Indian (Dravidian)", "percentage": 72, "confidence": "high"},
                {"population": "North Indian (Indo-Aryan)", "percentage": 18, "confidence": "high"},
                {"population": "Sri Lankan", "percentage": 6, "confidence": "moderate"},
                {"population": "Other South Asian", "percentage": 4, "confidence": "low"},
            ],
            "genetic_report": {
                "provider": "23andMe Health + Ancestry",
                "report_date": "2023-11-10",
                "test_type": "SNP_array",
            },
        },
        "seed://genetics_report_2023",
        {"date": "2023-11-10", "title": "23andMe Genetic Report 2023", "doc_type": "genetic_report"},
    )
    console.print("[green]✓ Genetic report: 9 genes, T2D moderate risk (TCF7L2), APOE low risk[/green]")
    console.print("[green]✓ MTHFR C677T — moderate cardiovascular risk (methylfolate note)[/green]")
    console.print("[green]✓ LCT CC — lactose intolerance (high — common South Asian)[/green]")
    console.print("[green]✓ Pharmacogenes: CYP2D6 intermediate (⚠ Adderall metabolism), CYP2C19 intermediate[/green]")
    console.print("[green]✓ Ancestry: 72% South Indian (Dravidian), 18% North Indian[/green]")

    # ── CROSS-VERTICAL LINKER ─────────────────────────────────────────────────

    console.rule("[bold]Running Cross-Vertical Linker[/bold]")

    from src.domains.healthcare.cross_vertical_linker import HealthcareCrossVerticalLinker
    linker = HealthcareCrossVerticalLinker(neo4j)
    counts = linker.run_all_links()

    console.print("[green]✓ Supplement interactions: L-Theanine+Adderall (modifier), Ashwagandha+Sertraline (monitor)[/green]")
    console.print("[green]✓ Genetic-medication: CYP2D6 intermediate → Adderall slow metabolism[/green]")
    console.print("[green]✓ Genetic-risk: TCF7L2 + South Asian ancestry → elevated T2D watch[/green]")
    console.print(f"[green]✓ Cross-vertical links created: {sum(counts.values())} total[/green]")

    # ── FINAL SUMMARY ─────────────────────────────────────────────────────────

    console.rule("[bold green]Seed Complete[/bold green]")
    summary = {
        "Person": neo4j.run_query("MATCH (p:Person) RETURN count(p) as c")[0]["c"],
        "Conditions": neo4j.run_query("MATCH (c:Condition) RETURN count(c) as c")[0]["c"],
        "Medications": neo4j.run_query("MATCH (m:Medication) RETURN count(m) as c")[0]["c"],
        "Supplements": neo4j.run_query("MATCH (s:Supplement) RETURN count(s) as c")[0]["c"],
        "Lab Results": neo4j.run_query("MATCH (l:LabResult) RETURN count(l) as c")[0]["c"],
        "Vitals": neo4j.run_query("MATCH (v:Vital) RETURN count(v) as c")[0]["c"],
        "Procedures": neo4j.run_query("MATCH (pr:Procedure) RETURN count(pr) as c")[0]["c"],
        "Vaccines": neo4j.run_query("MATCH (v:Vaccine) RETURN count(v) as c")[0]["c"],
        "Hospitalizations": neo4j.run_query("MATCH (h:Hospitalization) RETURN count(h) as c")[0]["c"],
        "Workouts": neo4j.run_query("MATCH (w:Workout) RETURN count(w) as c")[0]["c"],
        "Body Metrics": neo4j.run_query("MATCH (bm:BodyMetric) RETURN count(bm) as c")[0]["c"],
        "Sleep Records": neo4j.run_query("MATCH (sr:SleepRecord) RETURN count(sr) as c")[0]["c"],
        "Mood Entries": neo4j.run_query("MATCH (me:MoodEntry) RETURN count(me) as c")[0]["c"],
        "Therapy Sessions": neo4j.run_query("MATCH (ts:TherapySession) RETURN count(ts) as c")[0]["c"],
        "Stressors": neo4j.run_query("MATCH (s:Stressor) RETURN count(s) as c")[0]["c"],
        "Genes": neo4j.run_query("MATCH (g:Gene) RETURN count(g) as c")[0]["c"],
        "Genetic Risks": neo4j.run_query("MATCH (gr:GeneticRisk) RETURN count(gr) as c")[0]["c"],
        "Pharmacogenes": neo4j.run_query("MATCH (pg:Pharmacogene) RETURN count(pg) as c")[0]["c"],
    }
    for label, count in summary.items():
        console.print(f"  {label}: [bold]{count}[/bold]")

    console.print("\n[bold green]✓ Ganesh's healthcare knowledge base seeded successfully![/bold green]")
    console.print("[dim]Run: python scripts/query.py --question 'What medications am I on?' --domains healthcare[/dim]")
    console.print("[dim]Run: python scripts/query.py --question 'What are my genetic risks?' --domains healthcare[/dim]")


if __name__ == "__main__":
    main()
