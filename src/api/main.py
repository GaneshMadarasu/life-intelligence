"""Life Intelligence System — FastAPI app, localhost:127.0.0.1:8000 only."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Life Intelligence System",
    description="Privacy-first personal GraphRAG — all data stays on your machine.",
    version="1.0.0",
)

# Only allow localhost origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Serve the UI
_UI_DIR = Path(__file__).parent.parent / "ui"
if _UI_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_UI_DIR)), name="static")

@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(str(_UI_DIR / "index.html"))

# ── Lazy singletons ───────────────────────────────────────────────────────────

def _neo4j():
    from src.core.neo4j_client import get_client
    return get_client()

def _vector():
    from src.core.vector_store import get_vector_store
    return get_vector_store()

def _hybrid():
    from src.retrieval.hybrid_retriever import HybridRetriever
    return HybridRetriever(_neo4j(), _vector())

def _generator():
    from src.generation.answer_generator import AnswerGenerator
    return AnswerGenerator()

def _safety():
    from src.core.safety_checker import SafetyChecker
    return SafetyChecker(_neo4j())

def _cross_domain():
    from src.core.cross_domain_linker import CrossDomainLinker
    return CrossDomainLinker(_neo4j())

def _person():
    from src.core.person import get_person_manager
    return get_person_manager(_neo4j())

def _timeline():
    from src.core.timeline import TimelineManager
    return TimelineManager(_neo4j())

def _hc_linker():
    from src.domains.healthcare.cross_vertical_linker import HealthcareCrossVerticalLinker
    return HealthcareCrossVerticalLinker(_neo4j())


# ── Pydantic models ───────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    file_path: str
    domain: str
    vertical: str

class QueryRequest(BaseModel):
    question: str
    domains: list[str] = ["all"]
    verticals: list[str] = ["all"]
    date_from: str | None = None
    date_to: str | None = None
    top_k: int = 5


# ── Domain management ─────────────────────────────────────────────────────────

@app.get("/domains", tags=["domains"])
async def list_domains() -> dict[str, Any]:
    """List all registered domains with status and stats."""
    active = []
    planned = [
        {"domain": "finances", "status": "planned", "verticals": ["banking", "investments", "insurance", "taxes"]},
        {"domain": "legal-contracts", "status": "planned", "verticals": ["employment", "property", "insurance-policies"]},
        {"domain": "career", "status": "planned", "verticals": ["employment-history", "skills", "education"]},
        {"domain": "relationships", "status": "planned", "verticals": ["family", "professional"]},
    ]
    try:
        from src.domains.healthcare.domain import HealthcareDomain
        hc = HealthcareDomain(_neo4j(), _vector())
        active.append(hc.get_status())
    except Exception as e:
        logger.warning("Could not load healthcare domain: %s", e)
    return {"active": active, "planned": planned}


@app.get("/domains/{domain}/summary", tags=["domains"])
async def domain_summary(domain: str) -> dict[str, Any]:
    if domain == "healthcare":
        from src.domains.healthcare.domain import HealthcareDomain
        hc = HealthcareDomain(_neo4j(), _vector())
        return hc.get_status()
    planned = {"finances", "legal-contracts", "career", "relationships"}
    if domain in planned:
        raise HTTPException(
            status_code=501,
            detail=f"This domain is planned but not yet implemented. See src/domains/{domain}/PLANNED.md for the roadmap.",
        )
    raise HTTPException(status_code=404, detail=f"Unknown domain: {domain}")


@app.get("/domains/{domain}/verticals", tags=["domains"])
async def domain_verticals(domain: str) -> dict[str, Any]:
    if domain == "healthcare":
        return {
            "domain": "healthcare",
            "verticals": ["medical", "fitness", "mental_health", "genetics"],
        }
    planned_verticals = {
        "finances": ["banking", "investments", "insurance", "taxes"],
        "legal-contracts": ["employment", "property", "insurance-policies"],
        "career": ["employment-history", "skills", "education"],
        "relationships": ["family", "professional"],
    }
    if domain in planned_verticals:
        raise HTTPException(
            status_code=501,
            detail=f"This domain is planned but not yet implemented. See src/domains/{domain}/PLANNED.md for the roadmap.",
        )
    raise HTTPException(status_code=404, detail=f"Unknown domain: {domain}")


# ── Universal endpoints ───────────────────────────────────────────────────────

@app.post("/ingest", tags=["universal"])
async def ingest(req: IngestRequest) -> dict[str, Any]:
    """Ingest a file into the specified domain/vertical."""
    if req.domain == "healthcare":
        from src.domains.healthcare.domain import HealthcareDomain
        hc = HealthcareDomain(_neo4j(), _vector())
        result = hc.ingest(req.file_path, req.vertical)
        # Run cross-vertical and cross-domain linkers
        try:
            _hc_linker().run_all_links()
            _cross_domain().run_all_rules()
        except Exception as e:
            logger.warning("Linker error (non-fatal): %s", e)
        return result
    planned = {"finances", "legal-contracts", "career", "relationships"}
    if req.domain in planned:
        raise HTTPException(
            status_code=501,
            detail=f"This domain is planned but not yet implemented. See src/domains/{req.domain}/PLANNED.md for the roadmap.",
        )
    raise HTTPException(status_code=400, detail=f"Unknown domain: {req.domain}")


@app.post("/query", tags=["universal"])
async def query(req: QueryRequest) -> dict[str, Any]:
    """Ask anything — hybrid retrieval across all specified domains."""
    retrieval = _hybrid().retrieve(
        question=req.question,
        domains=req.domains,
        verticals=req.verticals,
        date_from=req.date_from,
        date_to=req.date_to,
        top_k=req.top_k,
    )
    warnings = {}
    try:
        warnings = _safety().run_full_check()
    except Exception as e:
        logger.warning("Safety check failed: %s", e)

    cross_insights = []
    try:
        cross_insights = _cross_domain().get_cross_domain_insights()
    except Exception as e:
        logger.warning("Cross-domain insights failed: %s", e)

    answer = _generator().generate(
        question=req.question,
        context=retrieval["total_context"],
        domains=req.domains,
        cross_domain_insights=cross_insights,
        warnings=warnings,
    )
    return answer


@app.get("/me", tags=["universal"])
async def me() -> dict[str, Any]:
    """Person node + stats across all active domains."""
    return _person().get_person_summary()


@app.get("/timeline", tags=["universal"])
async def timeline(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    domains: str = Query("all"),
) -> dict[str, Any]:
    domain_list = [d.strip() for d in domains.split(",")]
    events = _timeline().get_timeline(date_from, date_to, domain_list)
    return {"events": events, "count": len(events)}


@app.get("/cross-domain/insights", tags=["universal"])
async def cross_domain_insights() -> dict[str, Any]:
    insights = _cross_domain().get_cross_domain_insights()
    return {"insights": insights, "count": len(insights)}


@app.get("/safety/full", tags=["universal"])
async def safety_full() -> dict[str, Any]:
    return _safety().run_full_check()


# ── Healthcare endpoints ──────────────────────────────────────────────────────

@app.get("/healthcare/timeline", tags=["healthcare"])
async def healthcare_timeline(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> dict[str, Any]:
    events = _timeline().get_timeline(date_from, date_to, ["healthcare"])
    return {"events": events, "count": len(events)}


@app.get("/healthcare/medications/current", tags=["healthcare"])
async def current_medications() -> dict[str, Any]:
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = _neo4j().run_query(QUERIES["current_medications"])
    return {"medications": results, "count": len(results)}


@app.get("/healthcare/conditions/active", tags=["healthcare"])
async def active_conditions() -> dict[str, Any]:
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = _neo4j().run_query(QUERIES["active_conditions"])
    return {"conditions": results, "count": len(results)}


@app.get("/healthcare/labs/trends", tags=["healthcare"])
async def lab_trends(test: str = Query(..., description="e.g. HbA1c")) -> dict[str, Any]:
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = _neo4j().run_query(QUERIES["lab_trends"], {"test_name": test})
    return {"test": test, "results": results, "count": len(results)}


@app.get("/healthcare/safety/current", tags=["healthcare"])
async def healthcare_safety() -> dict[str, Any]:
    checker = _safety()
    warnings = checker.run_full_check()
    # Filter to healthcare-domain warnings only
    hc_warnings = [w for w in warnings.get("warnings", []) if w.get("domain") == "healthcare"]
    return {"total": len(hc_warnings), "warnings": hc_warnings}


@app.get("/healthcare/genetics/risks", tags=["healthcare"])
async def genetics_risks() -> dict[str, Any]:
    from src.domains.healthcare.verticals.genetics.queries import QUERIES
    high = _neo4j().run_query(QUERIES["high_risks"])
    all_risks = _neo4j().run_query(QUERIES["all_genetic_risks"])
    pharmacogenes = _neo4j().run_query(QUERIES["pharmacogene_warnings"])
    return {
        "high_risks": high,
        "all_risks": all_risks,
        "pharmacogene_warnings": pharmacogenes,
    }


@app.get("/healthcare/insights/cross-vertical", tags=["healthcare"])
async def cross_vertical_insights() -> dict[str, Any]:
    linker = _hc_linker()
    counts = linker.run_all_links()
    interactions = _neo4j().run_query(
        """
        MATCH (s:Supplement)-[r:INTERACTS_WITH]->(m:Medication)
        WHERE EXISTS((:Person {id: 'primary'})-[:TAKES_SUPPLEMENT]->(s))
        AND EXISTS((:Person {id: 'primary'})-[:TAKES_MEDICATION]->(m))
        RETURN s.name AS supplement, m.name AS medication,
               r.severity AS severity, r.description AS description
        """
    )
    drug_drug = _neo4j().run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:TAKES_MEDICATION]->(m1:Medication)
        MATCH (p)-[:TAKES_MEDICATION]->(m2:Medication)
        MATCH (m1)-[r:INTERACTS_WITH]->(m2)
        WHERE m1.name < m2.name
        RETURN m1.name AS drug1, m2.name AS drug2,
               r.severity AS severity, r.description AS description
        """
    )
    return {
        "links_created": counts,
        "supplement_drug_interactions": interactions,
        "drug_drug_interactions": drug_drug,
    }


# ── Whoop integration endpoints ──────────────────────────────────────────────

class WhoopSyncRequest(BaseModel):
    days: int = 30


@app.get("/integrations/whoop/status", tags=["integrations"])
async def whoop_status() -> dict[str, Any]:
    """Connection status, profile info, and last sync summary."""
    from src.integrations.whoop.sync import WhoopSync
    try:
        syncer = WhoopSync(_neo4j())
        return syncer.get_status()
    except Exception as e:
        return {"connected": False, "error": str(e)}


@app.post("/integrations/whoop/sync", tags=["integrations"])
async def whoop_sync(req: WhoopSyncRequest = WhoopSyncRequest()) -> dict[str, Any]:
    """Trigger a Whoop sync. Fetches the last `days` days of data."""
    from src.integrations.whoop.sync import WhoopSync
    try:
        syncer = WhoopSync(_neo4j(), _vector())
        result = syncer.run(days=req.days)
        # Re-run cross-vertical linker after ingesting new data
        try:
            _hc_linker().run_all_links()
        except Exception as e:
            logger.warning("Linker error after Whoop sync (non-fatal): %s", e)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/healthcare/fitness/recovery", tags=["healthcare"])
async def recovery_trends(
    days: int = Query(30, description="Number of days to look back"),
) -> dict[str, Any]:
    """HRV, resting heart rate, and recovery score trends from Whoop."""
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    results = _neo4j().run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_RECOVERY]->(r:WhoopRecovery)
        WHERE r.date >= $cutoff
        RETURN r.date AS date, r.recovery_score AS recovery_score,
               r.hrv_rmssd AS hrv_rmssd, r.resting_hr AS resting_hr,
               r.spo2_pct AS spo2_pct, r.skin_temp_celsius AS skin_temp_celsius
        ORDER BY r.date DESC
        """,
        {"cutoff": cutoff},
    )
    avg_hrv = (
        round(sum(r["hrv_rmssd"] for r in results if r["hrv_rmssd"]) / len(results), 1)
        if results else 0
    )
    avg_rhr = (
        round(sum(r["resting_hr"] for r in results if r["resting_hr"]) / len(results), 1)
        if results else 0
    )
    avg_recovery = (
        round(sum(r["recovery_score"] for r in results if r["recovery_score"]) / len(results), 1)
        if results else 0
    )
    return {
        "days": days,
        "records": results,
        "count": len(results),
        "averages": {
            "hrv_rmssd": avg_hrv,
            "resting_hr": avg_rhr,
            "recovery_score": avg_recovery,
        },
    }


@app.get("/healthcare/fitness/strain", tags=["healthcare"])
async def strain_trends(
    days: int = Query(30, description="Number of days to look back"),
) -> dict[str, Any]:
    """Daily strain scores and workout load from Whoop."""
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    cycles = _neo4j().run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_WHOOP_CYCLE]->(c:WhoopCycle)
        WHERE c.date >= $cutoff
        RETURN c.date AS date, c.strain AS strain, c.calories AS calories,
               c.avg_heart_rate AS avg_heart_rate, c.max_heart_rate AS max_heart_rate
        ORDER BY c.date DESC
        """,
        {"cutoff": cutoff},
    )
    workouts = _neo4j().run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_WORKOUT]->(w:Workout)
        WHERE w.source = 'whoop' AND w.date >= $cutoff
        RETURN w.date AS date, w.type AS type, w.strain_score AS strain_score,
               w.duration_mins AS duration_mins, w.calories_burned AS calories_burned,
               w.avg_heart_rate AS avg_heart_rate, w.max_heart_rate AS max_heart_rate
        ORDER BY w.date DESC
        """,
        {"cutoff": cutoff},
    )
    avg_strain = (
        round(sum(c["strain"] for c in cycles if c["strain"]) / len(cycles), 1)
        if cycles else 0
    )
    return {
        "days": days,
        "daily_cycles": cycles,
        "workouts": workouts,
        "averages": {"daily_strain": avg_strain},
    }


@app.get("/healthcare/fitness/sleep", tags=["healthcare"])
async def sleep_trends(
    days: int = Query(30, description="Number of days to look back"),
) -> dict[str, Any]:
    """Sleep performance, HRV-linked sleep quality, and stage breakdown from Whoop."""
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    results = _neo4j().run_query(
        """
        MATCH (p:Person {id: 'primary'})-[:HAS_SLEEP_RECORD]->(sr:SleepRecord)
        WHERE sr.date >= $cutoff AND sr.source = 'whoop'
        RETURN sr.date AS date, sr.duration_hours AS duration_hours,
               sr.deep_sleep_hours AS deep_sleep_hours, sr.rem_hours AS rem_hours,
               sr.light_sleep_hours AS light_sleep_hours,
               sr.sleep_performance_pct AS sleep_performance_pct,
               sr.sleep_efficiency_pct AS sleep_efficiency_pct,
               sr.respiratory_rate AS respiratory_rate,
               sr.cycle_count AS cycle_count, sr.disturbances AS disturbances
        ORDER BY sr.date DESC
        """,
        {"cutoff": cutoff},
    )
    avg_perf = (
        round(sum(r["sleep_performance_pct"] for r in results if r["sleep_performance_pct"]) / len(results), 1)
        if results else 0
    )
    avg_dur = (
        round(sum(r["duration_hours"] for r in results if r["duration_hours"]) / len(results), 2)
        if results else 0
    )
    return {
        "days": days,
        "records": results,
        "count": len(results),
        "averages": {
            "sleep_performance_pct": avg_perf,
            "duration_hours": avg_dur,
        },
    }


# ── Planned domain stubs ──────────────────────────────────────────────────────

PLANNED_MSG = "This domain is planned but not yet implemented. See src/domains/{domain}/PLANNED.md for the roadmap."

@app.get("/finances/summary", tags=["planned"])
async def finances_summary():
    raise HTTPException(status_code=501, detail=PLANNED_MSG.format(domain="finances"))

@app.get("/finances/insurance/coverage", tags=["planned"])
async def finances_insurance():
    raise HTTPException(status_code=501, detail=PLANNED_MSG.format(domain="finances"))

@app.get("/legal/contracts/active", tags=["planned"])
async def legal_contracts():
    raise HTTPException(status_code=501, detail=PLANNED_MSG.format(domain="legal-contracts"))

@app.get("/legal/obligations/upcoming", tags=["planned"])
async def legal_obligations():
    raise HTTPException(status_code=501, detail=PLANNED_MSG.format(domain="legal-contracts"))

@app.get("/career/summary", tags=["planned"])
async def career_summary():
    raise HTTPException(status_code=501, detail=PLANNED_MSG.format(domain="career"))


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    logger.info("Life Intelligence System starting on 127.0.0.1:8000")
    try:
        neo4j = _neo4j()
        neo4j.init_backbone_schema()
        from src.core.person import get_person_manager
        pm = get_person_manager(neo4j)
        pm.ensure_person()
        from src.domains.healthcare.domain import HealthcareDomain
        hc = HealthcareDomain(neo4j, _vector())
        hc.register()
        logger.info("Healthcare domain registered")
    except Exception as e:
        logger.warning("Startup initialization warning (services may not be running): %s", e)


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=int(os.getenv("APP_PORT", "8000")),
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
