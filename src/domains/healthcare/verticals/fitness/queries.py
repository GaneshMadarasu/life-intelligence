"""Cypher query templates for the fitness vertical."""

QUERIES = {
    "current_supplements": """
        MATCH (p:Person {id: 'primary'})-[:TAKES_SUPPLEMENT]->(s:Supplement)
        RETURN s.name AS name, s.dosage AS dosage,
               s.frequency AS frequency, s.purpose AS purpose, s.brand AS brand
        ORDER BY s.name
    """,
    "workout_history": """
        MATCH (p:Person {id: 'primary'})-[:HAS_WORKOUT]->(w:Workout)
        WHERE ($date_from IS NULL OR w.date >= $date_from)
        AND ($date_to IS NULL OR w.date <= $date_to)
        RETURN w.type AS type, w.date AS date, w.duration_mins AS duration_mins,
               w.intensity AS intensity, w.calories_burned AS calories_burned
        ORDER BY w.date DESC
    """,
    "body_metric_trends": """
        MATCH (p:Person {id: 'primary'})-[:HAS_BODY_METRIC]->(bm:BodyMetric)
        WHERE bm.type = $metric_type
        RETURN bm.value AS value, bm.unit AS unit, bm.date AS date
        ORDER BY bm.date
    """,
    "sleep_trends": """
        MATCH (p:Person {id: 'primary'})-[:HAS_SLEEP_RECORD]->(sr:SleepRecord)
        RETURN sr.date AS date, sr.duration_hours AS duration_hours,
               sr.quality AS quality, sr.deep_sleep_hours AS deep_sleep_hours
        ORDER BY sr.date
    """,
    "nutrition_summary": """
        MATCH (p:Person {id: 'primary'})-[:ATE]->(m:Meal)
        WHERE m.date >= $date_from AND m.date <= $date_to
        RETURN m.date AS date,
               sum(m.calories) AS total_calories,
               sum(m.protein_g) AS total_protein,
               sum(m.carbs_g) AS total_carbs,
               sum(m.fat_g) AS total_fat
        ORDER BY m.date
    """,
    "fitness_goals": """
        MATCH (p:Person {id: 'primary'})-[:HAS_FITNESS_GOAL]->(g:FitnessGoal)
        RETURN g.description AS description, g.status AS status,
               g.target_date AS target_date, g.target_value AS target_value,
               g.metric AS metric
        ORDER BY g.target_date
    """,
    "supplement_interaction_check": """
        MATCH (p:Person {id: 'primary'})-[:TAKES_SUPPLEMENT]->(s:Supplement)
        OPTIONAL MATCH (s)-[r:INTERACTS_WITH]->(m:Medication)
        WHERE EXISTS((p)-[:TAKES_MEDICATION]->(m))
        RETURN s.name AS supplement,
               collect({drug: m.name, severity: r.severity, desc: r.description}) AS interactions
    """,
}
