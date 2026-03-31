"""
FastAPI backend. Thin wrapper around the existing engine.
All computation happens in the engine modules — this just exposes them as REST.
"""

import io
import json
import os
import tempfile
import uuid
from datetime import date
from dataclasses import asdict

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from core.ingest import ingest_file
from core.result import NormalizedResult
from analysis.engine import run_analysis
from analysis.excel_export import export_to_excel
from modeling.types import (
    AssumptionSet, RevenueAssumptions, CostAssumptions, CostLineAssumption,
    WorkingCapitalAssumptions, ExitAssumptions,
)
from modeling.auto_suggest import suggest_assumptions
from modeling.engine import run_model
from chat.agent import chat as agent_chat
from chat.tools import execute_tool


import json as json_module
import math

class NaNSafeEncoder(json_module.JSONEncoder):
    """JSON encoder that converts NaN/Inf to null."""
    def default(self, obj):
        import numpy as np
        if isinstance(obj, (np.floating,)):
            val = float(obj)
            if math.isnan(val) or math.isinf(val):
                return None
            return val
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

    def encode(self, o):
        text = super().encode(o)
        # Belt and suspenders: replace any remaining NaN
        text = text.replace(': NaN', ': null').replace(':NaN', ':null')
        return text


def _json_response(data):
    """Return a response with NaN-safe JSON encoding."""
    text = json_module.dumps(data, cls=NaNSafeEncoder)
    return JSONResponse(content=json_module.loads(text))


app = FastAPI(title="PE Value Creation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session store ──
sessions: dict[str, dict] = {}

DEMO_COMPANIES = {
    "meridian": {
        "name": "Meridian Software",
        "sector": "B2B SaaS",
        "files": {
            "P&L": "data/sample_pl.csv",
            "Balance Sheet": "data/test/balance_sheet_clean.csv",
            "Cash Flow": "data/test/cash_flow_clean.csv",
            "Working Capital": "data/test/working_capital_clean.csv",
            "Revenue Detail": "data/test/revenue_detail_clean.csv",
            "KPIs": "data/test/kpi_operational_clean.csv",
        },
    },
    "atlas": {
        "name": "Atlas Manufacturing",
        "sector": "Manufacturing",
        "files": {"P&L": "data/test/manufacturing_pl.xlsx"},
    },
    "acme": {
        "name": "Acme Corp",
        "sector": "B2B SaaS",
        "files": {"P&L": "data/test/quickbooks_export.csv"},
    },
}


def _safe_json(data):
    """Return a JSONResponse that handles NaN/Inf values."""
    import json
    text = json.dumps(data, default=str, allow_nan=False)
    return JSONResponse(content=json.loads(text))


def _serialize(obj):
    """Serialize dataclass/complex objects to JSON-safe dicts."""
    import math
    if obj is None:
        return None
    import numpy as np
    if isinstance(obj, (float, np.floating)):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (int, str, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if hasattr(obj, '__dataclass_fields__'):
        d = {}
        for field_name in obj.__dataclass_fields__:
            val = getattr(obj, field_name)
            if field_name.startswith('_'):
                continue
            import pandas as pd
            if isinstance(val, pd.DataFrame):
                # Replace NaN with None before converting
                d[field_name] = val.where(pd.notna(val), None).to_dict(orient="records")
            else:
                d[field_name] = _serialize(val)
        return d
    if hasattr(obj, 'value'):  # Enum
        return obj.value
    return str(obj)


def _get_session(session_id: str) -> dict:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Load a company first.")
    return sessions[session_id]


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/demo/{company_key}")
async def load_demo(company_key: str):
    """Load a demo company. Returns session_id + full analysis."""
    if company_key not in DEMO_COMPANIES:
        raise HTTPException(status_code=404, detail=f"Demo company '{company_key}' not found")

    demo = DEMO_COMPANIES[company_key]
    ingested = {}

    for label, path in demo["files"].items():
        try:
            r = ingest_file(path, company_name=demo["name"], business_type=demo["sector"])
            ingested[r.doc_type] = r
        except Exception as e:
            pass

    if not ingested:
        raise HTTPException(status_code=500, detail="Failed to load demo data")

    # Auto-suggest + model
    suggested = suggest_assumptions(ingested)

    def _pct(item):
        for cl in suggested.costs.lines:
            if cl.line_item == item:
                return cl.pct_of_revenue or 0.0
        return 0.0

    assumptions = AssumptionSet(
        projection_months=12,
        revenue=RevenueAssumptions(method="growth_rate", growth_rate_pct=suggested.revenue.growth_rate_pct or 0),
        costs=CostAssumptions(lines=[
            CostLineAssumption("cogs", method="pct_of_revenue", pct_of_revenue=_pct("cogs")),
            CostLineAssumption("sales_marketing", method="pct_of_revenue", pct_of_revenue=_pct("sales_marketing")),
            CostLineAssumption("rd", method="pct_of_revenue", pct_of_revenue=_pct("rd")),
            CostLineAssumption("ga", method="pct_of_revenue", pct_of_revenue=_pct("ga")),
        ]),
        working_capital=WorkingCapitalAssumptions(
            target_dso=suggested.working_capital.target_dso or 40,
            target_dpo=suggested.working_capital.target_dpo or 30,
        ),
        capex=suggested.capex, debt=suggested.debt, tax=suggested.tax,
        exit_=ExitAssumptions(exit_year=5, exit_multiple=10.0, entry_equity=10_000_000),
    )

    model = run_model(ingested, assumptions)

    # Store session
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "company_name": demo["name"],
        "sector": demo["sector"],
        "ingested": ingested,
        "assumptions": assumptions,
        "model": model,
        "analysis": model.analysis,
        "research": None,
        "vc_plan": None,
        "chat_history": [],
    }

    return _json_response({
        "session_id": session_id,
        "company_name": demo["name"],
        "sector": demo["sector"],
        "analysis": _serialize(model.analysis),
        "assumptions": _serialize(assumptions),
        "returns": _serialize(model.returns) if model.returns else None,
    })


class ModelRequest(BaseModel):
    session_id: str
    revenue_growth_pct: Optional[float] = None
    cogs_pct: Optional[float] = None
    sm_pct: Optional[float] = None
    rd_pct: Optional[float] = None
    ga_pct: Optional[float] = None
    dso_target: Optional[float] = None
    dpo_target: Optional[float] = None
    exit_multiple: Optional[float] = None
    entry_equity_m: Optional[float] = None
    projection_months: Optional[int] = None


@app.post("/api/model")
async def update_model(req: ModelRequest):
    """Re-run model with updated assumptions."""
    session = _get_session(req.session_id)
    base = session["assumptions"]

    def _base_pct(item):
        for cl in base.costs.lines:
            if cl.line_item == item:
                return cl.pct_of_revenue or 0
        return 0

    new_assumptions = AssumptionSet(
        projection_months=req.projection_months or base.projection_months,
        revenue=RevenueAssumptions(
            method="growth_rate",
            growth_rate_pct=req.revenue_growth_pct if req.revenue_growth_pct is not None else base.revenue.growth_rate_pct or 0,
        ),
        costs=CostAssumptions(lines=[
            CostLineAssumption("cogs", method="pct_of_revenue", pct_of_revenue=req.cogs_pct if req.cogs_pct is not None else _base_pct("cogs")),
            CostLineAssumption("sales_marketing", method="pct_of_revenue", pct_of_revenue=req.sm_pct if req.sm_pct is not None else _base_pct("sales_marketing")),
            CostLineAssumption("rd", method="pct_of_revenue", pct_of_revenue=req.rd_pct if req.rd_pct is not None else _base_pct("rd")),
            CostLineAssumption("ga", method="pct_of_revenue", pct_of_revenue=req.ga_pct if req.ga_pct is not None else _base_pct("ga")),
        ]),
        working_capital=WorkingCapitalAssumptions(
            target_dso=req.dso_target if req.dso_target is not None else base.working_capital.target_dso,
            target_dpo=req.dpo_target if req.dpo_target is not None else base.working_capital.target_dpo,
        ),
        capex=base.capex, debt=base.debt, tax=base.tax,
        exit_=ExitAssumptions(
            exit_year=base.exit_.exit_year,
            exit_multiple=req.exit_multiple if req.exit_multiple is not None else base.exit_.exit_multiple,
            entry_equity=(req.entry_equity_m * 1e6) if req.entry_equity_m is not None else base.exit_.entry_equity,
        ),
    )

    model = run_model(session["ingested"], new_assumptions)
    session["assumptions"] = new_assumptions
    session["model"] = model
    session["analysis"] = model.analysis

    return _json_response({
        "analysis": _serialize(model.analysis),
        "assumptions": _serialize(new_assumptions),
        "returns": _serialize(model.returns) if model.returns else None,
    })


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Send a message to the AI analyst."""
    session = _get_session(req.session_id)

    context = {
        "analysis": session["analysis"],
        "ingested": session["ingested"],
        "assumptions": session["assumptions"],
        "model": session["model"],
        "research": session.get("research"),
        "company_name": session["company_name"],
        "sector": session["sector"],
    }

    response_text, updated_history = agent_chat(
        req.message,
        session["chat_history"],
        context,
    )

    session["chat_history"] = updated_history

    return {"response": response_text}


@app.post("/api/research")
async def research_endpoint(session_id: str):
    """Run market research."""
    session = _get_session(session_id)
    analysis = session["analysis"]

    company_metrics = {}
    if analysis.margins and analysis.margins.periods:
        m = analysis.margins.periods[-1]
        for k in ["gross_margin_pct", "ebitda_margin_pct", "sm_pct_revenue", "rd_pct_revenue", "ga_pct_revenue"]:
            v = getattr(m, k, None)
            if v is not None:
                company_metrics[k] = v
        if m.revenue_growth_yoy is not None:
            company_metrics["revenue_growth_yoy_pct"] = m.revenue_growth_yoy
    if analysis.ltm:
        company_metrics["ltm_revenue"] = analysis.ltm.ltm_revenue
        company_metrics["ltm_ebitda"] = analysis.ltm.ltm_ebitda

    from research.engine import run_research
    brief = run_research(session["company_name"], session["sector"], company_metrics)
    session["research"] = brief

    return _serialize(brief)


@app.post("/api/value-creation")
async def value_creation_endpoint(session_id: str):
    """Run AI value creation agents."""
    session = _get_session(session_id)

    from value_creation.engine import run_value_creation
    plan = run_value_creation(
        session["company_name"],
        session["sector"],
        session["analysis"],
        session.get("research"),
    )
    session["vc_plan"] = plan

    return _serialize(plan)


@app.get("/api/export/excel")
async def export_excel(session_id: str):
    """Download Excel workbook."""
    session = _get_session(session_id)

    buf = io.BytesIO()
    export_to_excel(
        session["analysis"],
        buf,
        ingested=session["model"].combined_data if session["model"] else session["ingested"],
        company_name=session["company_name"],
    )

    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{session["company_name"]}_{date.today()}.xlsx"'},
    )


@app.get("/api/companies")
async def list_companies():
    """List available demo companies."""
    return [
        {"key": k, "name": v["name"], "sector": v["sector"]}
        for k, v in DEMO_COMPANIES.items()
    ]


@app.post("/api/ingest")
async def ingest_endpoint(
    file: UploadFile = File(...),
    company_name: str = "",
    business_type: str = "",
    session_id: str = "",
):
    """Upload and ingest a financial file."""
    # Save to temp file
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = ingest_file(tmp_path, company_name=company_name, business_type=business_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.unlink(tmp_path)

    # If session exists, add to it
    if session_id and session_id in sessions:
        sessions[session_id]["ingested"][result.doc_type] = result
        # Re-run analysis
        model = run_model(sessions[session_id]["ingested"], sessions[session_id]["assumptions"])
        sessions[session_id]["model"] = model
        sessions[session_id]["analysis"] = model.analysis

    return {
        "doc_type": result.doc_type,
        "doc_type_name": result.doc_type_name,
        "rows": len(result.df),
        "quality_score": result.quality_score,
        "used_ai": result.used_ai,
    }
