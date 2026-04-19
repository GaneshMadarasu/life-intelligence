"""Cypher query templates for the finances domain."""

QUERIES = {
    "all_accounts": """
        MATCH (p:Person {id: 'primary'})-[:HAS_ACCOUNT]->(a:FinancialAccount)
        RETURN a.name AS name, a.type AS type, a.institution AS institution,
               a.balance AS balance, a.currency AS currency, a.status AS status
        ORDER BY a.type, a.name
    """,
    "net_worth": """
        MATCH (p:Person {id: 'primary'})
        OPTIONAL MATCH (p)-[:HAS_ACCOUNT]->(a:FinancialAccount WHERE a.status = 'active')
        OPTIONAL MATCH (p)-[:HAS_INVESTMENT]->(i:Investment)
        OPTIONAL MATCH (p)-[:HAS_DEBT]->(d:Debt)
        WITH
          coalesce(sum(a.balance), 0) AS account_total,
          coalesce(sum(i.total_value), 0) AS investment_total,
          coalesce(sum(d.balance), 0) AS debt_total
        RETURN account_total, investment_total, debt_total,
               (account_total + investment_total - debt_total) AS net_worth
    """,
    "all_investments": """
        MATCH (p:Person {id: 'primary'})-[:HAS_INVESTMENT]->(i:Investment)
        RETURN i.symbol AS symbol, i.name AS name, i.asset_type AS asset_type,
               i.quantity AS quantity, i.price_per_unit AS price,
               i.total_value AS total_value, i.account AS account
        ORDER BY i.total_value DESC
    """,
    "insurance_plans": """
        MATCH (p:Person {id: 'primary'})-[:HAS_INSURANCE]->(i:InsurancePlan)
        RETURN i.plan_name AS plan_name, i.insurer AS insurer, i.type AS type,
               i.premium_monthly AS premium_monthly, i.deductible AS deductible,
               i.coverage_limit AS coverage_limit, i.end_date AS end_date
        ORDER BY i.type
    """,
    "recent_transactions": """
        MATCH (p:Person {id: 'primary'})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.date >= $cutoff
        RETURN t.description AS description, t.amount AS amount, t.type AS type,
               t.category AS category, t.date AS date, t.merchant AS merchant
        ORDER BY t.date DESC
        LIMIT 50
    """,
    "spending_by_category": """
        MATCH (p:Person {id: 'primary'})-[:HAS_TRANSACTION]->(t:Transaction)
        WHERE t.type = 'debit' AND t.date >= $cutoff
        RETURN t.category AS category, sum(t.amount) AS total, count(t) AS count
        ORDER BY total DESC
    """,
    "all_debts": """
        MATCH (p:Person {id: 'primary'})-[:HAS_DEBT]->(d:Debt)
        RETURN d.name AS name, d.type AS type, d.balance AS balance,
               d.interest_rate AS interest_rate, d.minimum_payment AS minimum_payment
        ORDER BY d.balance DESC
    """,
    "tax_history": """
        MATCH (p:Person {id: 'primary'})-[:HAS_TAX_ITEM]->(t:TaxItem)
        RETURN t.year AS year, t.type AS type, t.amount AS amount,
               t.description AS description, t.issuer AS issuer
        ORDER BY t.year DESC, t.type
    """,
    "health_insurance_cross": """
        MATCH (p:Person {id: 'primary'})-[:HAS_INSURANCE]->(i:InsurancePlan)
        WHERE i.type = 'health'
        OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c:Condition WHERE c.status IN ['active','chronic'])
        RETURN i.plan_name AS plan, i.insurer AS insurer,
               i.deductible AS deductible, collect(c.name) AS active_conditions
    """,
}
