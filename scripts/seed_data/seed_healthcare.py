#!/usr/bin/env python3
"""
30-year synthetic healthcare history for Alex Johnson (1985-03-15).
Covers 1995–2025 across all 4 healthcare verticals.
Run: python scripts/seed_data/seed_healthcare.py
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

    console.print("[bold cyan]Life Intelligence — Healthcare Seed Data Generator[/bold cyan]")
    console.print("[dim]Seeding 30 years of synthetic healthcare data (1995–2025)...[/dim]\n")

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
        name="Alex Johnson",
        dob="1985-03-15",
        sex="Male",
        blood_type="O+",
    )
    console.print("[green]✓ Person: Alex Johnson (DOB 1985-03-15, Male, O+)[/green]")

    # Register domain
    from src.domains.healthcare.domain import HealthcareDomain
    hc = HealthcareDomain(neo4j, vector)
    hc.register()

    # ── MEDICAL VERTICAL ──────────────────────────────────────────────────────

    console.rule("[bold]Medical Vertical[/bold]")

    from src.domains.healthcare.verticals.medical.graph_builder import MedicalGraphBuilder
    med_builder = MedicalGraphBuilder(neo4j)

    # 1. Allergies (discovered early childhood)
    med_builder.build(
        {
            "conditions": [],
            "medications": [
                {"name": "Albuterol", "dosage": "90mcg/puff", "frequency": "as needed",
                 "prescribed_date": "1992-06-01", "prescriber": "Dr. Robert Hill",
                 "indication": "Childhood Asthma"},
                {"name": "Methylphenidate", "dosage": "10mg", "frequency": "once daily",
                 "prescribed_date": "1998-09-01", "prescriber": "Dr. Sandra Lee",
                 "indication": "ADHD"},
            ],
            "symptoms": [],
            "lab_results": [],
            "vitals": [],
            "allergies": [
                {"allergen": "Penicillin", "reaction": "Anaphylaxis",
                 "severity": "anaphylaxis", "discovered_date": "1997-04-10"},
                {"allergen": "Peanuts", "reaction": "Hives and throat swelling",
                 "severity": "severe", "discovered_date": "1999-07-15"},
            ],
            "procedures": [],
            "vaccines": [
                {"name": "MMR", "date": "1987-03-20", "lot_number": "L1987A", "provider": "Pediatric Clinic"},
                {"name": "DTaP", "date": "1988-06-15", "lot_number": "L1988B", "provider": "Pediatric Clinic"},
                {"name": "Varicella", "date": "1991-09-10", "lot_number": "L1991C", "provider": "Pediatric Clinic"},
                {"name": "Hepatitis B", "date": "1992-01-20", "lot_number": "L1992A", "provider": "Pediatric Clinic"},
                {"name": "Influenza", "date": "2005-10-15", "lot_number": "FL2005", "provider": "CVS Pharmacy"},
            ],
            "hospitalizations": [],
            "providers": [
                {"name": "Dr. Robert Hill", "specialty": "Pediatrics",
                 "institution": "Children's Medical Center", "contact": "617-555-0101"},
            ],
        },
        "seed://childhood_records",
        {"date": "1999-07-15", "title": "Childhood Medical Records", "doc_type": "medical_history"},
    )
    console.print("[green]✓ Childhood records (allergies, vaccines, Albuterol, Methylphenidate)[/green]")

    # 2. Conditions diagnosed over the years
    med_builder.build(
        {
            "conditions": [
                {"name": "Childhood Asthma", "icd_code": "J45.909", "status": "resolved",
                 "diagnosed_date": "1992-06-01", "severity": "moderate"},
                {"name": "ADHD", "icd_code": "F90.0", "status": "managed",
                 "diagnosed_date": "1998-09-01", "severity": "moderate"},
                {"name": "Hypertension", "icd_code": "I10", "status": "chronic",
                 "diagnosed_date": "2012-03-15", "severity": "mild"},
                {"name": "Anxiety Disorder", "icd_code": "F41.1", "status": "chronic",
                 "diagnosed_date": "2010-08-20", "severity": "moderate"},
                {"name": "Type 2 Diabetes", "icd_code": "E11.9", "status": "chronic",
                 "diagnosed_date": "2017-02-14", "severity": "moderate"},
                {"name": "Vitamin D Deficiency", "icd_code": "E55.9", "status": "resolved",
                 "diagnosed_date": "2016-05-10", "severity": "mild"},
                {"name": "Hyperlipidemia", "icd_code": "E78.5", "status": "chronic",
                 "diagnosed_date": "2021-01-20", "severity": "mild"},
                {"name": "Mild Depression", "icd_code": "F32.1", "status": "active",
                 "diagnosed_date": "2020-04-10", "severity": "mild"},
            ],
            "medications": [
                {"name": "Lisinopril", "dosage": "10mg", "frequency": "once daily",
                 "prescribed_date": "2012-03-15", "prescriber": "Dr. Sarah Chen",
                 "indication": "Hypertension"},
                {"name": "Sertraline", "dosage": "50mg", "frequency": "once daily",
                 "prescribed_date": "2010-08-20", "prescriber": "Dr. Sarah Chen",
                 "indication": "Anxiety Disorder"},
                {"name": "Metformin", "dosage": "500mg", "frequency": "twice daily",
                 "prescribed_date": "2017-02-14", "prescriber": "Dr. Michael Torres",
                 "indication": "Type 2 Diabetes"},
                {"name": "Vitamin D3", "dosage": "2000IU", "frequency": "once daily",
                 "prescribed_date": "2016-05-10", "prescriber": "Dr. Sarah Chen",
                 "indication": "Vitamin D Deficiency"},
                {"name": "Atorvastatin", "dosage": "20mg", "frequency": "once daily",
                 "prescribed_date": "2021-01-20", "prescriber": "Dr. Sarah Chen",
                 "indication": "Hyperlipidemia"},
                {"name": "Escitalopram", "dosage": "10mg", "frequency": "once daily",
                 "prescribed_date": "2020-04-10", "prescriber": "Dr. Sarah Chen",
                 "indication": "Mild Depression"},
            ],
            "symptoms": [],
            "lab_results": [],
            "vitals": [],
            "allergies": [],
            "procedures": [
                {"name": "Appendectomy", "date": "2008-07-22",
                 "provider": "Dr. James Wilson", "location": "Massachusetts General Hospital",
                 "notes": "Laparoscopic appendectomy, uncomplicated"},
                {"name": "Colonoscopy", "date": "2018-05-10",
                 "provider": "Dr. Patricia Wang", "location": "Boston Medical Center",
                 "notes": "Routine screening, no polyps found"},
                {"name": "Diabetic retinal exam", "date": "2018-09-15",
                 "provider": "Dr. Lisa Patel", "location": "Eye Care Associates",
                 "notes": "No diabetic retinopathy detected"},
                {"name": "Diabetic retinal exam", "date": "2020-09-20",
                 "provider": "Dr. Lisa Patel", "location": "Eye Care Associates",
                 "notes": "No diabetic retinopathy, mild microaneurysm watch"},
                {"name": "Diabetic foot exam", "date": "2022-03-10",
                 "provider": "Dr. Michael Torres", "location": "Boston Endocrinology",
                 "notes": "Normal sensation, no neuropathy"},
                {"name": "Diabetic foot exam", "date": "2024-03-15",
                 "provider": "Dr. Michael Torres", "location": "Boston Endocrinology",
                 "notes": "Normal, continue monitoring"},
            ],
            "vaccines": [
                {"name": "COVID-19 mRNA (Pfizer)", "date": "2021-03-15",
                 "lot_number": "EW0182", "provider": "Mass Vaccination Site"},
                {"name": "COVID-19 mRNA Booster", "date": "2021-11-20",
                 "lot_number": "FK3921", "provider": "CVS Pharmacy"},
                {"name": "COVID-19 Bivalent Booster", "date": "2022-10-05",
                 "lot_number": "BV2022", "provider": "CVS Pharmacy"},
                {"name": "Tdap", "date": "2015-06-01",
                 "lot_number": "TD2015", "provider": "Boston Medical Center"},
                {"name": "Shingrix (dose 1)", "date": "2023-04-10",
                 "lot_number": "SHX001", "provider": "Walgreens"},
                {"name": "Shingrix (dose 2)", "date": "2023-06-15",
                 "lot_number": "SHX002", "provider": "Walgreens"},
            ],
            "hospitalizations": [
                {"reason": "Appendicitis / Appendectomy",
                 "admit_date": "2008-07-21", "discharge_date": "2008-07-24",
                 "facility": "Massachusetts General Hospital",
                 "discharge_summary": "Laparoscopic appendectomy. Uncomplicated recovery. Discharged home on oral antibiotics."},
                {"reason": "Community-acquired Pneumonia",
                 "admit_date": "2019-12-03", "discharge_date": "2019-12-06",
                 "facility": "Boston Medical Center",
                 "discharge_summary": "Treated with IV ceftriaxone and azithromycin, transitioned to oral antibiotics. Full recovery. Note: Blood glucose elevated during admission due to stress response."},
            ],
            "providers": [
                {"name": "Dr. Sarah Chen", "specialty": "Internal Medicine",
                 "institution": "Boston Medical Center", "contact": "617-555-0200"},
                {"name": "Dr. Michael Torres", "specialty": "Endocrinology",
                 "institution": "Boston Endocrinology Associates", "contact": "617-555-0300"},
                {"name": "Dr. James Wilson", "specialty": "General Surgery",
                 "institution": "Massachusetts General Hospital", "contact": "617-555-0400"},
                {"name": "Dr. Patricia Wang", "specialty": "Gastroenterology",
                 "institution": "Boston Medical Center", "contact": "617-555-0500"},
            ],
        },
        "seed://conditions_and_medications",
        {"date": "2024-01-01", "title": "Comprehensive Medical History 1992-2024", "doc_type": "medical_history"},
    )
    console.print("[green]✓ Conditions, medications, procedures, hospitalizations[/green]")

    # 3. Lab results — HbA1c trend over time (key diabetes tracking)
    hba1c_data = [
        ("2016-01-15", "5.8", "pre-diabetic range"),
        ("2017-02-14", "6.2", "pre-diabetes confirmed"),
        ("2017-09-10", "7.1", "T2D diagnosis confirmed"),
        ("2018-03-15", "6.8", "improving with Metformin"),
        ("2018-09-20", "6.5", "good response to treatment"),
        ("2019-03-10", "6.7", "slight rise, stress related"),
        ("2019-09-15", "6.4", "back on track"),
        ("2020-03-20", "6.6", "pandemic stress effect"),
        ("2020-09-10", "6.3", "lifestyle improvements"),
        ("2021-03-15", "6.2", "excellent control"),
        ("2021-09-20", "6.0", "near-normal"),
        ("2022-03-10", "6.1", "stable"),
        ("2022-09-15", "6.0", "sustained control"),
        ("2023-03-20", "5.9", "near target"),
        ("2023-09-10", "6.0", "stable"),
        ("2024-03-15", "6.1", "annual review, stable"),
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

    # Additional labs — lipid panels
    lipid_data = [
        ("2015-01-10", "Total Cholesterol", "195", "mg/dL", "<200", False),
        ("2017-01-15", "Total Cholesterol", "210", "mg/dL", "<200", True),
        ("2019-01-20", "Total Cholesterol", "225", "mg/dL", "<200", True),
        ("2019-01-20", "LDL", "148", "mg/dL", "<100", True),
        ("2019-01-20", "HDL", "42", "mg/dL", ">40", False),
        ("2019-01-20", "Triglycerides", "185", "mg/dL", "<150", True),
        ("2021-01-15", "Total Cholesterol", "238", "mg/dL", "<200", True),
        ("2021-01-15", "LDL", "162", "mg/dL", "<100", True),
        ("2021-09-10", "Total Cholesterol", "198", "mg/dL", "<200", False),  # after statin
        ("2021-09-10", "LDL", "108", "mg/dL", "<100", True),
        ("2023-01-15", "Total Cholesterol", "182", "mg/dL", "<200", False),
        ("2023-01-15", "LDL", "95", "mg/dL", "<100", False),
        ("2023-01-15", "HDL", "48", "mg/dL", ">40", False),
        ("2024-01-20", "Total Cholesterol", "175", "mg/dL", "<200", False),
        ("2024-01-20", "LDL", "88", "mg/dL", "<100", False),
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

    console.print("[green]✓ HbA1c trend (2016-2024) + lipid panels[/green]")

    # Blood pressure vitals
    bp_data = [
        ("2012-03-15", "128/85"), ("2013-06-10", "132/88"), ("2014-09-15", "130/86"),
        ("2015-03-20", "126/82"), ("2016-05-10", "124/80"), ("2017-02-14", "138/90"),
        ("2018-09-20", "132/86"), ("2019-12-05", "145/95"), ("2020-04-10", "128/84"),
        ("2021-03-15", "122/80"), ("2022-03-10", "120/78"), ("2023-01-15", "118/76"),
        ("2024-03-15", "120/78"),
    ]
    for (date_, bp) in bp_data:
        systolic, diastolic = bp.split("/")
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
    console.print("[green]✓ Blood pressure vitals (2012-2024)[/green]")

    # ── FITNESS VERTICAL ──────────────────────────────────────────────────────

    console.rule("[bold]Fitness Vertical[/bold]")

    from src.domains.healthcare.verticals.fitness.graph_builder import FitnessGraphBuilder
    fit_builder = FitnessGraphBuilder(neo4j)

    # Body weight progression (quarterly 2005-2025)
    weight_data = [
        ("2005-03-01", "165", "lbs"),  # College athlete
        ("2007-06-01", "168", "lbs"),
        ("2009-09-01", "175", "lbs"),  # Post-college, gym
        ("2011-03-01", "182", "lbs"),
        ("2013-06-01", "190", "lbs"),  # Sedentary job begins
        ("2015-09-01", "205", "lbs"),
        ("2016-06-01", "215", "lbs"),
        ("2017-02-01", "218", "lbs"),  # Pre-diabetes diagnosis
        ("2017-06-01", "212", "lbs"),  # Lifestyle change
        ("2018-03-01", "205", "lbs"),
        ("2019-03-01", "198", "lbs"),
        ("2020-06-01", "195", "lbs"),
        ("2021-06-01", "190", "lbs"),
        ("2022-06-01", "187", "lbs"),
        ("2023-06-01", "185", "lbs"),
        ("2024-06-01", "183", "lbs"),
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
    console.print("[green]✓ Body weight trend 2005-2024 (165→218→183 lbs)[/green]")

    # Supplements (with known interactions)
    supplements = [
        ("Omega-3 Fish Oil", "1000mg", "once daily", "Nature Made", "Cardiovascular health, started 2018", "2018-01-01"),
        ("Magnesium Glycinate", "400mg", "once daily", "Doctor's Best", "Sleep quality, started 2021", "2021-06-01"),
        ("Berberine", "500mg", "twice daily", "Thorne", "Blood sugar support, started 2022", "2022-03-01"),
        ("Vitamin D3", "2000IU", "once daily", "NOW Foods", "Deficiency treatment, started 2016", "2016-05-10"),
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
            {"name": name, "dosage": dosage, "freq": freq, "brand": brand, "purpose": purpose, "date": date_},
        )
    console.print("[green]✓ Supplements: Omega-3, Magnesium, Berberine (⚠+Metformin), Vitamin D3[/green]")

    # Workout records (post-diabetes lifestyle change 2017+)
    workouts_2017_2024 = [
        ("2017-06-10", "walking", 45, 200, "low"),
        ("2017-07-15", "cycling", 60, 320, "moderate"),
        ("2018-01-10", "running", 30, 280, "moderate"),
        ("2018-06-20", "strength_training", 45, 220, "moderate"),
        ("2019-03-15", "running", 45, 380, "moderate"),
        ("2019-09-10", "cycling", 90, 480, "high"),
        ("2020-01-20", "running", 40, 340, "moderate"),
        ("2020-07-15", "strength_training", 50, 260, "high"),
        ("2021-03-10", "running", 50, 420, "high"),
        ("2021-09-20", "cycling", 75, 450, "high"),
        ("2022-03-15", "strength_training", 55, 280, "high"),
        ("2022-09-10", "running", 50, 410, "high"),
        ("2023-03-20", "running", 55, 440, "high"),
        ("2023-09-15", "strength_training", 60, 300, "high"),
        ("2024-03-10", "running", 50, 415, "high"),
        ("2024-09-15", "cycling", 80, 490, "high"),
    ]
    for (date_, wtype, duration, calories, intensity) in workouts_2017_2024:
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
    console.print("[green]✓ Workout history 2017-2024 (lifestyle change after T2D diagnosis)[/green]")

    # Sleep records (worsening 2015-2018, improving after)
    sleep_data = [
        ("2015-06-01", 5.5, 4, 1.0), ("2015-12-01", 5.2, 3, 0.8),
        ("2016-06-01", 5.4, 4, 1.0), ("2016-12-01", 5.0, 3, 0.8),
        ("2017-06-01", 5.5, 4, 1.1), ("2017-12-01", 6.0, 5, 1.2),
        ("2018-06-01", 6.3, 6, 1.4), ("2018-12-01", 6.5, 6, 1.5),
        ("2019-06-01", 6.8, 7, 1.6), ("2019-12-01", 6.0, 5, 1.2),
        ("2020-06-01", 6.5, 6, 1.4), ("2020-12-01", 6.8, 7, 1.6),
        ("2021-06-01", 7.0, 7, 1.7), ("2021-12-01", 7.2, 8, 1.8),
        ("2022-06-01", 7.1, 8, 1.7), ("2022-12-01", 7.3, 8, 1.9),
        ("2023-06-01", 7.2, 8, 1.8), ("2023-12-01", 7.4, 9, 2.0),
        ("2024-06-01", 7.2, 8, 1.8),
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
    console.print("[green]✓ Sleep records 2015-2024 (5.0→7.4 hrs/night)[/green]")

    # ── MENTAL HEALTH VERTICAL ────────────────────────────────────────────────

    console.rule("[bold]Mental Health Vertical[/bold]")

    from src.domains.healthcare.verticals.mental_health.graph_builder import MentalHealthGraphBuilder
    mh_builder = MentalHealthGraphBuilder(neo4j)

    # Mental conditions
    mh_builder.build(
        {
            "therapy_sessions": [
                {"date": "2010-09-05", "therapist": "Dr. Lisa Park",
                 "type": "CBT", "notes_summary": "Initial assessment, moderate anxiety",
                 "mood_at_session": 4},
                {"date": "2011-03-10", "therapist": "Dr. Lisa Park",
                 "type": "CBT", "notes_summary": "Progress with cognitive restructuring",
                 "mood_at_session": 5},
                {"date": "2012-01-15", "therapist": "Dr. Lisa Park",
                 "type": "CBT", "notes_summary": "Significant improvement, reduced avoidance",
                 "mood_at_session": 6},
                {"date": "2013-06-20", "therapist": "Dr. Lisa Park",
                 "type": "CBT", "notes_summary": "Termination session, maintenance plan discussed",
                 "mood_at_session": 7},
                {"date": "2020-05-15", "therapist": "Dr. James Wright",
                 "type": "CBT", "notes_summary": "Pandemic-related depression, grief processing",
                 "mood_at_session": 3},
                {"date": "2020-08-20", "therapist": "Dr. James Wright",
                 "type": "CBT", "notes_summary": "Behavioral activation, improved routine",
                 "mood_at_session": 4},
                {"date": "2021-01-10", "therapist": "Dr. James Wright",
                 "type": "CBT", "notes_summary": "Coping with health anxiety (diabetes)",
                 "mood_at_session": 5},
                {"date": "2021-06-15", "therapist": "Dr. James Wright",
                 "type": "CBT", "notes_summary": "Good progress, working on health acceptance",
                 "mood_at_session": 6},
                {"date": "2022-03-10", "therapist": "Dr. James Wright",
                 "type": "CBT", "notes_summary": "Maintaining gains, reduced session frequency",
                 "mood_at_session": 7},
                {"date": "2023-01-20", "therapist": "Dr. James Wright",
                 "type": "CBT", "notes_summary": "Annual check-in, stable",
                 "mood_at_session": 7},
            ],
            "mood_entries": [
                # 2015-2017 decline (stressful job)
                {"date": "2015-03-01", "score": 6, "energy_level": 6, "anxiety_level": 5, "triggers": "work deadlines"},
                {"date": "2015-09-01", "score": 5, "energy_level": 5, "anxiety_level": 6, "triggers": "work overload"},
                {"date": "2016-03-01", "score": 5, "energy_level": 4, "anxiety_level": 7, "triggers": "financial stress, job pressure"},
                {"date": "2016-09-01", "score": 4, "energy_level": 4, "anxiety_level": 7, "triggers": "poor sleep, work"},
                {"date": "2017-02-01", "score": 3, "energy_level": 3, "anxiety_level": 8, "triggers": "diabetes diagnosis shock"},
                {"date": "2017-06-01", "score": 4, "energy_level": 5, "anxiety_level": 6, "triggers": "adjusting to diabetes management"},
                {"date": "2018-03-01", "score": 5, "energy_level": 6, "anxiety_level": 5, "triggers": "improving health"},
                {"date": "2018-09-01", "score": 6, "energy_level": 6, "anxiety_level": 4, "triggers": ""},
                {"date": "2019-03-01", "score": 6, "energy_level": 7, "anxiety_level": 4, "triggers": ""},
                {"date": "2019-12-01", "score": 4, "energy_level": 4, "anxiety_level": 6, "triggers": "hospitalization, pneumonia"},
                {"date": "2020-03-01", "score": 3, "energy_level": 3, "anxiety_level": 8, "triggers": "pandemic lockdown"},
                {"date": "2020-07-01", "score": 4, "energy_level": 4, "anxiety_level": 7, "triggers": "pandemic fatigue"},
                {"date": "2020-12-01", "score": 5, "energy_level": 5, "anxiety_level": 6, "triggers": "therapy helping"},
                {"date": "2021-06-01", "score": 6, "energy_level": 6, "anxiety_level": 4, "triggers": ""},
                {"date": "2021-12-01", "score": 7, "energy_level": 7, "anxiety_level": 3, "triggers": "meditation started"},
                {"date": "2022-06-01", "score": 7, "energy_level": 7, "anxiety_level": 3, "triggers": ""},
                {"date": "2023-03-01", "score": 7, "energy_level": 8, "anxiety_level": 3, "triggers": ""},
                {"date": "2023-12-01", "score": 8, "energy_level": 8, "anxiety_level": 2, "triggers": ""},
                {"date": "2024-06-01", "score": 8, "energy_level": 8, "anxiety_level": 2, "triggers": ""},
            ],
            "mental_conditions": [
                {"name": "Anxiety Disorder", "diagnosed_date": "2010-08-20",
                 "status": "managed", "treating_provider": "Dr. Lisa Park / Dr. Sarah Chen"},
                {"name": "Mild Depression", "diagnosed_date": "2020-04-10",
                 "status": "active", "treating_provider": "Dr. James Wright"},
            ],
            "stressors": [
                {"description": "High-pressure software job with 60-hour weeks",
                 "category": "work", "intensity": 8,
                 "start_date": "2015-01-01", "resolved_date": "2017-08-01"},
                {"description": "Type 2 Diabetes diagnosis — health anxiety",
                 "category": "health", "intensity": 9,
                 "start_date": "2017-02-14", "resolved_date": "2018-06-01"},
                {"description": "COVID-19 pandemic — isolation and uncertainty",
                 "category": "other", "intensity": 7,
                 "start_date": "2020-03-15", "resolved_date": "2021-06-01"},
                {"description": "Pneumonia hospitalization",
                 "category": "health", "intensity": 7,
                 "start_date": "2019-12-03", "resolved_date": "2019-12-31"},
            ],
            "journal_entries": [
                {"date": "2017-02-20", "text_summary": "Just got diagnosed with diabetes. Feeling overwhelmed and scared. Need to completely change my diet.",
                 "sentiment": "negative", "key_themes": "health anxiety, diagnosis shock, lifestyle change"},
                {"date": "2017-06-10", "text_summary": "3 months on Metformin. Blood sugar is improving. Starting to accept this condition.",
                 "sentiment": "neutral", "key_themes": "acceptance, progress, medication"},
                {"date": "2020-03-20", "text_summary": "Lockdown day 5. Working from home. Feeling isolated and anxious about COVID and my diabetes risk.",
                 "sentiment": "negative", "key_themes": "pandemic, isolation, health anxiety"},
                {"date": "2021-10-15", "text_summary": "6 months of daily meditation. Sleep improved. Blood sugar stable. Feeling the most balanced in years.",
                 "sentiment": "positive", "key_themes": "meditation, progress, balance"},
                {"date": "2023-09-01", "text_summary": "HbA1c at 6.0 - almost normal range! Exercise routine solid. Therapy monthly now.",
                 "sentiment": "positive", "key_themes": "health success, routine, stability"},
            ],
            "meditation_sessions": [
                {"date": "2021-04-01", "duration_mins": 10, "type": "mindfulness", "app_used": "Headspace", "notes": "Started daily practice"},
                {"date": "2021-07-15", "duration_mins": 15, "type": "mindfulness", "app_used": "Headspace", "notes": "Consistent daily"},
                {"date": "2022-01-10", "duration_mins": 15, "type": "breathwork", "app_used": "Calm", "notes": "Added breathwork"},
                {"date": "2022-06-20", "duration_mins": 20, "type": "mindfulness", "app_used": "Calm", "notes": "Increased duration"},
                {"date": "2023-03-15", "duration_mins": 15, "type": "mindfulness", "app_used": "Calm", "notes": "Daily for 2 years"},
                {"date": "2024-01-10", "duration_mins": 15, "type": "mindfulness", "app_used": "Calm", "notes": "Consistent practice"},
            ],
        },
        "seed://mental_health_history",
        {"date": "2024-01-01", "title": "Mental Health History 2010-2024", "doc_type": "mental_health_record"},
    )
    console.print("[green]✓ Therapy sessions (CBT 2010-2013, 2020-2023)[/green]")
    console.print("[green]✓ Mood entries 2015-2024 (6→3→8 trajectory)[/green]")
    console.print("[green]✓ Stressors, journal entries, meditation sessions[/green]")

    # ── GENETICS VERTICAL ─────────────────────────────────────────────────────

    console.rule("[bold]Genetics Vertical[/bold]")

    from src.domains.healthcare.verticals.genetics.graph_builder import GeneticsGraphBuilder
    gen_builder = GeneticsGraphBuilder(neo4j)

    gen_builder.build(
        {
            "genes": [
                {"name": "BRCA2", "chromosome": "13", "function": "Tumor suppressor — DNA damage repair"},
                {"name": "APOE", "chromosome": "19", "function": "Lipid transport and Alzheimer's risk modulation"},
                {"name": "TCF7L2", "chromosome": "10", "function": "Transcription factor linked to Type 2 Diabetes risk"},
                {"name": "KCNQ1", "chromosome": "11", "function": "Potassium channel — cardiac and T2D risk"},
                {"name": "CYP2D6", "chromosome": "22", "function": "Drug metabolism enzyme — antidepressants, opioids"},
                {"name": "CYP2C19", "chromosome": "10", "function": "Drug metabolism enzyme — antidepressants, PPIs"},
            ],
            "genetic_variants": [
                {"rsid": "rs80359550", "gene": "BRCA2", "variant_type": "SNP",
                 "genotype": "heterozygous", "significance": "risk_factor"},
                {"rsid": "rs429358", "gene": "APOE", "variant_type": "SNP",
                 "genotype": "ε3/ε4", "significance": "risk_factor"},
                {"rsid": "rs7903146", "gene": "TCF7L2", "variant_type": "SNP",
                 "genotype": "CT", "significance": "risk_factor"},
                {"rsid": "rs2237892", "gene": "KCNQ1", "variant_type": "SNP",
                 "genotype": "CT", "significance": "risk_factor"},
                {"rsid": "rs3892097", "gene": "CYP2D6", "variant_type": "SNP",
                 "genotype": "reduced function", "significance": "uncertain"},
                {"rsid": "rs4244285", "gene": "CYP2C19", "variant_type": "SNP",
                 "genotype": "*2/*2 (homozygous)", "significance": "pathogenic"},
            ],
            "genetic_risks": [
                {"condition_name": "Breast and Prostate Cancer",
                 "risk_level": "high",
                 "genes_involved": ["BRCA2"],
                 "recommendations": "Annual mammography/prostate screening from age 40. Consider genetic counseling. Discuss prophylactic options with oncologist."},
                {"condition_name": "Alzheimer's Disease",
                 "risk_level": "moderate",
                 "genes_involved": ["APOE"],
                 "recommendations": "Maintain cardiovascular health. Mediterranean diet. Regular cognitive exercise. Monitor with annual cognitive screening after age 60."},
                {"condition_name": "Type 2 Diabetes",
                 "risk_level": "high",
                 "genes_involved": ["TCF7L2", "KCNQ1"],
                 "recommendations": "Confirmed diagnosis. Strict glycemic control. TCF7L2 variant associated with reduced insulin secretion — medication response monitoring important."},
                {"condition_name": "QTc Prolongation",
                 "risk_level": "moderate",
                 "genes_involved": ["KCNQ1"],
                 "recommendations": "Avoid QT-prolonging medications. ECG monitoring. Inform all prescribers. Avoid electrolyte imbalance."},
            ],
            "pharmacogenes": [
                {"gene": "CYP2D6",
                 "drug_metabolism": "intermediate",
                 "affected_drugs": ["Sertraline", "Codeine", "Tramadol", "Metoprolol", "Atomoxetine"]},
                {"gene": "CYP2C19",
                 "drug_metabolism": "poor",
                 "affected_drugs": ["Escitalopram", "Citalopram", "Omeprazole", "Clopidogrel", "Diazepam"]},
            ],
            "ancestry_segments": [
                {"population": "British Isles", "percentage": 45, "confidence": "high"},
                {"population": "Scandinavian", "percentage": 30, "confidence": "high"},
                {"population": "Eastern European", "percentage": 15, "confidence": "moderate"},
                {"population": "Ashkenazi Jewish", "percentage": 10, "confidence": "moderate"},
            ],
            "genetic_report": {
                "provider": "23andMe Health + Ancestry",
                "report_date": "2022-06-15",
                "test_type": "SNP_array",
            },
        },
        "seed://genetics_report_2022",
        {"date": "2022-06-15", "title": "23andMe Genetic Report 2022", "doc_type": "genetic_report"},
    )
    console.print("[green]✓ Genetic report: 6 genes, BRCA2 high risk, APOE moderate, T2D confirmed genetic[/green]")
    console.print("[green]✓ Pharmacogenes: CYP2D6 intermediate (Sertraline), CYP2C19 poor (⚠ Escitalopram)[/green]")
    console.print("[green]✓ Ancestry: 45% British Isles, 30% Scandinavian[/green]")

    # ── CROSS-VERTICAL LINKER ─────────────────────────────────────────────────

    console.rule("[bold]Running Cross-Vertical Linker[/bold]")

    from src.domains.healthcare.cross_vertical_linker import HealthcareCrossVerticalLinker
    linker = HealthcareCrossVerticalLinker(neo4j)
    counts = linker.run_all_links()

    console.print(f"[green]✓ Drug-drug interactions seeded: Sertraline+Escitalopram ⚠ HIGH[/green]")
    console.print(f"[green]✓ Supplement-drug: Berberine+Metformin ⚠ HIGH[/green]")
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

    console.print("\n[bold green]✓ Healthcare knowledge base seeded successfully![/bold green]")
    console.print("[dim]Run: python scripts/query.py --question 'What medications am I on?' --domains healthcare[/dim]")


if __name__ == "__main__":
    main()
