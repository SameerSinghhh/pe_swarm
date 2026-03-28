# PE Value Creation Platform

## Vision

The Bloomberg of private equity. A platform so essential that any PE firm without it
is making decisions blind while their competitors aren't.

Each portfolio company gets its own AI analyst that knows all the financials, remembers
every conversation, gets smarter each month, and helps the operating partner find value
creation opportunities they'd otherwise miss.

## The Product (North Star)

An operating partner opens "Meridian Software" and chats:

- "Why did EBITDA margin drop in February?" → AI already has the variance analysis, answers instantly
- "What if we raised prices 10% on SMB?" → AI models the math from revenue detail data
- "Pipeline is soft for Q3" → AI stores the context, flags risk in next month's analysis

It's not a dashboard. It's a thinking partner for each portfolio company.

## What Makes This a Must-Have

1. Sees every pattern across every metric simultaneously (humans check 10, miss the 11th)
2. Cross-portfolio pattern recognition ("this margin pattern preceded revenue decline at Atlas too")
3. Institutional memory (never loses knowledge when analysts leave)
4. Speed of iteration (50 scenarios in the time it takes an analyst to model 3)

---

## Current State

### Phase 1: Data Ingestion ✅ COMPLETE
Universal ingestion: any file format (CSV/Excel/PDF), any document type, auto-classified,
normalized, validated, quality-scored with full audit trail.
- 8 document types (P&L, Balance Sheet, Cash Flow, Trial Balance, Working Capital, Revenue Detail, Cost Detail, KPI)
- AI normalization for messy files, fast path for clean files
- Code-gen fallback for truly weird files
- 14 test files, all passing

### Phase 2: Analysis Engine ✅ COMPLETE
All deterministic math PE analysts do monthly. Zero assumptions, 100% accurate.
- EBITDA Bridge (MoM, Budget, Prior Year) with verification
- Variance Analysis (three-way on every P&L line, favorability)
- Margins & Growth (all ratios, MoM/YoY growth)
- Working Capital (DSO/DPO/DIO/CCC, WC changes, AR aging)
- FCF & Leverage (free cash flow, cash conversion, net debt/EBITDA)
- Revenue Analytics (concentration, HHI, price/volume/mix decomposition)
- LTM Rollups (trailing 12 months, Rule of 40 for SaaS)
- Trend Detection (consecutive decline, margin compression, anomalies)
- Excel Export (10-tab formatted workbook, analyst-ready)
- 240 tests, 0 failures

---

## Roadmap

### Phase 3: Assumption-Driven Analysis ← NEXT
The analyst inputs their assumptions, the system does all the math instantly.
This is where the tool goes from "reporting what happened" to "modeling what could happen."
- Forecasting framework (growth rates, margin targets → projected P&L)
- Scenario modeling (base/upside/downside with toggleable inputs)
- Initiative sizing ("if DSO improves 5 days → $X freed")
- Sensitivity tables (what if growth is 5% vs 10% vs 15%)
- LBO refresh (exit multiple + timing → IRR/MOIC)

### Phase 4: External Data
Pull in context the company's data alone can't provide:
- Peer benchmarking (public comp margins, growth, multiples)
- Industry benchmarks (median DSO, margin ranges by sector)
- Market/macro context (rates, industry trends, news)
- Comparable transactions (recent deal multiples)

### Phase 5: Per-Company AI Analyst (THE PRODUCT)
Each portfolio company gets its own AI that:
- Has all financial data loaded + all analysis pre-computed
- Has external context (industry, comps, macro)
- Remembers every conversation with the operating partner
- Gets smarter every month as new data comes in
- Operating partner chats with it naturally to explore the data

Implementation approach:
- Agent swarms (Revenue Agent, Margin Agent, WC Agent, AI Transformation Agent)
- Each analyzes from a different angle, they argue and synthesize
- Human-in-the-loop: operating partner adds insider context via chat
- The AI + human together find value creation opportunities
- Prioritized value creation plan with sized EBITDA impact

### Phase 6: Portfolio Intelligence
Cross-company analysis across the entire fund:
- Pattern recognition ("this happened at Company A, now happening at Company B")
- Institutional memory (what playbooks worked before)
- Portfolio-level dashboards and reporting
- LP reporting automation
- Board deck generation

---

## Architecture

```
pe_swarm/
├── core/                    ← Data ingestion
│   ├── ingest.py            Universal orchestrator
│   ├── classify.py          Document type classification
│   ├── normalize.py         AI normalization (Claude)
│   ├── validate.py          Validation + audit trail
│   ├── profiler.py          Quality scoring
│   ├── fallback.py          AI code-gen fallback
│   ├── readers.py           CSV/Excel/PDF reading
│   ├── cleaning.py          Shared utilities
│   ├── registry.py          Schema registry
│   ├── result.py            NormalizedResult dataclass
│   └── schemas/             8 document type schemas
│
├── analysis/                ← Analysis engine
│   ├── types.py             Result dataclasses + enums
│   ├── utils.py             safe_div, favorability helpers
│   ├── ebitda_bridge.py     EBITDA bridges (MoM, Budget, PY)
│   ├── variance.py          Three-way variance
│   ├── margins.py           All margins and growth rates
│   ├── working_capital.py   DSO/DPO/DIO/CCC
│   ├── fcf.py               FCF, cash conversion, leverage
│   ├── revenue_analytics.py Concentration, price/volume/mix
│   ├── ltm.py               LTM rollups, Rule of 40
│   ├── trends.py            Anomaly detection
│   ├── excel_export.py      10-tab formatted Excel workbook
│   └── engine.py            Orchestrator
│
├── tests/                   ← 240 tests, 0 failures
│   ├── test_all.py          179 analysis math tests
│   └── test_excel.py        61 Excel verification tests
│
├── data/test/               ← 14 test files
├── app.py                   ← Streamlit UI
├── main.py                  ← CLI
├── requirements.txt
└── .env
```

## Key Principles

- All backward-looking analysis is deterministic — no assumptions, no AI, just math
- Forward-looking analysis separates math (exact) from assumptions (analyst inputs)
- The AI layer reasons ON TOP of verified math — never replaces it
- Human-in-the-loop for insider context that data can't capture
- Excel is the primary output format (analysts live in Excel)
- Every calculation is tested (240 tests, 0 failures)
- Each portfolio company is its own context — data, conversations, history

## Running

```bash
streamlit run app.py          # Web UI
python main.py                # CLI
```

## Dependencies

anthropic, pandas, streamlit, python-dotenv, openpyxl, pdfplumber
