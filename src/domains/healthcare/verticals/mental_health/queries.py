"""Cypher query templates for the mental health vertical."""

QUERIES = {
    "mood_trends": """
        MATCH (p:Person {id: 'primary'})-[:HAS_MOOD_ENTRY]->(me:MoodEntry)
        WHERE ($date_from IS NULL OR me.date >= $date_from)
        AND ($date_to IS NULL OR me.date <= $date_to)
        RETURN me.date AS date, me.score AS score,
               me.anxiety_level AS anxiety_level,
               me.energy_level AS energy_level, me.triggers AS triggers
        ORDER BY me.date
    """,
    "therapy_history": """
        MATCH (p:Person {id: 'primary'})-[:HAD_THERAPY]->(ts:TherapySession)
        RETURN ts.date AS date, ts.therapist AS therapist,
               ts.type AS type, ts.mood_at_session AS mood_at_session
        ORDER BY ts.date DESC
    """,
    "active_stressors": """
        MATCH (p:Person {id: 'primary'})-[:HAS_STRESSOR]->(s:Stressor)
        WHERE s.resolved_date IS NULL OR s.resolved_date = ''
        RETURN s.description AS description, s.category AS category,
               s.intensity AS intensity, s.start_date AS start_date
        ORDER BY s.intensity DESC
    """,
    "mental_conditions": """
        MATCH (p:Person {id: 'primary'})-[:HAS_MENTAL_CONDITION]->(mc:MentalCondition)
        RETURN mc.name AS name, mc.status AS status,
               mc.diagnosed_date AS diagnosed_date,
               mc.treating_provider AS treating_provider
        ORDER BY mc.diagnosed_date
    """,
    "meditation_stats": """
        MATCH (p:Person {id: 'primary'})-[:HAS_MEDITATION]->(ms:MeditationSession)
        WHERE ms.date >= $date_from
        RETURN count(ms) AS session_count,
               sum(ms.duration_mins) AS total_minutes,
               avg(ms.duration_mins) AS avg_duration
    """,
    "journal_sentiment_trend": """
        MATCH (p:Person {id: 'primary'})-[:HAS_JOURNAL]->(je:JournalEntry)
        WHERE ($date_from IS NULL OR je.date >= $date_from)
        RETURN je.date AS date, je.sentiment AS sentiment,
               je.key_themes AS key_themes
        ORDER BY je.date
    """,
    "stress_blood_sugar_correlation": """
        MATCH (p:Person {id: 'primary'})-[:HAS_STRESSOR]->(s:Stressor)
        MATCH (p)-[:HAS_LAB_RESULT]->(l:LabResult {test_name: 'HbA1c'})
        WHERE s.start_date IS NOT NULL AND l.date IS NOT NULL
        AND abs(duration.inDays(date(s.start_date), date(l.date)).days) <= 90
        RETURN s.description AS stressor, s.intensity AS stress_intensity,
               l.value AS hba1c, l.date AS lab_date, s.start_date AS stress_date
        ORDER BY l.date
    """,
}
