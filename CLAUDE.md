# PE Value Creation Platform

## Vision

A platform that replicates the entire PE value creation analytical workflow.
Upload messy financial data → ingest → normalize → analyze → gather external context →
identify where value needs to be created. Faster and more thorough than a team of analysts.

## Roadmap

### Phase 1: Data Ingestion ✅ COMPLETE
Universal ingestion: any file format, any document type, auto-classified, normalized, validated.
8 document types, 3 formats (CSV/Excel/PDF), quality scoring, audit trail.

### Phase 2A: Backward-Looking Analysis ✅ COMPLETE
Deterministic math on ingested data. No assumptions, 100% accurate.
EBITDA bridges, variance analysis, margins, working capital, FCF, revenue analytics, trends.
238 tests, 0 failures. Excel export with 9 formatted tabs.

### Phase 2B: Remaining Analysis ← NEXT
Still exact math on existing data:
- Trial balance / GL analysis (vendor spend, cost center trends, account-level)
- Cost detail analysis (cost-out tracking, headcount productivity, dept margins)
- Segment P&Ls (build per-product/segment P&Ls from revenue + cost detail)
- LTM rollups (trailing 12-month revenue, EBITDA, FCF)
- Operating leverage (cost growth vs revenue growth)
- Rule of 40 (SaaS: growth % + margin %)
- Cross-document ratios (asset turnover, ROIC, working capital as % of revenue)

### Phase 3: Assumption-Driven Analysis ← AFTER 2B
Analyst inputs assumptions, system does all the math:
- Forecasting framework (growth rates, margin targets → projected P&L)
- Scenario modeling (base/upside/downside with toggleable inputs)
- Initiative sizing ("if DSO improves 5 days → $X freed" — math exact, 5 days is the assumption)
- LBO refresh (exit multiple + timing → IRR/MOIC)
- Sensitivity tables (what happens if growth is 5% vs 10% vs 15%)

### Phase 4: External Data ← AFTER 3
Pull in context the company's data alone can't provide:
- Peer benchmarking (public comp data: margins, growth, multiples)
- Industry benchmarks (median DSO, margin ranges by sector)
- Market/macro context (rates, industry trends, relevant news)
- Comparable transactions (recent deal multiples)

### Phase 5: AI Commentary + Agent Swarms ← AFTER 4
Only after we have THE FULL PICTURE (all analysis + assumptions + external data):
- Revenue Agent, Margin Agent, Working Capital Agent, AI Transformation Agent
- Each analyzes from a different angle, they argue and synthesize
- Prioritized value creation plan with sized EBITDA impact
- PE analyst-style narrative on every finding
- Board deck generation

---

## Architecture

```
pe_swarm/
├── core/                    ← Data ingestion (Phase 1)
│   ├── ingest.py            Universal orchestrator
│   ├── classify.py          Document type classification
│   ├── registry.py          Schema registry
│   ├── readers.py           File reading (CSV/Excel/PDF)
│   ├── normalize.py         AI normalization (Claude)
│   ├── validate.py          Validation + audit trail
│   ├── cleaning.py          Shared utilities
│   ├── profiler.py          Data profiling + quality scoring
│   ├── fallback.py          AI code-gen fallback
│   ├── result.py            NormalizedResult dataclass
│   └── schemas/             8 document type schemas
│
├── analysis/                ← Analysis engine (Phase 2)
│   ├── types.py             Result dataclasses + enums
│   ├── utils.py             safe_div, favorability, period helpers
│   ├── ebitda_bridge.py     EBITDA bridges (MoM, Budget, PY)
│   ├── variance.py          Three-way variance on every P&L line
│   ├── margins.py           All margin % and growth rates
│   ├── working_capital.py   DSO/DPO/DIO/CCC, WC changes, AR aging
│   ├── fcf.py               FCF, cash conversion, leverage
│   ├── revenue_analytics.py Concentration, price/volume/mix, KPI trends
│   ├── trends.py            Auto-flag anomalies, declines, compression
│   ├── excel_export.py      9-tab formatted Excel workbook
│   └── engine.py            Orchestrator
│
├── tests/                   ← 238 tests, 0 failures
│   ├── test_all.py          179 analysis math tests
│   └── test_excel.py        59 Excel verification tests
│
├── data/                    ← Test data
│   ├── sample_pl.csv
│   └── test/                14 test files across all types
│
├── app.py                   ← Streamlit UI
├── main.py                  ← CLI
├── requirements.txt
└── .env
```

## Key Principles

- All backward-looking analysis is deterministic math — no assumptions, no AI
- Forward-looking analysis clearly separates math (exact) from assumptions (analyst inputs)
- External data supplements but never replaces the company's own data
- Commentary and value creation spotting only happens after the full picture is assembled
- Every calculation is tested and verified (238 tests)
- Excel output is the primary deliverable (analysts live in Excel)

## Running

```bash
streamlit run app.py          # Web UI
python main.py                # CLI
```

## Dependencies

anthropic, pandas, streamlit, python-dotenv, openpyxl, pdfplumber
