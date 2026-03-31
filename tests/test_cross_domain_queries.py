"""
Cross-domain query tests — skipped until planned domains are implemented.
Each test is marked with @pytest.mark.skip and documents what it will verify.
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


@pytest.mark.skip(
    reason="Requires finances domain — see src/domains/finances/PLANNED.md"
)
def test_diabetes_hsa_maximization(neo4j):
    """
    Query: Given my diabetes and insurance, am I maximizing HSA benefits?

    What it will test:
    - Finds InsurancePlan nodes (finances domain)
    - Finds Benefit {type: HSA} nodes (finances domain)
    - Links to Condition {name: Type 2 Diabetes} (healthcare domain)
    - Finds Medication (Metformin) that should be HSA-eligible
    - Finds Expense nodes with is_medical=true (finances domain)
    - Asserts: HSA balance + eligible expenses are correctly linked
    """
    results = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_CONDITION]->(c:Condition)
        WHERE c.name = 'Type 2 Diabetes'
        MATCH (p)-[:HAS_BENEFIT]->(b:Benefit {type: 'HSA'})
        MATCH (p)-[:TAKES_MEDICATION]->(m:Medication)
        WHERE (c)-[:TREATED_BY]->(m)
        OPTIONAL MATCH (b)-[:FUNDS]->(m)
        RETURN c.name AS condition, b.balance AS hsa_balance,
               m.name AS medication, b.year AS year
        """
    )
    assert len(results) > 0, "Should find diabetes + HSA + medication cross-domain link"
    for r in results:
        assert r["hsa_balance"] is not None, "HSA balance should be tracked"


@pytest.mark.skip(
    reason="Requires finances domain (insurance vertical) — see src/domains/finances/PLANNED.md"
)
def test_life_insurance_brca2(neo4j):
    """
    Query: Does my life insurance account for my BRCA2 risk?

    What it will test:
    - Finds InsurancePlan {type: life} (finances domain)
    - Finds GeneticRisk {condition: cancer, genes_involved: [BRCA2]} (healthcare)
    - Checks (InsurancePlan)-[:RELEVANT_TO]->(GeneticRisk) link exists
    - Asserts: life insurance coverage adequacy relative to elevated risk
    """
    results = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_GENETIC_RISK]->(gr:GeneticRisk)
        WHERE any(gene IN gr.genes_involved WHERE gene = 'BRCA2')
        MATCH (p)-[:HAS_INSURANCE]->(ip:InsurancePlan {type: 'life'})
        RETURN gr.condition_name AS genetic_risk, gr.risk_level AS risk_level,
               ip.provider AS insurer, ip.coverage_start AS coverage_start
        """
    )
    assert len(results) > 0, "Should find BRCA2 risk linked to life insurance"


@pytest.mark.skip(
    reason="Requires both finances and legal-contracts domains — see PLANNED.md files"
)
def test_medical_expenses_employment_benefits(neo4j):
    """
    Query: What medical expenses can I claim given my employment benefits?

    What it will test:
    - Finds Contract {type: employment} (legal domain)
    - Finds Benefit {type: FSA|HSA} linked to Contract (legal + finances)
    - Finds Expense {is_medical: true} (finances domain)
    - Matches expenses to eligible benefit categories
    - Asserts: total claimable amount is calculated
    """
    results = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_CONTRACT]->(c:Contract {type: 'employment'})
        MATCH (c)-[:INCLUDES_BENEFIT]->(b:Benefit)
        WHERE b.type IN ['FSA', 'HSA']
        MATCH (p)-[:HAS_EXPENSE]->(e:Expense {is_medical: true})
        RETURN c.parties AS employer, b.type AS benefit_type,
               b.balance AS available_balance,
               sum(e.amount) AS total_medical_expenses
        """
    )
    assert len(results) > 0, "Should find employment benefits covering medical expenses"


@pytest.mark.skip(
    reason="Requires finances domain (insurance vertical) — see src/domains/finances/PLANNED.md"
)
def test_sertraline_insurance_coverage(neo4j):
    """
    Query: Is my Sertraline covered by my insurance plan?

    What it will test:
    - Finds Medication {name: Sertraline} (healthcare domain)
    - Finds InsurancePlan (finances domain)
    - Checks (InsurancePlan)-[:COVERS]->(Condition) where Condition is anxiety/depression
    - Verifies coverage through condition → medication treatment chain
    - Asserts: insurance covers anxiety disorder which is treated by Sertraline
    """
    results = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:TAKES_MEDICATION]->(m:Medication {name: 'Sertraline'})
        MATCH (c:Condition)-[:TREATED_BY]->(m)
        MATCH (p)-[:HAS_CONDITION]->(c)
        MATCH (p)-[:HAS_INSURANCE]->(ip:InsurancePlan)
        OPTIONAL MATCH (ip)-[:COVERS]->(c)
        RETURN m.name AS medication, c.name AS condition,
               ip.type AS insurance_type, ip.provider AS insurer
        """
    )
    assert len(results) > 0, "Should find Sertraline + insurance coverage chain"


@pytest.mark.skip(
    reason="Requires legal-contracts domain — see src/domains/legal-contracts/PLANNED.md"
)
def test_contract_obligations_health_coverage(neo4j):
    """
    Query: What are all my upcoming contract obligations that affect my health coverage?

    What it will test:
    - Finds Obligation nodes with upcoming due_date (legal domain)
    - Finds InsurancePlan linked to employment Contract (legal + finances)
    - Flags obligations whose resolution could affect healthcare benefits
    - Asserts: obligations are returned with their health coverage impact

    Real example: If employment contract renewal has a 30-day window and
    health insurance is tied to employment, this query surfaces that risk.
    """
    results = neo4j.run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_CONTRACT]->(c:Contract)
        MATCH (c)-[:HAS_OBLIGATION]->(o:Obligation)
        WHERE o.due_date >= toString(date()) AND o.status = 'pending'
        OPTIONAL MATCH (c)-[:INCLUDES_BENEFIT]->(b:Benefit)
        OPTIONAL MATCH (ip:InsurancePlan)-[:COVERS]->(cond:Condition)
        WHERE EXISTS((p)-[:HAS_CONDITION]->(cond))
        RETURN o.description AS obligation, o.due_date AS due_date,
               collect(b.type) AS benefits_at_risk,
               collect(cond.name) AS conditions_covered
        ORDER BY o.due_date
        """
    )
    assert len(results) >= 0, "Query should execute without error"
    # When implemented: assert pending obligations affecting coverage are surfaced
