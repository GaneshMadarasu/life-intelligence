# Finances Domain — Planned Implementation

## What this domain will do
Track banking, investments, insurance policies, and tax records to answer financial intelligence questions — and crucially, cross-reference them with your healthcare and legal data.

## Verticals
- **banking**: Bank accounts, transactions, balances, spending categories
- **investments**: Stocks, ETFs, retirement accounts (401k, IRA), crypto
- **insurance**: Health, life, home, auto insurance policies and claims
- **taxes**: Tax returns, deductions, income records, medical expense tracking

## Planned Node Types
- `BankAccount` {type, institution, balance_snapshot, date}
- `Transaction` {amount, category, merchant, date, type: debit|credit}
- `Investment` {type, symbol, value, purchase_date, current_value}
- `InsurancePlan` {type: health|life|home|auto, provider, premium, deductible, coverage_start, coverage_end}
- `TaxReturn` {year, income, deductions, refund_amount, filing_status}
- `Expense` {category, amount, date, is_medical: bool, is_deductible: bool}
- `Benefit` {type: FSA|HSA|401k|IRA, balance, year, contribution_limit}

## Planned Relationships
- (Person)-[:HAS_ACCOUNT]->(BankAccount)
- (Person)-[:HAS_INSURANCE]->(InsurancePlan)
- (Person)-[:HAS_BENEFIT]->(Benefit)
- (BankAccount)-[:HAS_TRANSACTION]->(Transaction)
- (InsurancePlan)-[:COVERS]->(Condition)
- (Benefit {type:HSA})-[:FUNDS]->(Medication)
- (InsurancePlan)-[:PAYS_CLAIM_FOR]->(Hospitalization)

## Cross-Domain Connections
### finances ↔ healthcare
- `(InsurancePlan)-[:COVERS]->(Condition)` — does your insurance cover your diagnosis?
- `(Expense {is_medical: true})-[:RELATED_TO]->(Procedure|Medication)` — document medical expenses
- `(Benefit {type: HSA|FSA})-[:FUNDS]->(Medication|Procedure)` — HSA/FSA coverage
- `(InsurancePlan)-[:PAYS_CLAIM_FOR]->(Hospitalization)` — claim tracking

### finances ↔ legal-contracts
- `(Contract)-[:SPECIFIES_COMPENSATION]->(Transaction)` — salary from employment contract
- `(Obligation)-[:TRIGGERS]->(Expense)` — contractual obligations as expenses

## Data Sources Accepted
- Bank statement PDFs and CSVs (Chase, BofA, Wells Fargo formats)
- Investment account exports (Fidelity, Vanguard, Schwab CSV/JSON)
- Insurance policy PDFs
- Tax return PDFs (TurboTax, H&R Block, FreeTaxUSA exports)
- Mint, YNAB, Personal Capital data exports
- EOB (Explanation of Benefits) documents from insurers

## Example Queries This Will Answer
- "Am I maximizing my HSA contributions given my medical expenses?"
- "What medical expenses can I claim as tax deductions this year?"
- "Does my health insurance cover my diabetes medication?"
- "How much have I spent on healthcare vs my annual deductible?"
- "What is my net worth trend over the last 5 years?"
- "Given my diabetes diagnosis, am I getting the maximum FSA reimbursement?"
- "Which insurance plan covers my BRCA2 screening needs?"

## Implementation Steps (when ready)
1. Create `src/domains/finances/verticals/banking/` — full implementation
2. Create `src/domains/finances/verticals/investments/` — full implementation
3. Create `src/domains/finances/verticals/insurance/` — full implementation
4. Create `src/domains/finances/verticals/taxes/` — full implementation
5. Update `src/core/cross_domain_linker.py` Rule 1 and Rule 3
6. Add active endpoints to `src/api/main.py`
7. Add finance seed data to `scripts/seed_data/`
8. Add finance tests to `tests/`
