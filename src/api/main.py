"""Life Intelligence System — FastAPI app, localhost:127.0.0.1:8000 only."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Life Intelligence System",
    description="Privacy-first personal GraphRAG — all data stays on your machine.",
    version="1.1.0",
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


# ── Async executor helper ─────────────────────────────────────────────────────

async def _run_sync(fn, *args, **kwargs):
    """Run a synchronous (blocking) function in a thread pool so it doesn't
    block FastAPI's event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


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
    conversation_history: list[dict] = []

class WhoopSyncRequest(BaseModel):
    days: int = 30

class GCalSyncRequest(BaseModel):
    days_ahead: int = 90
    days_back: int = 30

class GmailSyncRequest(BaseModel):
    days_back: int = 90
    domains: list[str] = []   # empty = all domains
    extract_entities: bool = True


# ── Domain management ─────────────────────────────────────────────────────────

@app.get("/domains", tags=["domains"])
async def list_domains() -> dict[str, Any]:
    """List all registered domains with status and stats."""
    active = []
    for domain_cls, name in [
        ("src.domains.healthcare.domain.HealthcareDomain", "healthcare"),
        ("src.domains.finances.domain.FinancesDomain", "finances"),
        ("src.domains.career.domain.CareerDomain", "career"),
    ]:
        try:
            module, cls = domain_cls.rsplit(".", 1)
            import importlib
            mod = importlib.import_module(module)
            domain = getattr(mod, cls)(_neo4j(), _vector())
            active.append(await _run_sync(domain.get_status))
        except Exception as e:
            logger.warning("Could not load domain %s: %s", name, e)

    planned = [
        {"domain": "legal-contracts", "status": "planned", "verticals": ["employment", "property", "insurance-policies"]},
        {"domain": "relationships", "status": "planned", "verticals": ["family", "professional"]},
    ]
    return {"active": active, "planned": planned}


@app.get("/domains/{domain}/summary", tags=["domains"])
async def domain_summary(domain: str) -> dict[str, Any]:
    domain_map = {
        "healthcare": "src.domains.healthcare.domain.HealthcareDomain",
        "finances": "src.domains.finances.domain.FinancesDomain",
        "career": "src.domains.career.domain.CareerDomain",
    }
    if domain in domain_map:
        import importlib
        module, cls = domain_map[domain].rsplit(".", 1)
        mod = importlib.import_module(module)
        d = getattr(mod, cls)(_neo4j(), _vector())
        return await _run_sync(d.get_status)
    planned = {"legal-contracts", "relationships"}
    if domain in planned:
        raise HTTPException(
            status_code=501,
            detail=f"Domain planned but not yet implemented. See src/domains/{domain}/PLANNED.md.",
        )
    raise HTTPException(status_code=404, detail=f"Unknown domain: {domain}")


@app.get("/domains/{domain}/verticals", tags=["domains"])
async def domain_verticals(domain: str) -> dict[str, Any]:
    verticals_map = {
        "healthcare": ["medical", "fitness", "mental_health", "genetics"],
        "finances": ["banking", "investments", "insurance", "taxes"],
        "career": ["employment-history", "skills", "education"],
    }
    if domain in verticals_map:
        return {"domain": domain, "verticals": verticals_map[domain]}
    planned_verticals = {
        "legal-contracts": ["employment", "property", "insurance-policies"],
        "relationships": ["family", "professional"],
    }
    if domain in planned_verticals:
        raise HTTPException(status_code=501, detail=f"Domain planned but not yet implemented.")
    raise HTTPException(status_code=404, detail=f"Unknown domain: {domain}")


# ── Universal endpoints ───────────────────────────────────────────────────────

@app.post("/ingest", tags=["universal"])
async def ingest(req: IngestRequest) -> dict[str, Any]:
    """Ingest a file into the specified domain/vertical."""
    domain_map = {
        "healthcare": "src.domains.healthcare.domain.HealthcareDomain",
        "finances": "src.domains.finances.domain.FinancesDomain",
        "career": "src.domains.career.domain.CareerDomain",
    }
    if req.domain not in domain_map:
        planned = {"legal-contracts", "relationships"}
        if req.domain in planned:
            raise HTTPException(status_code=501, detail=f"Domain planned but not yet implemented.")
        raise HTTPException(status_code=400, detail=f"Unknown domain: {req.domain}")

    import importlib
    module, cls = domain_map[req.domain].rsplit(".", 1)
    mod = importlib.import_module(module)
    domain_obj = getattr(mod, cls)(_neo4j(), _vector())

    def _do_ingest():
        result = domain_obj.ingest(req.file_path, req.vertical)
        try:
            if req.domain == "healthcare":
                _hc_linker().run_all_links()
            _cross_domain().run_all_rules()
        except Exception as e:
            logger.warning("Linker error (non-fatal): %s", e)
        return result

    return await _run_sync(_do_ingest)


@app.post("/ingest/upload", tags=["universal"])
async def ingest_upload(
    file: UploadFile = File(...),
    domain: str = Form(...),
    vertical: str = Form(...),
) -> dict[str, Any]:
    """Upload a file directly from the browser and ingest it."""
    upload_dir = Path("data/uploads") / domain / vertical
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / file.filename
    content = await file.read()
    dest.write_bytes(content)
    logger.info("Uploaded %s → %s", file.filename, dest)
    # Reuse the ingest logic
    return await ingest(IngestRequest(file_path=str(dest), domain=domain, vertical=vertical))


@app.post("/query", tags=["universal"])
async def query(req: QueryRequest) -> dict[str, Any]:
    """Ask anything — hybrid retrieval across all specified domains."""
    def _do_query():
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

        return _generator().generate(
            question=req.question,
            context=retrieval["total_context"],
            domains=req.domains,
            cross_domain_insights=cross_insights,
            warnings=warnings,
            conversation_history=req.conversation_history,
        )

    return await _run_sync(_do_query)


@app.post("/query/stream", tags=["universal"])
async def query_stream(req: QueryRequest):
    """Streaming version — returns SSE token-by-token for real-time UI updates."""
    def _retrieve():
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
        except Exception:
            pass
        cross_insights = []
        try:
            cross_insights = _cross_domain().get_cross_domain_insights()
        except Exception:
            pass
        return retrieval["total_context"], warnings, cross_insights

    context, warnings, cross_insights = await _run_sync(_retrieve)

    gen = _generator()

    def _sse_generator():
        yield from gen.generate_stream(
            question=req.question,
            context=context,
            domains=req.domains,
            cross_domain_insights=cross_insights,
            warnings=warnings,
            conversation_history=req.conversation_history,
        )

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/me", tags=["universal"])
async def me() -> dict[str, Any]:
    return await _run_sync(_person().get_person_summary)


@app.get("/timeline", tags=["universal"])
async def timeline(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    domains: str = Query("all"),
) -> dict[str, Any]:
    domain_list = [d.strip() for d in domains.split(",")]
    events = await _run_sync(_timeline().get_timeline, date_from, date_to, domain_list)
    return {"events": events, "count": len(events)}


@app.get("/cross-domain/insights", tags=["universal"])
async def cross_domain_insights() -> dict[str, Any]:
    insights = await _run_sync(_cross_domain().get_cross_domain_insights)
    return {"insights": insights, "count": len(insights)}


@app.get("/safety/full", tags=["universal"])
async def safety_full() -> dict[str, Any]:
    return await _run_sync(_safety().run_full_check)


# ── Alerts endpoint ───────────────────────────────────────────────────────────

@app.get("/alerts", tags=["universal"])
async def alerts() -> dict[str, Any]:
    """Proactive alerts — HRV decline, overdue labs, expiring certs, low recovery streaks."""
    from datetime import date, timedelta

    def _build_alerts():
        found: list[dict] = []
        neo4j = _neo4j()

        # 1. HRV 3-day declining trend
        try:
            hrv_rows = neo4j.run_query(
                """
                MATCH (p:Person {id: 'primary'})-[:HAS_RECOVERY]->(r:WhoopRecovery)
                WHERE r.date >= $cutoff
                RETURN r.date AS date, r.hrv_rmssd AS hrv
                ORDER BY r.date DESC LIMIT 7
                """,
                {"cutoff": (date.today() - timedelta(days=7)).isoformat()},
            )
            if len(hrv_rows) >= 3:
                last3 = [r["hrv"] for r in hrv_rows[:3] if r.get("hrv")]
                if len(last3) == 3 and last3[0] < last3[1] < last3[2]:
                    found.append({
                        "id": "hrv_decline",
                        "title": "HRV Declining 3 Days",
                        "message": f"HRV dropped from {last3[2]:.0f}ms → {last3[0]:.0f}ms over the last 3 days. Consider rest.",
                        "severity": "medium",
                        "domain": "healthcare",
                    })
        except Exception as e:
            logger.debug("HRV alert check failed: %s", e)

        # 2. Recovery streak below 34 (red zone)
        try:
            rec_rows = neo4j.run_query(
                """
                MATCH (p:Person {id: 'primary'})-[:HAS_RECOVERY]->(r:WhoopRecovery)
                WHERE r.date >= $cutoff AND r.recovery_score < 34
                RETURN count(r) AS low_days
                """,
                {"cutoff": (date.today() - timedelta(days=5)).isoformat()},
            )
            if rec_rows and rec_rows[0].get("low_days", 0) >= 3:
                found.append({
                    "id": "recovery_red",
                    "title": "Prolonged Low Recovery",
                    "message": f"{rec_rows[0]['low_days']} of the last 5 days in red zone (< 34%). Prioritise sleep and recovery.",
                    "severity": "high",
                    "domain": "healthcare",
                })
        except Exception as e:
            logger.debug("Recovery alert check failed: %s", e)

        # 3. Lab results older than 12 months
        try:
            cutoff_12m = (date.today() - timedelta(days=365)).isoformat()
            overdue_labs = neo4j.run_query(
                """
                MATCH (p:Person {id: 'primary'})-[:HAS_CONDITION]->(c:Condition)
                WHERE c.status IN ['active','chronic']
                WITH collect(c.name) AS conditions
                MATCH (p)-[:HAS_LAB_RESULT]->(l:LabResult)
                WHERE l.date < $cutoff
                WITH l.test_name AS test, max(l.date) AS last_date
                RETURN test, last_date
                ORDER BY last_date
                LIMIT 5
                """,
                {"cutoff": cutoff_12m},
            )
            for lab in overdue_labs:
                found.append({
                    "id": f"lab_overdue_{lab['test']}",
                    "title": f"Overdue Lab: {lab['test']}",
                    "message": f"Last result was {lab['last_date']}. Consider scheduling a retest.",
                    "severity": "low",
                    "domain": "healthcare",
                })
        except Exception as e:
            logger.debug("Lab alert check failed: %s", e)

        # 4. Expiring certifications (career domain)
        try:
            cutoff_cert = (date.today() + timedelta(days=90)).isoformat()
            expiring = neo4j.run_query(
                """
                MATCH (p:Person {id: 'primary'})-[:HAS_CERTIFICATION]->(c:Certification)
                WHERE c.expiry_date <> '' AND c.expiry_date <= $cutoff
                RETURN c.name AS name, c.expiry_date AS expiry_date
                ORDER BY c.expiry_date
                """,
                {"cutoff": cutoff_cert},
            )
            for cert in expiring:
                found.append({
                    "id": f"cert_expiring_{cert['name']}",
                    "title": f"Certification Expiring: {cert['name']}",
                    "message": f"Expires {cert['expiry_date']}. Renew before it lapses.",
                    "severity": "medium",
                    "domain": "career",
                })
        except Exception as e:
            logger.debug("Cert alert check failed: %s", e)

        # 5. Insurance renewals within 60 days
        try:
            cutoff_ins = (date.today() + timedelta(days=60)).isoformat()
            today_str = date.today().isoformat()
            renewals = neo4j.run_query(
                """
                MATCH (p:Person {id: 'primary'})-[:HAS_INSURANCE]->(i:InsurancePlan)
                WHERE i.end_date <> '' AND i.end_date >= $today AND i.end_date <= $cutoff
                RETURN i.plan_name AS name, i.type AS type, i.end_date AS end_date
                ORDER BY i.end_date
                """,
                {"today": today_str, "cutoff": cutoff_ins},
            )
            for ins in renewals:
                found.append({
                    "id": f"insurance_renewal_{ins['name']}",
                    "title": f"Insurance Renewal: {ins['name']}",
                    "message": f"{ins['type'].capitalize()} insurance expires {ins['end_date']}. Review and renew.",
                    "severity": "medium",
                    "domain": "finances",
                })
        except Exception as e:
            logger.debug("Insurance alert check failed: %s", e)

        # 6. Drug-drug interactions (always surface)
        try:
            interactions = neo4j.run_query(
                """
                MATCH (p:Person {id: 'primary'})-[:TAKES_MEDICATION]->(m1:Medication)
                MATCH (p)-[:TAKES_MEDICATION]->(m2:Medication)
                MATCH (m1)-[r:INTERACTS_WITH]->(m2)
                WHERE m1.name < m2.name AND r.severity = 'high'
                RETURN m1.name AS drug1, m2.name AS drug2, r.description AS description
                """
            )
            for i in interactions:
                found.append({
                    "id": f"interaction_{i['drug1']}_{i['drug2']}",
                    "title": f"Drug Interaction: {i['drug1']} + {i['drug2']}",
                    "message": i.get("description", "High-severity interaction detected. Consult your doctor."),
                    "severity": "high",
                    "domain": "healthcare",
                })
        except Exception as e:
            logger.debug("Drug interaction alert check failed: %s", e)

        # Sort by severity
        sev_order = {"high": 0, "medium": 1, "low": 2}
        found.sort(key=lambda a: sev_order.get(a.get("severity", "low"), 3))
        return found

    alerts_list = await _run_sync(_build_alerts)
    return {
        "alerts": alerts_list,
        "count": len(alerts_list),
        "high": sum(1 for a in alerts_list if a["severity"] == "high"),
        "medium": sum(1 for a in alerts_list if a["severity"] == "medium"),
        "low": sum(1 for a in alerts_list if a["severity"] == "low"),
    }


# ── Healthcare endpoints ──────────────────────────────────────────────────────

@app.get("/healthcare/timeline", tags=["healthcare"])
async def healthcare_timeline(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> dict[str, Any]:
    events = await _run_sync(_timeline().get_timeline, date_from, date_to, ["healthcare"])
    return {"events": events, "count": len(events)}


@app.get("/healthcare/medications/current", tags=["healthcare"])
async def current_medications() -> dict[str, Any]:
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = await _run_sync(_neo4j().run_query, QUERIES["current_medications"])
    return {"medications": results, "count": len(results)}


@app.get("/healthcare/conditions/active", tags=["healthcare"])
async def active_conditions() -> dict[str, Any]:
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = await _run_sync(_neo4j().run_query, QUERIES["active_conditions"])
    return {"conditions": results, "count": len(results)}


@app.get("/healthcare/labs/trends", tags=["healthcare"])
async def lab_trends(test: str = Query(..., description="e.g. HbA1c")) -> dict[str, Any]:
    from src.domains.healthcare.verticals.medical.queries import QUERIES
    results = await _run_sync(_neo4j().run_query, QUERIES["lab_trends"], {"test_name": test})
    return {"test": test, "results": results, "count": len(results)}


@app.get("/healthcare/safety/current", tags=["healthcare"])
async def healthcare_safety() -> dict[str, Any]:
    checker = _safety()
    warnings = await _run_sync(checker.run_full_check)
    hc_warnings = [w for w in warnings.get("warnings", []) if w.get("domain") == "healthcare"]
    return {"total": len(hc_warnings), "warnings": hc_warnings}


@app.get("/healthcare/genetics/risks", tags=["healthcare"])
async def genetics_risks() -> dict[str, Any]:
    from src.domains.healthcare.verticals.genetics.queries import QUERIES
    high, all_risks, pharmacogenes = await asyncio.gather(
        _run_sync(_neo4j().run_query, QUERIES["high_risks"]),
        _run_sync(_neo4j().run_query, QUERIES["all_genetic_risks"]),
        _run_sync(_neo4j().run_query, QUERIES["pharmacogene_warnings"]),
    )
    return {"high_risks": high, "all_risks": all_risks, "pharmacogene_warnings": pharmacogenes}


@app.get("/healthcare/insights/cross-vertical", tags=["healthcare"])
async def cross_vertical_insights() -> dict[str, Any]:
    def _do():
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
        return {"links_created": counts, "supplement_drug_interactions": interactions, "drug_drug_interactions": drug_drug}
    return await _run_sync(_do)


# ── Whoop integration endpoints ──────────────────────────────────────────────

@app.get("/integrations/whoop/status", tags=["integrations"])
async def whoop_status() -> dict[str, Any]:
    from src.integrations.whoop.sync import WhoopSync
    try:
        return await _run_sync(WhoopSync(_neo4j()).get_status)
    except Exception as e:
        return {"connected": False, "error": str(e)}


@app.post("/integrations/whoop/sync", tags=["integrations"])
async def whoop_sync(req: WhoopSyncRequest = WhoopSyncRequest()) -> dict[str, Any]:
    from src.integrations.whoop.sync import WhoopSync
    def _do():
        result = WhoopSync(_neo4j(), _vector()).run(days=req.days)
        try:
            _hc_linker().run_all_links()
        except Exception as e:
            logger.warning("Linker error after Whoop sync (non-fatal): %s", e)
        return result
    try:
        return await _run_sync(_do)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/healthcare/fitness/recovery", tags=["healthcare"])
async def recovery_trends(days: int = Query(30)) -> dict[str, Any]:
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    results = await _run_sync(
        _neo4j().run_query,
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
    avg_hrv = round(sum(r["hrv_rmssd"] for r in results if r.get("hrv_rmssd")) / max(len(results), 1), 1)
    avg_rhr = round(sum(r["resting_hr"] for r in results if r.get("resting_hr")) / max(len(results), 1), 1)
    avg_recovery = round(sum(r["recovery_score"] for r in results if r.get("recovery_score")) / max(len(results), 1), 1)
    return {
        "days": days,
        "records": results,
        "count": len(results),
        "averages": {"hrv_rmssd": avg_hrv, "resting_hr": avg_rhr, "recovery_score": avg_recovery},
    }


@app.get("/healthcare/fitness/strain", tags=["healthcare"])
async def strain_trends(days: int = Query(30)) -> dict[str, Any]:
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    cycles, workouts = await asyncio.gather(
        _run_sync(
            _neo4j().run_query,
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_WHOOP_CYCLE]->(c:WhoopCycle)
            WHERE c.date >= $cutoff
            RETURN c.date AS date, c.strain AS strain, c.calories AS calories,
                   c.avg_heart_rate AS avg_heart_rate, c.max_heart_rate AS max_heart_rate
            ORDER BY c.date DESC
            """,
            {"cutoff": cutoff},
        ),
        _run_sync(
            _neo4j().run_query,
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_WORKOUT]->(w:Workout)
            WHERE w.source = 'whoop' AND w.date >= $cutoff
            RETURN w.date AS date, w.type AS type, w.strain_score AS strain_score,
                   w.duration_mins AS duration_mins, w.calories_burned AS calories_burned,
                   w.avg_heart_rate AS avg_heart_rate, w.max_heart_rate AS max_heart_rate
            ORDER BY w.date DESC
            """,
            {"cutoff": cutoff},
        ),
    )
    avg_strain = round(sum(c["strain"] for c in cycles if c.get("strain")) / max(len(cycles), 1), 1)
    return {
        "days": days,
        "daily_cycles": cycles,
        "workouts": workouts,
        "averages": {"daily_strain": avg_strain},
    }


@app.get("/healthcare/fitness/sleep", tags=["healthcare"])
async def sleep_trends(days: int = Query(30)) -> dict[str, Any]:
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    results = await _run_sync(
        _neo4j().run_query,
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
    avg_perf = round(sum(r["sleep_performance_pct"] for r in results if r.get("sleep_performance_pct")) / max(len(results), 1), 1)
    avg_dur = round(sum(r["duration_hours"] for r in results if r.get("duration_hours")) / max(len(results), 1), 2)
    return {
        "days": days,
        "records": results,
        "count": len(results),
        "averages": {"sleep_performance_pct": avg_perf, "duration_hours": avg_dur},
    }


# ── Finances endpoints ────────────────────────────────────────────────────────

@app.get("/finances/summary", tags=["finances"])
async def finances_summary() -> dict[str, Any]:
    from src.domains.finances.queries import QUERIES
    accounts, investments, debts = await asyncio.gather(
        _run_sync(_neo4j().run_query, QUERIES["all_accounts"]),
        _run_sync(_neo4j().run_query, QUERIES["all_investments"]),
        _run_sync(_neo4j().run_query, QUERIES["all_debts"]),
    )
    net_worth_rows = await _run_sync(_neo4j().run_query, QUERIES["net_worth"])
    return {
        "accounts": accounts,
        "investments": investments,
        "debts": debts,
        "net_worth": net_worth_rows[0] if net_worth_rows else {},
    }


@app.get("/finances/insurance/coverage", tags=["finances"])
async def finances_insurance() -> dict[str, Any]:
    from src.domains.finances.queries import QUERIES
    plans = await _run_sync(_neo4j().run_query, QUERIES["insurance_plans"])
    cross = await _run_sync(_neo4j().run_query, QUERIES["health_insurance_cross"])
    return {"insurance_plans": plans, "health_cross_domain": cross}


# ── Career endpoints ──────────────────────────────────────────────────────────

@app.get("/career/summary", tags=["career"])
async def career_summary() -> dict[str, Any]:
    from src.domains.career.queries import QUERIES
    jobs, skills, education, certs = await asyncio.gather(
        _run_sync(_neo4j().run_query, QUERIES["employment_history"]),
        _run_sync(_neo4j().run_query, QUERIES["all_skills"]),
        _run_sync(_neo4j().run_query, QUERIES["education_history"]),
        _run_sync(_neo4j().run_query, QUERIES["certifications"]),
    )
    return {"jobs": jobs, "skills": skills, "education": education, "certifications": certs}


@app.get("/career/current-job", tags=["career"])
async def career_current_job() -> dict[str, Any]:
    from src.domains.career.queries import QUERIES
    results = await _run_sync(_neo4j().run_query, QUERIES["current_job"])
    return {"current_job": results[0] if results else None}


# ── Google Calendar integration endpoints ─────────────────────────────────────

@app.get("/integrations/gcal/status", tags=["integrations"])
async def gcal_status() -> dict[str, Any]:
    from src.integrations.google_calendar.sync import GoogleCalendarSync
    try:
        return GoogleCalendarSync(_neo4j()).get_status()
    except Exception as e:
        return {"authenticated": False, "error": str(e)}


@app.post("/integrations/gcal/sync", tags=["integrations"])
async def gcal_sync(req: GCalSyncRequest = GCalSyncRequest()) -> dict[str, Any]:
    from src.integrations.google_calendar.sync import GoogleCalendarSync
    try:
        return await _run_sync(
            GoogleCalendarSync(_neo4j()).run,
            req.days_ahead,
            req.days_back,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/integrations/gcal/upcoming", tags=["integrations"])
async def gcal_upcoming(days: int = Query(14)) -> dict[str, Any]:
    from src.integrations.google_calendar.sync import GoogleCalendarSync
    try:
        events = await _run_sync(GoogleCalendarSync(_neo4j()).get_upcoming_events, days)
        return {"events": events, "count": len(events)}
    except Exception as e:
        return {"events": [], "count": 0, "error": str(e)}


# ── Gmail integration endpoints ────────────────────────────────────────────���─

def _gmail_syncer(with_claude: bool = False):
    from src.integrations.gmail.sync import GmailSync
    anthropic_client = None
    if with_claude:
        try:
            import anthropic
            anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        except Exception:
            pass
    return GmailSync(_neo4j(), anthropic_client)


@app.get("/integrations/gmail/status", tags=["integrations"])
async def gmail_status() -> dict[str, Any]:
    """Gmail connection status and ingested email counts."""
    try:
        return await _run_sync(_gmail_syncer().get_status)
    except Exception as e:
        return {"authenticated": False, "error": str(e)}


@app.post("/integrations/gmail/sync", tags=["integrations"])
async def gmail_sync(req: GmailSyncRequest = GmailSyncRequest()) -> dict[str, Any]:
    """Sync domain-relevant emails from Gmail into the knowledge graph."""
    def _do():
        syncer = _gmail_syncer(with_claude=req.extract_entities)
        return syncer.run(
            days_back=req.days_back,
            domains=req.domains or None,
            extract_entities=req.extract_entities,
        )
    try:
        return await _run_sync(_do)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/integrations/gmail/emails", tags=["integrations"])
async def gmail_emails(
    domain: str | None = Query(None, description="healthcare | finances | career | general"),
    days: int | None = Query(None, description="Only show emails from last N days"),
    limit: int = Query(50, le=200),
) -> dict[str, Any]:
    """List ingested emails from the graph, optionally filtered by domain."""
    try:
        emails = await _run_sync(
            _gmail_syncer().get_emails,
            domain,
            limit,
            days,
        )
        return {"emails": emails, "count": len(emails)}
    except Exception as e:
        return {"emails": [], "count": 0, "error": str(e)}


@app.post("/integrations/gmail/search", tags=["integrations"])
async def gmail_search(
    q: str = Query(..., description="Gmail search query (same syntax as Gmail search bar)"),
    domain: str = Query("general"),
) -> dict[str, Any]:
    """Ad-hoc Gmail search — ingest any emails matching the query."""
    def _do():
        return _gmail_syncer(with_claude=True).search_and_ingest(q, domain=domain)
    try:
        return await _run_sync(_do)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Planned domain stubs ──────────────────────────────────────────────────────

PLANNED_MSG = "Domain planned but not yet implemented. See src/domains/{domain}/PLANNED.md."

@app.get("/legal/contracts/active", tags=["planned"])
async def legal_contracts():
    raise HTTPException(status_code=501, detail=PLANNED_MSG.format(domain="legal-contracts"))

@app.get("/legal/obligations/upcoming", tags=["planned"])
async def legal_obligations():
    raise HTTPException(status_code=501, detail=PLANNED_MSG.format(domain="legal-contracts"))


# ── Scheduled tasks ───────────────────────────────────────────────────────────

def _start_scheduler():
    """Start background scheduler for periodic Whoop sync and alerts refresh."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning("apscheduler not installed — background sync disabled. Run: pip install apscheduler")
        return

    scheduler = BackgroundScheduler()

    def _auto_whoop_sync():
        logger.info("Scheduled Whoop auto-sync starting…")
        try:
            from src.integrations.whoop.sync import WhoopSync
            result = WhoopSync(_neo4j(), _vector()).run(days=7)
            logger.info("Scheduled Whoop sync complete: %s", result)
            try:
                _hc_linker().run_all_links()
            except Exception as e:
                logger.warning("Linker after auto-sync (non-fatal): %s", e)
        except Exception as e:
            logger.warning("Scheduled Whoop sync failed (non-fatal): %s", e)

    scheduler.add_job(
        _auto_whoop_sync,
        trigger=IntervalTrigger(hours=int(os.getenv("WHOOP_SYNC_INTERVAL_HOURS", "6"))),
        id="whoop_auto_sync",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Background scheduler started (Whoop auto-sync every %sh)", os.getenv("WHOOP_SYNC_INTERVAL_HOURS", "6"))
    return scheduler


# ── Startup ───────────────────────────────────────────────────────────────────

_scheduler = None


@app.on_event("startup")
async def startup_event():
    global _scheduler
    logger.info("Life Intelligence System starting on 127.0.0.1:8000")
    try:
        neo4j = _neo4j()
        neo4j.init_backbone_schema()
        from src.core.person import get_person_manager
        get_person_manager(neo4j).ensure_person()

        # Register all active domains
        for domain_module, domain_cls in [
            ("src.domains.healthcare.domain", "HealthcareDomain"),
            ("src.domains.finances.domain", "FinancesDomain"),
            ("src.domains.career.domain", "CareerDomain"),
        ]:
            try:
                import importlib
                mod = importlib.import_module(domain_module)
                domain = getattr(mod, domain_cls)(neo4j, _vector())
                domain.register()
                logger.info("%s registered", domain_cls)
            except Exception as e:
                logger.warning("Could not register %s: %s", domain_cls, e)

    except Exception as e:
        logger.warning("Startup initialization warning (services may not be running): %s", e)

    # Start background scheduler (non-blocking)
    _scheduler = _start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    if _scheduler:
        _scheduler.shutdown(wait=False)


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="127.0.0.1",
        port=int(os.getenv("APP_PORT", "8000")),
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
