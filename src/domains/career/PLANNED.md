# Career Domain — Planned Implementation

## What this domain will do
Track employment history, skills, certifications, and performance reviews to answer career intelligence questions and detect correlations with health and financial outcomes.

## Verticals
- **employment-history**: Jobs, roles, companies, tenures, salaries, locations
- **skills**: Technical and soft skills, proficiency levels, last used dates
- **education**: Degrees, courses, certifications, training programs

## Planned Node Types
- `Job` {title, company, start_date, end_date, salary, location, type: full-time|part-time|contract}
- `PerformanceReview` {date, score, reviewer, key_feedback, got_promotion: bool}
- `Skill` {name, category: technical|soft|domain, proficiency: beginner|intermediate|expert, last_used}
- `Certification` {name, issuer, issue_date, expiry_date, credential_id}
- `Education` {institution, degree, field, start_date, end_date, gpa}

## Planned Relationships
- (Person)-[:HAS_JOB]->(Job)
- (Person)-[:HAS_REVIEW]->(PerformanceReview)
- (Person)-[:HAS_SKILL]->(Skill)
- (Person)-[:HAS_CERTIFICATION]->(Certification)
- (Person)-[:HAS_EDUCATION]->(Education)
- (Job)-[:REQUIRES]->(Skill)

## Cross-Domain Connections
### career ↔ healthcare (mental health)
- `(Stressor {category: work})-[:CORRELATES_WITH]->(PerformanceReview)` — burnout detection by TimePoint
- `(MoodEntry)-[:CORRELATES_WITH]->(PerformanceReview)` — mood vs performance correlation

### career ↔ finances
- `(Job)-[:GENERATES]->(Transaction {type: income})` — salary income tracking
- `(Certification)-[:QUALIFIES_FOR]->(Job)` — career progression

## Data Sources Accepted
- Resume PDFs and DOCX
- LinkedIn data export (JSON)
- Performance review documents (PDF, DOCX)
- Certification PDFs (AWS, Google, Microsoft, etc.)
- Diploma and transcript PDFs
- GitHub/portfolio links (future)

## Example Queries This Will Answer
- "Has my work stress correlated with health issues over the last 5 years?"
- "What certifications are expiring in the next 6 months?"
- "How has my salary grown over my career?"
- "What skills should I develop based on my career trajectory?"
- "Was there a health decline during my most stressful job period?"

## Implementation Steps (when ready)
1. Create `src/domains/career/verticals/employment-history/` — full implementation
2. Create `src/domains/career/verticals/skills/` — full implementation
3. Create `src/domains/career/verticals/education/` — full implementation
4. Update `src/core/cross_domain_linker.py` Rule 4 (stress ↔ performance)
5. Add active endpoints to `src/api/main.py`
6. Add career seed data to `scripts/seed_data/`
