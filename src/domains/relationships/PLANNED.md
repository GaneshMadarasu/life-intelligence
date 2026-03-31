# Relationships Domain — Planned Implementation

## What this domain will do
Track family health history and professional network connections to inform genetic risk assessment and career intelligence — especially useful when cross-referenced with genetics and healthcare data.

## Verticals
- **family**: Family members, their health histories, genetic connections
- **professional**: Professional contacts, mentors, references, collaboration history

## Planned Node Types
- `FamilyMember` {name, relation: parent|sibling|grandparent|child|aunt|uncle|cousin, dob, sex, is_alive: bool}
- `FamilyHealthHistory` {condition, family_member, onset_age, severity, cause_of_death}
- `Contact` {name, relation_type: mentor|colleague|client|collaborator, company, met_date, last_contact}

## Planned Relationships
- (Person)-[:HAS_FAMILY_MEMBER]->(FamilyMember)
- (FamilyMember)-[:HAS_CONDITION]->(Condition)
- (FamilyHealthHistory)-[:INCREASES_RISK]->(GeneticRisk)
- (Person)-[:HAS_CONTACT]->(Contact)

## Cross-Domain Connections
### relationships ↔ healthcare (genetics)
- `(FamilyMember)-[:HAS_CONDITION]->(Condition)` — family conditions inform genetic risk
- `(FamilyHealthHistory)-[:INCREASES_RISK]->(GeneticRisk)` — family history + genetic variant = compound risk
- Query: "Given my family history of breast cancer and my BRCA2 variant, what is my actual risk?"

### relationships ↔ career
- `(Contact)-[:WORKS_AT]->(Organisation)` — professional network intelligence

## Data Sources Accepted
- Family health history forms (PDF, JSON)
- 23andMe/AncestryDNA family relative exports
- Manual input via API (JSON)
- Medical intake forms with family history sections

## Example Queries This Will Answer
- "Based on my family history, what conditions am I at elevated risk for?"
- "Which of my genetic risks are also supported by family history?"
- "My father had a heart attack at 55 — how does that affect my cardiovascular risk?"
- "What conditions run in both sides of my family?"

## Implementation Steps (when ready)
1. Create `src/domains/relationships/verticals/family/` — full implementation
2. Create `src/domains/relationships/verticals/professional/` — full implementation
3. Update cross-domain linker to link FamilyHealthHistory → GeneticRisk
4. Add family history endpoints to `src/api/main.py`
