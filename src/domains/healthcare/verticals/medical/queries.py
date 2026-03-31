"""Cypher query templates for the medical vertical."""

QUERIES = {
    "current_medications": """
        MATCH (p:Person {id: 'primary'})-[:TAKES_MEDICATION]->(m:Medication)
        WHERE m.end_date IS NULL OR m.end_date > toString(date())
        RETURN m.name AS name, m.dosage AS dosage,
               m.frequency AS frequency, m.indication AS indication,
               m.prescribed_date AS prescribed_date
        ORDER BY m.name
    """,
    "active_conditions": """
        MATCH (p:Person {id: 'primary'})-[:HAS_CONDITION]->(c:Condition)
        WHERE c.status IN ['active', 'chronic']
        RETURN c.name AS name, c.status AS status,
               c.diagnosed_date AS diagnosed_date, c.severity AS severity,
               c.icd_code AS icd_code
        ORDER BY c.diagnosed_date
    """,
    "drug_interactions": """
        MATCH (p:Person {id: 'primary'})-[:TAKES_MEDICATION]->(m1:Medication)
        MATCH (p)-[:TAKES_MEDICATION]->(m2:Medication)
        MATCH (m1)-[r:INTERACTS_WITH]->(m2)
        WHERE m1.name < m2.name
        RETURN m1.name AS drug1, m2.name AS drug2,
               coalesce(r.severity, 'unknown') AS severity,
               coalesce(r.description, 'Known interaction') AS description
    """,
    "lab_trends": """
        MATCH (p:Person {id: 'primary'})-[:HAS_LAB_RESULT]->(l:LabResult)
        WHERE l.test_name = $test_name
        RETURN l.value AS value, l.unit AS unit,
               l.date AS date, l.is_abnormal AS is_abnormal,
               l.reference_range AS reference_range
        ORDER BY l.date
    """,
    "abnormal_labs": """
        MATCH (p:Person {id: 'primary'})-[:HAS_LAB_RESULT]->(l:LabResult)
        WHERE l.is_abnormal = true
        RETURN l.test_name AS test_name, l.value AS value,
               l.unit AS unit, l.date AS date
        ORDER BY l.date DESC
        LIMIT 20
    """,
    "medical_timeline": """
        MATCH (p:Person {id: 'primary'})-[:HAS_DOCUMENT]->(d:Document)-[:OCCURRED_AT]->(t:TimePoint)
        WHERE d.vertical = 'medical'
        AND ($date_from IS NULL OR t.date >= date($date_from))
        AND ($date_to IS NULL OR t.date <= date($date_to))
        RETURN d.title AS title, d.doc_type AS doc_type,
               toString(t.date) AS date
        ORDER BY t.date
    """,
    "conditions_with_medications": """
        MATCH (p:Person {id: 'primary'})-[:HAS_CONDITION]->(c:Condition)
        OPTIONAL MATCH (c)-[:TREATED_BY]->(m:Medication)
        RETURN c.name AS condition, collect(m.name) AS medications,
               c.status AS status
        ORDER BY c.name
    """,
    "provider_history": """
        MATCH (p:Person {id: 'primary'})-[:SAW_PROVIDER]->(pr:Provider)
        RETURN pr.name AS name, pr.specialty AS specialty,
               pr.institution AS institution
        ORDER BY pr.name
    """,
    "vaccine_history": """
        MATCH (p:Person {id: 'primary'})-[:RECEIVED_VACCINE]->(v:Vaccine)
        RETURN v.name AS name, v.date AS date, v.provider AS provider
        ORDER BY v.date
    """,
    "hospitalization_history": """
        MATCH (p:Person {id: 'primary'})-[:HAD_HOSPITALIZATION]->(h:Hospitalization)
        RETURN h.reason AS reason, h.admit_date AS admit_date,
               h.discharge_date AS discharge_date, h.facility AS facility
        ORDER BY h.admit_date DESC
    """,
    "supplement_interactions": """
        MATCH (p:Person {id: 'primary'})-[:TAKES_SUPPLEMENT]->(s:Supplement)
        MATCH (p)-[:TAKES_MEDICATION]->(m:Medication)
        MATCH (s)-[r:INTERACTS_WITH]->(m)
        RETURN s.name AS supplement, m.name AS medication,
               r.severity AS severity, r.description AS description
    """,
    "allergy_list": """
        MATCH (p:Person {id: 'primary'})-[:HAS_ALLERGY]->(a:Allergy)
        RETURN a.allergen AS allergen, a.reaction AS reaction,
               a.severity AS severity, a.discovered_date AS discovered_date
        ORDER BY a.severity DESC
    """,
}
