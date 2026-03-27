# PE Value Creation Platform

## Vision

A platform that replicates and accelerates the entire PE value creation analytical workflow.
PE firms upload messy financial data → the system ingests, normalizes, analyzes, and ultimately
identifies where value needs to be created — faster and more thoroughly than a team of analysts.

## Current State: Data Ingestion (COMPLETE)

Universal financial data ingestion that auto-detects and normalizes any financial document.

## Next Step: Analysis Engine (IN PROGRESS)

Build all the deterministic math that PE analysts do monthly. Pure math, no AI, 100% accurate.
This is the foundation that future AI agents will reason on top of.

## Future Steps (NOT YET STARTED)

- **AI Agent Swarms**: Multiple agents analyzing the same data from different angles (Revenue Agent,
  Margin Agent, Working Capital Agent, AI Transformation Agent) that argue with each other and
  synthesize into a prioritized value creation plan
- **AI Commentary**: PE analyst-style narrative on findings
- **Board Deck Generation**: Automated monthly reporting packages
- **Portfolio View**: Cross-company analysis across the entire portfolio

---

## Architecture

```
pe_swarm/
├── core/
│   ├── ingest.py          ← Universal ingestion orchestrator
│   ├── classify.py        ← Document type classification (heuristic + AI)
│   ├── registry.py        ← Schema registry (auto-discovery)
│   ├── readers.py         ← File reading (CSV/Excel/PDF)
│   ├── normalize.py       ← AI normalization engine (Claude API)
│   ├── validate.py        ← Validation with audit trail
│   ├── cleaning.py        ← Shared utilities
│   ├── profiler.py        ← Data profiling + quality scoring
│   ├── fallback.py        ← AI code-gen fallback (sandboxed)
│   ├── result.py          ← NormalizedResult dataclass
│   └── schemas/           ← One file per document type
│       ├── base.py                ← Abstract DocumentSchema
│       ├── income_statement.py
│       ├── balance_sheet.py
│       ├── cash_flow.py
│       ├── trial_balance.py
│       ├── revenue_detail.py
│       ├── cost_detail.py
│       ├── working_capital.py
│       └── kpi_operational.py
├── data/
│   ├── sample_pl.csv
│   └── test/              ← 14 test files across all types and formats
├── app.py                 ← Streamlit UI (before/after view)
├── main.py                ← CLI entry point
├── requirements.txt
└── .env                   ← ANTHROPIC_API_KEY goes here
```

## Ingestion Pipeline

```
File (CSV/Excel/PDF)
  → read_file()           Read raw data, handle encoding, select Excel sheet
  → classify_document()   Auto-detect document type (8 types supported)
  → profile_raw()         Column stats, temporal coverage, anomaly detection
  → normalize             Fast path (no AI) or AI mapping or code-gen fallback
  → validate()            Accounting identities, temporal checks, reasonableness
  → profile_normalized()  Quality score (completeness/consistency/coverage/reasonableness)
  → NormalizedResult      Clean DataFrame + quality_score + audit_trail
```

## 8 Supported Document Types

1. **Income Statement / P&L** — Revenue, COGS, OpEx, EBITDA. Validation: GP = Rev - COGS
2. **Balance Sheet** — Assets, liabilities, equity. Validation: A = L + E
3. **Cash Flow Statement** — Operating, investing, financing. Validation: net change = ops + inv + fin
4. **Trial Balance / GL** — Account-level debits and credits. Validation: debits = credits
5. **Revenue Detail** — By customer, product, segment, geography
6. **Cost Detail** — By department, vendor, category
7. **Working Capital / AR-AP Aging** — Aging buckets, DSO/DPO/DIO
8. **KPI / Operational** — SaaS metrics, manufacturing KPIs, unit economics

## Analysis Engine (Next to Build)

All deterministic — pure math on ingested data, no AI needed, 100% accurate:

1. **EBITDA Bridge** — MoM, vs Budget, vs PY with price/volume/mix decomposition
2. **Variance Analysis** — Three-way (actual vs budget vs PY) on every line item
3. **Working Capital Analytics** — DSO/DPO/DIO trending, cash conversion cycle, cash impact
4. **FCF Analysis** — Free cash flow calculation, cash conversion ratio
5. **Revenue Analytics** — Concentration, cohort retention, NRR/GRR
6. **Cost Analytics** — Cost-out tracking, headcount productivity
7. **Trend Detection** — Automatic flagging of inflection points, threshold crossings
8. **KPI Scoring** — Traffic light status against targets

## Key Design Principles

- Each document type is a self-registering schema class
- Heuristic classification first, AI only when ambiguous
- Fast path skips AI for already-standardized files
- Derive fields rather than require all (GP = Rev - COGS)
- Full audit trail of every transformation
- Quality scoring so downstream agents know data trustworthiness
- Code-gen fallback for truly weird files (Claude writes custom Python)
- All analysis math is deterministic — no guessing, no assumptions

## Running

```bash
# CLI
python main.py                                    # Sample P&L
python main.py data/test/quickbooks_export.csv    # Any file

# UI
streamlit run app.py

# Dependencies
pip install anthropic pandas streamlit python-dotenv openpyxl pdfplumber
```

## Environment

```
ANTHROPIC_API_KEY=sk-ant-...   # Required for AI normalization of messy files
```

Note: Clean/standardized files work without an API key (fast path).
