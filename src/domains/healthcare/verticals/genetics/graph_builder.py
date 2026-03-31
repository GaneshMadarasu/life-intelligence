"""Genetics graph builder — creates Neo4j nodes from genetic report entities."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class GeneticsGraphBuilder:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def build(self, entities: dict[str, Any], file_path: str, metadata: dict) -> str:
        doc_id = f"gen_{hashlib.md5(f'{file_path}_{metadata.get(\"date\",\"\")}'.encode()).hexdigest()[:16]}"
        report = entities.get("genetic_report", {})
        self.neo4j.run_query(
            """
            MERGE (d:Document {id: $id})
            SET d.title = $title, d.domain = 'healthcare',
                d.vertical = 'genetics', d.source_file = $source_file,
                d.date = $date, d.doc_type = 'genetic_report'
            WITH d
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_DOCUMENT]->(d)
            """,
            {
                "id": doc_id,
                "title": file_path.split("/")[-1],
                "source_file": file_path,
                "date": report.get("report_date", ""),
            },
        )

        if report.get("provider"):
            self.neo4j.run_query(
                """
                MERGE (gr:GeneticReport {id: $id})
                SET gr.provider = $provider, gr.report_date = $date,
                    gr.test_type = $test_type
                WITH gr
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_GENETIC_REPORT]->(gr)
                """,
                {
                    "id": f"genreport_{doc_id}",
                    "provider": report.get("provider", ""),
                    "date": report.get("report_date", ""),
                    "test_type": report.get("test_type", ""),
                },
            )

        self._build_genes(entities.get("genes", []))
        self._build_genetic_variants(entities.get("genetic_variants", []))
        self._build_genetic_risks(entities.get("genetic_risks", []))
        self._build_pharmacogenes(entities.get("pharmacogenes", []))
        self._build_ancestry_segments(entities.get("ancestry_segments", []))
        return doc_id

    def _build_genes(self, genes: list[dict]) -> None:
        for g in genes:
            if not g.get("name"):
                continue
            self.neo4j.run_query(
                """
                MERGE (g:Gene {name: $name})
                SET g.chromosome = $chromosome, g.function = $function
                """,
                {
                    "name": g["name"],
                    "chromosome": g.get("chromosome", ""),
                    "function": g.get("function", ""),
                },
            )

    def _build_genetic_variants(self, variants: list[dict]) -> None:
        for v in variants:
            if not v.get("gene"):
                continue
            vid = f"var_{hashlib.md5(f'{v.get(\"rsid\",\"\")}_{v[\"gene\"]}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (gv:GeneticVariant {id: $id})
                SET gv.rsid = $rsid, gv.gene = $gene,
                    gv.variant_type = $variant_type,
                    gv.genotype = $genotype,
                    gv.significance = $significance
                WITH gv
                MATCH (g:Gene {name: $gene})
                MERGE (g)-[:HAS_VARIANT]->(gv)
                """,
                {
                    "id": vid,
                    "rsid": v.get("rsid", ""),
                    "gene": v["gene"],
                    "variant_type": v.get("variant_type", "SNP"),
                    "genotype": v.get("genotype", ""),
                    "significance": v.get("significance", "uncertain"),
                },
            )

    def _build_genetic_risks(self, risks: list[dict]) -> None:
        for r in risks:
            if not r.get("condition_name"):
                continue
            rid = f"grisk_{hashlib.md5(r['condition_name'].encode()).hexdigest()[:12]}"
            genes_involved = r.get("genes_involved", [])
            if isinstance(genes_involved, str):
                genes_involved = [genes_involved]
            self.neo4j.run_query(
                """
                MERGE (gr:GeneticRisk {id: $id})
                SET gr.condition_name = $condition_name,
                    gr.risk_level = $risk_level,
                    gr.genes_involved = $genes_involved,
                    gr.recommendations = $recommendations
                WITH gr
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_GENETIC_RISK]->(gr)
                """,
                {
                    "id": rid,
                    "condition_name": r["condition_name"],
                    "risk_level": r.get("risk_level", "low"),
                    "genes_involved": genes_involved,
                    "recommendations": r.get("recommendations", ""),
                },
            )
            # Link risk to its genes
            for gene_name in genes_involved:
                if gene_name:
                    self.neo4j.run_query(
                        """
                        MATCH (gr:GeneticRisk {id: $rid})
                        MERGE (g:Gene {name: $gene})
                        MERGE (gr)-[:INVOLVES_GENE]->(g)
                        """,
                        {"rid": rid, "gene": gene_name},
                    )

    def _build_pharmacogenes(self, pharmacogenes: list[dict]) -> None:
        for pg in pharmacogenes:
            if not pg.get("gene"):
                continue
            affected = pg.get("affected_drugs", [])
            if isinstance(affected, str):
                affected = [affected]
            self.neo4j.run_query(
                """
                MERGE (pg:Pharmacogene {gene: $gene})
                SET pg.drug_metabolism = $drug_metabolism,
                    pg.affected_drugs = $affected_drugs
                WITH pg
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_PHARMACOGENE]->(pg)
                """,
                {
                    "gene": pg["gene"],
                    "drug_metabolism": pg.get("drug_metabolism", "normal"),
                    "affected_drugs": affected,
                },
            )

    def _build_ancestry_segments(self, segments: list[dict]) -> None:
        for seg in segments:
            if not seg.get("population"):
                continue
            self.neo4j.run_query(
                """
                MERGE (a:AncestrySegment {population: $population})
                SET a.percentage = $percentage, a.confidence = $confidence
                WITH a
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_ANCESTRY]->(a)
                """,
                {
                    "population": seg["population"],
                    "percentage": seg.get("percentage", 0),
                    "confidence": seg.get("confidence", "moderate"),
                },
            )
