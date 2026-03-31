# Legal Contracts Domain — Planned Implementation

## What this domain will do
Parse and track employment contracts, property agreements, and insurance policies to surface obligations, rights, deadlines, and benefits — and cross-reference them with your healthcare and financial data.

## Verticals
- **employment**: Employment contracts, offer letters, NDAs, non-competes, equity agreements
- **property**: Lease agreements, mortgage documents, property deeds, HOA agreements
- **insurance-policies**: Policy documents for all insurance types (health, life, home, auto)

## Planned Node Types
- `Contract` {type: employment|property|insurance|service, parties: list, start_date, end_date, status: active|expired|terminated}
- `Clause` {text, category: compensation|benefits|termination|IP|confidentiality|disability, obligations, rights}
- `Obligation` {description, due_date, party_responsible, status: pending|fulfilled|overdue}
- `Benefit` {description, type: health|dental|vision|FSA|HSA|401k|PTO|equity, value, conditions}
- `Deadline` {description, date, contract_id, status: upcoming|overdue|met}

## Planned Relationships
- (Person)-[:HAS_CONTRACT]->(Contract)
- (Contract)-[:HAS_CLAUSE]->(Clause)
- (Contract)-[:HAS_OBLIGATION]->(Obligation)
- (Contract)-[:INCLUDES_BENEFIT]->(Benefit)
- (Contract)-[:HAS_DEADLINE]->(Deadline)

## Cross-Domain Connections
### legal ↔ healthcare
- `(Contract {type: employment})-[:INCLUDES_BENEFIT]->(InsurancePlan)` — employer health coverage
- `(Clause {category: disability})-[:RELATES_TO]->(Condition)` — does your disability clause cover your diagnosis?
- `(Contract)-[:INCLUDES_BENEFIT]->(Benefit {type: FSA|HSA})` — employer FSA/HSA

### legal ↔ finances
- `(Contract)-[:SPECIFIES_COMPENSATION]->(Transaction {type: income})` — salary tracking
- `(Obligation)-[:TRIGGERS]->(Expense)` — obligations that create financial obligations
- `(Benefit)-[:MAPS_TO]->(Benefit in finances domain)` — contract benefit → financial benefit

## Data Sources Accepted
- Employment contract PDFs
- Lease agreement PDFs
- Insurance policy documents (PDF, DOCX)
- Employment offer letters
- NDA and non-compete agreements
- Equity/stock option agreements

## Example Queries This Will Answer
- "What are my upcoming contract obligations in the next 30 days?"
- "Does my employment contract include HSA or FSA benefits?"
- "When does my non-compete clause expire?"
- "What insurance benefits am I entitled to under my employment contract?"
- "Does my disability clause cover my diagnosed chronic condition?"
- "What is my total equity vesting schedule?"

## Implementation Steps (when ready)
1. Create `src/domains/legal-contracts/verticals/employment/` — full implementation
2. Create `src/domains/legal-contracts/verticals/property/` — full implementation
3. Create `src/domains/legal-contracts/verticals/insurance-policies/` — full implementation
4. Update `src/core/cross_domain_linker.py` Rule 2
5. Add active endpoints to `src/api/main.py`
6. Add legal seed data to `scripts/seed_data/`
7. Add legal tests to `tests/`
