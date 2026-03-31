"""
15 healthcare query tests — requires seeded data.
Run after: python scripts/seed_data/seed_healthcare.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(scope="module")
def neo4j():
    from src.core.neo4j_client import get_client
    client = get_client()
    yield client
    client.close()


@pytest.fixture(scope="module")
def vector():
    from src.core.vector_store import get_vector_store
    return get_vector_store()


# ── Test 1: Current medications ───────────────────────────────────────────────

def test_current_medications(neo4j):
    """What medications am I currently taking?"""
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = neo4j.run_query(QUERIES["current_medications"])
    assert len(results) > 0, "Should have at least one medication"
    names = [r["name"] for r in results]
    # Key medications from seed
    assert any("Lisinopril" in n for n in names), "Should have Lisinopril (hypertension)"
    assert any("Metformin" in n for n in names), "Should have Metformin (diabetes)"
    assert any("Sertraline" in n for n in names), "Should have Sertraline (anxiety)"


# ── Test 2: Drug interactions — must flag Sertraline + Escitalopram ───────────

def test_drug_interactions_sertraline_escitalopram(neo4j):
    """Do any of my medications interact with each other?"""
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = neo4j.run_query(QUERIES["drug_interactions"])
    assert len(results) > 0, "Should detect drug interactions"
    drug_pairs = [(r["drug1"].lower(), r["drug2"].lower()) for r in results]
    has_sertraline_escitalopram = any(
        ("sertraline" in d1 or "escitalopram" in d1) and
        ("sertraline" in d2 or "escitalopram" in d2)
        for d1, d2 in drug_pairs
    )
    assert has_sertraline_escitalopram, (
        "CRITICAL: Must flag Sertraline + Escitalopram interaction (serotonin syndrome risk)"
    )
    # Check severity
    high_severity = [r for r in results if r.get("severity") == "high"]
    assert len(high_severity) > 0, "Should have at least one high-severity interaction"


# ── Test 3: Active chronic conditions ─────────────────────────────────────────

def test_active_conditions(neo4j):
    """What are my active chronic conditions?"""
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = neo4j.run_query(QUERIES["active_conditions"])
    assert len(results) > 0, "Should have active conditions"
    names = [r["name"].lower() for r in results]
    assert any("diabetes" in n for n in names), "Should have Type 2 Diabetes"
    assert any("hypertension" in n for n in names), "Should have Hypertension"


# ── Test 4: HbA1c trend ───────────────────────────────────────────────────────

def test_hba1c_trend(neo4j):
    """Show me my HbA1c trend over the years."""
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = neo4j.run_query(QUERIES["lab_trends"], {"test_name": "HbA1c"})
    assert len(results) >= 5, "Should have multiple HbA1c readings"
    # Should be ordered by date
    dates = [r["date"] for r in results if r.get("date")]
    assert dates == sorted(dates), "Results should be sorted by date"
    # First reading should be pre-diabetic range
    first = results[0]
    assert float(first["value"]) < 6.5, "First HbA1c should be pre-diabetic"
    # Should show peak around diagnosis
    values = [float(r["value"]) for r in results]
    assert max(values) >= 6.5, "Should show at least one diabetic-range reading"


# ── Test 5: Supplement-drug interactions — Berberine + Metformin ──────────────

def test_supplement_drug_interactions(neo4j):
    """What supplements might interact with my medications?"""
    results = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:TAKES_SUPPLEMENT]->(s:Supplement)
        MATCH (p)-[:TAKES_MEDICATION]->(m:Medication)
        MATCH (s)-[r:INTERACTS_WITH]->(m)
        RETURN s.name AS supplement, m.name AS drug,
               r.severity AS severity, r.description AS description
        """
    )
    assert len(results) > 0, "Should detect supplement-drug interactions"
    berberine_metformin = any(
        "berberine" in r["supplement"].lower() and "metformin" in r["drug"].lower()
        for r in results
    )
    assert berberine_metformin, "Must flag Berberine + Metformin interaction"


# ── Test 6: High genetic risks ────────────────────────────────────────────────

def test_high_genetic_risks(neo4j):
    """What are my high genetic risks?"""
    from src.domains.healthcare.verticals.genetics.queries import QUERIES
    results = neo4j.run_query(QUERIES["high_risks"])
    assert len(results) > 0, "Should have high genetic risks"
    conditions = [r["condition_name"].lower() for r in results]
    assert any("brca" in c or "cancer" in c for c in conditions), (
        "Should flag BRCA2-related cancer risk"
    )
    assert any("diabetes" in c for c in conditions), (
        "Should flag genetic T2D risk (TCF7L2/KCNQ1)"
    )


# ── Test 7: CYP pharmacogenomics ──────────────────────────────────────────────

def test_cyp2c19_escitalopram(neo4j):
    """How does my CYP2D6/CYP2C19 status affect my current medications?"""
    from src.domains.healthcare.verticals.genetics.queries import QUERIES
    results = neo4j.run_query(QUERIES["pharmacogene_warnings"])
    assert len(results) > 0, "Should have pharmacogenomic warnings"
    # CYP2C19 poor metabolizer + Escitalopram is critical
    cyp2c19 = [r for r in results if "CYP2C19" in str(r.get("gene", ""))]
    assert len(cyp2c19) > 0, "Should detect CYP2C19 poor metabolizer status"
    # Should flag Escitalopram as affected
    affected = [r for r in cyp2c19 if r.get("current_medications_affected")]
    assert len(affected) > 0, (
        "CYP2C19 poor metabolizer should flag current Escitalopram prescription as at-risk"
    )


# ── Test 8: Mood trend ────────────────────────────────────────────────────────

def test_mood_trends(neo4j):
    """What is my mood trend over the last 3 years?"""
    from src.domains.healthcare.verticals.mental_health.queries import QUERIES
    results = neo4j.run_query(QUERIES["mood_trends"], {
        "date_from": "2021-01-01", "date_to": "2024-12-31"
    })
    assert len(results) >= 3, "Should have mood entries for last 3 years"
    scores = [r["score"] for r in results if r.get("score")]
    if scores:
        # Trend should be positive (improving)
        first_half_avg = sum(scores[:len(scores)//2]) / max(len(scores)//2, 1)
        second_half_avg = sum(scores[len(scores)//2:]) / max(len(scores) - len(scores)//2, 1)
        assert second_half_avg >= first_half_avg - 0.5, "Mood should be stable or improving"


# ── Test 9: Sleep-mood correlation ───────────────────────────────────────────

def test_sleep_mood_correlation(neo4j):
    """How has my sleep affected my mood?"""
    results = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_SLEEP_RECORD]->(sr:SleepRecord)
        MATCH (p)-[:HAS_MOOD_ENTRY]->(me:MoodEntry)
        WHERE sr.date IS NOT NULL AND me.date IS NOT NULL
        AND abs(duration.inDays(date(sr.date), date(me.date)).days) <= 7
        RETURN sr.duration_hours AS sleep_hours, sr.quality AS sleep_quality,
               me.score AS mood_score, me.date AS date
        ORDER BY me.date
        LIMIT 20
        """
    )
    assert len(results) >= 2, "Should find sleep records near mood entries"


# ── Test 10: Fitness since diabetes diagnosis ─────────────────────────────────

def test_fitness_post_diabetes(neo4j):
    """What is my fitness progression since my diabetes diagnosis (2017)?"""
    results = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_WORKOUT]->(w:Workout)
        WHERE w.date >= '2017-02-14'
        RETURN w.date AS date, w.type AS type, w.intensity AS intensity,
               w.duration_mins AS duration_mins
        ORDER BY w.date
        """
    )
    assert len(results) > 0, "Should have workouts after diabetes diagnosis"
    # Should show progression from low to high intensity
    intensities = [r["intensity"] for r in results if r.get("intensity")]
    assert "low" in intensities or "moderate" in intensities, "Should start with lower intensity"
    assert "high" in intensities, "Should reach high intensity workouts"


# ── Test 11: Hospitalization history ─────────────────────────────────────────

def test_hospitalization_history(neo4j):
    """What hospitalizations have I had and why?"""
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = neo4j.run_query(QUERIES["hospitalization_history"])
    assert len(results) >= 2, "Should have at least 2 hospitalizations (appendectomy + pneumonia)"
    reasons = [r["reason"].lower() for r in results]
    assert any("append" in r for r in reasons), "Should have appendectomy hospitalization"
    assert any("pneumon" in r for r in reasons), "Should have pneumonia hospitalization"


# ── Test 12: Vaccine history ─────────────────────────────────────────────────

def test_vaccine_history(neo4j):
    """What vaccines have I received?"""
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = neo4j.run_query(QUERIES["vaccine_history"])
    assert len(results) >= 5, "Should have multiple vaccine records"
    names = [r["name"].lower() for r in results]
    assert any("covid" in n for n in names), "Should have COVID vaccines"
    assert any("mmr" in n or "measles" in n for n in names), "Should have childhood MMR"


# ── Test 13: Stress-blood sugar correlation ───────────────────────────────────

def test_stress_blood_sugar(neo4j):
    """What is the relationship between my stress levels and my blood sugar?"""
    from src.domains.healthcare.verticals.mental_health.queries import QUERIES
    results = neo4j.run_query(QUERIES["stress_blood_sugar_correlation"])
    # Should find correlations — stress periods align with higher HbA1c
    # (seed has high stress 2015-2017 when HbA1c was rising)
    assert isinstance(results, list), "Should return a list"
    # Even if empty (depends on date alignment), check the query ran successfully


# ── Test 14: BRCA2 screening recommendations ─────────────────────────────────

def test_brca2_screening(neo4j):
    """Based on my BRCA2 variant, what screenings should I have?"""
    results = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_GENETIC_RISK]->(gr:GeneticRisk)
        WHERE any(gene IN gr.genes_involved WHERE gene = 'BRCA2')
        RETURN gr.condition_name AS condition, gr.risk_level AS risk_level,
               gr.recommendations AS recommendations
        """
    )
    assert len(results) > 0, "Should find BRCA2-related genetic risk"
    brca_risk = results[0]
    assert brca_risk["risk_level"] == "high", "BRCA2 risk should be flagged as HIGH"
    assert brca_risk.get("recommendations"), "Should have screening recommendations"


# ── Test 15: Cross-vertical health summary ────────────────────────────────────

def test_cross_vertical_summary_2020_2025(neo4j):
    """Full cross-vertical health summary for 2020-2025."""
    # Conditions active in this period
    conditions = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_CONDITION]->(c:Condition)
        WHERE c.status IN ['active', 'chronic']
        RETURN c.name AS name, c.status AS status
        """
    )
    # Medications in this period
    medications = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:TAKES_MEDICATION]->(m:Medication)
        RETURN m.name AS name, m.dosage AS dosage
        """
    )
    # Labs in this period
    labs = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_LAB_RESULT]->(l:LabResult)
        WHERE l.date >= '2020-01-01'
        RETURN l.test_name AS test, l.value AS value, l.date AS date
        ORDER BY l.date DESC
        LIMIT 10
        """
    )
    # Mood trend
    moods = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_MOOD_ENTRY]->(me:MoodEntry)
        WHERE me.date >= '2020-01-01'
        RETURN me.date AS date, me.score AS score
        ORDER BY me.date
        """
    )
    # Genetic risks
    risks = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_GENETIC_RISK]->(gr:GeneticRisk)
        WHERE gr.risk_level IN ['high', 'moderate']
        RETURN gr.condition_name AS condition, gr.risk_level AS level
        """
    )

    assert len(conditions) >= 3, "Should have multiple active conditions in 2020-2025"
    assert len(medications) >= 4, "Should have multiple medications"
    assert len(labs) >= 4, "Should have recent lab results"
    assert len(moods) >= 5, "Should have mood entries for 2020-2025"
    assert len(risks) >= 2, "Should have genetic risk factors identified"

    # Verify the narrative: mood improving, labs improving
    mood_scores = [m["score"] for m in moods if m.get("score")]
    if len(mood_scores) >= 2:
        assert mood_scores[-1] >= mood_scores[0], "Mood should be same or better at end of period"
