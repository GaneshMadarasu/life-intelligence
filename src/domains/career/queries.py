"""Cypher query templates for the career domain."""

QUERIES = {
    "employment_history": """
        MATCH (p:Person {id: 'primary'})-[:HAS_JOB]->(j:Job)
        RETURN j.title AS title, j.company AS company, j.location AS location,
               j.start_date AS start_date, j.end_date AS end_date,
               j.employment_type AS employment_type, j.is_current AS is_current,
               j.salary AS salary
        ORDER BY j.start_date DESC
    """,
    "current_job": """
        MATCH (p:Person {id: 'primary'})-[:HAS_JOB]->(j:Job)
        WHERE j.is_current = true OR j.end_date IS NULL OR j.end_date = ''
        RETURN j.title AS title, j.company AS company, j.location AS location,
               j.start_date AS start_date, j.description AS description,
               j.salary AS salary
        ORDER BY j.start_date DESC
        LIMIT 1
    """,
    "all_skills": """
        MATCH (p:Person {id: 'primary'})-[:HAS_SKILL]->(s:Skill)
        RETURN s.name AS name, s.category AS category, s.proficiency AS proficiency,
               s.years_experience AS years_experience
        ORDER BY s.category, s.proficiency DESC
    """,
    "technical_skills": """
        MATCH (p:Person {id: 'primary'})-[:HAS_SKILL]->(s:Skill)
        WHERE s.category IN ['technical', 'tool', 'framework', 'language']
        RETURN s.name AS name, s.category AS category, s.proficiency AS proficiency,
               s.years_experience AS years_experience
        ORDER BY s.proficiency DESC, s.name
    """,
    "education_history": """
        MATCH (p:Person {id: 'primary'})-[:HAS_EDUCATION]->(e:Education)
        RETURN e.institution AS institution, e.degree AS degree,
               e.field_of_study AS field_of_study, e.start_date AS start_date,
               e.end_date AS end_date, e.gpa AS gpa, e.honors AS honors
        ORDER BY e.end_date DESC
    """,
    "certifications": """
        MATCH (p:Person {id: 'primary'})-[:HAS_CERTIFICATION]->(c:Certification)
        RETURN c.name AS name, c.issuer AS issuer, c.issued_date AS issued_date,
               c.expiry_date AS expiry_date, c.credential_id AS credential_id
        ORDER BY c.issued_date DESC
    """,
    "expiring_certifications": """
        MATCH (p:Person {id: 'primary'})-[:HAS_CERTIFICATION]->(c:Certification)
        WHERE c.expiry_date <> '' AND c.expiry_date <= $cutoff
        RETURN c.name AS name, c.issuer AS issuer, c.expiry_date AS expiry_date
        ORDER BY c.expiry_date
    """,
    "achievements": """
        MATCH (p:Person {id: 'primary'})-[:HAS_ACHIEVEMENT]->(a:Achievement)
        RETURN a.title AS title, a.description AS description,
               a.date AS date, a.context AS context
        ORDER BY a.date DESC
    """,
    "projects": """
        MATCH (p:Person {id: 'primary'})-[:HAS_PROJECT]->(pr:Project)
        RETURN pr.name AS name, pr.description AS description, pr.role AS role,
               pr.start_date AS start_date, pr.end_date AS end_date,
               pr.technologies AS technologies, pr.url AS url
        ORDER BY pr.start_date DESC
    """,
    "career_summary": """
        MATCH (p:Person {id: 'primary'})
        OPTIONAL MATCH (p)-[:HAS_JOB]->(j:Job)
        OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)
        OPTIONAL MATCH (p)-[:HAS_EDUCATION]->(e:Education)
        OPTIONAL MATCH (p)-[:HAS_CERTIFICATION]->(c:Certification)
        RETURN count(DISTINCT j) AS total_jobs, count(DISTINCT s) AS total_skills,
               count(DISTINCT e) AS total_education, count(DISTINCT c) AS total_certifications
    """,
}
