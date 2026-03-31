"""Cypher query templates for the genetics vertical."""

QUERIES = {
    "high_risks": """
        MATCH (p:Person {id: 'primary'})-[:HAS_GENETIC_RISK]->(gr:GeneticRisk)
        WHERE gr.risk_level = 'high'
        RETURN gr.condition_name AS condition, gr.risk_level AS risk_level,
               gr.genes_involved AS genes_involved,
               gr.recommendations AS recommendations
        ORDER BY gr.condition_name
    """,
    "all_genetic_risks": """
        MATCH (p:Person {id: 'primary'})-[:HAS_GENETIC_RISK]->(gr:GeneticRisk)
        RETURN gr.condition_name AS condition, gr.risk_level AS risk_level,
               gr.genes_involved AS genes_involved,
               gr.recommendations AS recommendations
        ORDER BY CASE gr.risk_level
            WHEN 'high' THEN 0
            WHEN 'moderate' THEN 1
            ELSE 2 END
    """,
    "pharmacogene_warnings": """
        MATCH (p:Person {id: 'primary'})-[:HAS_PHARMACOGENE]->(pg:Pharmacogene)
        WHERE pg.drug_metabolism IN ['poor', 'ultra_rapid']
        OPTIONAL MATCH (p)-[:TAKES_MEDICATION]->(m:Medication)
        WHERE any(drug IN pg.affected_drugs WHERE toLower(m.name) CONTAINS toLower(drug))
        RETURN pg.gene AS gene, pg.drug_metabolism AS metabolism,
               pg.affected_drugs AS affected_drugs,
               collect(m.name) AS current_medications_affected
    """,
    "ancestry": """
        MATCH (p:Person {id: 'primary'})-[:HAS_ANCESTRY]->(a:AncestrySegment)
        RETURN a.population AS population, a.percentage AS percentage,
               a.confidence AS confidence
        ORDER BY a.percentage DESC
    """,
    "all_variants": """
        MATCH (g:Gene)-[:HAS_VARIANT]->(gv:GeneticVariant)
        RETURN g.name AS gene, gv.rsid AS rsid, gv.genotype AS genotype,
               gv.variant_type AS variant_type, gv.significance AS significance
        ORDER BY CASE gv.significance
            WHEN 'pathogenic' THEN 0
            WHEN 'risk_factor' THEN 1
            WHEN 'uncertain' THEN 2
            ELSE 3 END
    """,
    "condition_relevant_genes": """
        MATCH (gr:GeneticRisk)-[:INVOLVES_GENE]->(g:Gene)
        MATCH (p:Person {id: 'primary'})-[:HAS_GENETIC_RISK]->(gr)
        RETURN gr.condition_name AS condition, gr.risk_level AS risk_level,
               collect(g.name) AS genes
        ORDER BY gr.risk_level
    """,
    "pharmacogene_medication_interactions": """
        MATCH (p:Person {id: 'primary'})-[:HAS_PHARMACOGENE]->(pg:Pharmacogene)
        OPTIONAL MATCH (pg)-[:AFFECTS_METABOLISM_OF]->(m:Medication)
        WHERE EXISTS((p)-[:TAKES_MEDICATION]->(m))
        RETURN pg.gene AS gene, pg.drug_metabolism AS metabolism,
               collect(m.name) AS current_drugs_affected
    """,
}
