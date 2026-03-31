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
- "What if we cut 3 sales reps?" → AI recalculates projections, shows net EBITDA impact
- "Where should we implement AI?" → AI has already researched tools, sizes the ROI

It's not a dashboard. It's a thinking partner for each portfolio company.

## What Makes This a Must-Have

1. Sees every pattern across every metric simultaneously (humans check 10, miss the 11th)
2. Cross-portfolio pattern recognition ("this margin pattern preceded revenue decline at Atlas too")
3. Institutional memory (never loses knowledge when analysts leave)
4. Speed of iteration (50 scenarios in the time it takes an analyst to model 3)
5. The AI calls REAL math functions — never hallucates numbers, never makes up calculations

## Key Principles

- AI reasons ON TOP of verified math — it calls tested functions, never does math itself
- 240 tests prove every calculation is correct
- When the AI doesn't know something, it asks — never makes things up
- Complete data isolation per PE firm — NEVER share one firm's data with another
- Each portfolio company's data, conversations, and context are completely separate
- The conversational agent has persistent memory per company
- Human-in-the-loop: the operating partner adds context the data can't capture

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

### Phase 3: Assumption-Driven Analysis ✅ COMPLETE
- Forecasting framework (growth rates, margin targets → projected P&L)
- Scenario modeling (base/upside/downside with toggleable inputs)
- Auto-suggestion engine (reads historical data, proposes defaults)
- BS/CF projections (balance sheet + cash flow projected month by month)
- Returns calculator (IRR, MOIC from projected financials)
- Sensitivity tables

### Phase 4: External Data ✅ COMPLETE
- Peer benchmarking via yfinance (public comp margins, growth, multiples)
- Industry benchmarks by sector (static reference data)
- Perplexity API for industry research and competitor intelligence
- Claude-powered company profiling (understands the business, suggests real comps)
- Gap analysis (company vs peer median, sized in dollars)

### Phase 5: AI Value Creation Agents ✅ COMPLETE
- Financial Agent: finds margin gaps, cost inefficiencies, WC opportunities
- AI Transform Agent: 12 Perplexity queries researching specific AI tools by department
- Strategic Agent: exit positioning, risks, growth vs profitability
- Synthesis Agent: resolves conflicts, ranks initiatives, writes executive summary
- Produces prioritized value creation plan with sized EBITDA impact

---

## Next: Conversational AI Analyst ← BUILDING NOW

The per-company chat interface where the operating partner talks to an AI that:
- Has ALL financial data loaded + analysis pre-computed
- Has external context (industry, comps, macro)
- Remembers every conversation
- Can run scenarios in real-time ("what if we cut DSO by 5 days?")
- Can modify projections when asked
- Asks questions when it needs more context — never makes things up
- Gets smarter every month as new data comes in

## Future

### Cross-Portfolio Intelligence (within one PE firm only)
- Pattern recognition across the firm's own portfolio companies
- "This happened at Company A, now showing up at Company B"
- Outcome tracking: which recommendations actually worked?
- Institutional memory: what playbooks succeeded before?
- NEVER share data between different PE firms

### Product Maturity
- Board deck generation
- LP reporting automation
- Integration with ERPs (NetSuite, QuickBooks API)
- Mobile interface
- Multi-user with role-based access

---

## Architecture

```
pe_swarm/
├── core/                    ← Data ingestion (Phase 1)
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
├── analysis/                ← Analysis engine (Phase 2)
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
├── modeling/                ← Assumption-driven modeling (Phase 3)
│   ├── types.py             Assumption dataclasses
│   ├── projections.py       P&L + BS + CF projections
│   ├── initiatives.py       Initiative ramp + confidence
│   ├── returns.py           IRR, MOIC calculator
│   ├── scenarios.py         Scenario manager
│   ├── sensitivity.py       2-way sensitivity tables
│   ├── auto_suggest.py      Auto-generate assumptions from history
│   └── engine.py            Modeling orchestrator
│
├── research/                ← External data (Phase 4)
│   ├── types.py             Research result dataclasses
│   ├── company_profile.py   Claude-powered company understanding
│   ├── peers.py             yfinance peer financials
│   ├── benchmarks.py        Static industry benchmarks
│   ├── macro.py             Market data
│   ├── perplexity.py        Perplexity API wrapper
│   ├── synthesize.py        Gap analysis + Claude synthesis
│   └── engine.py            Research orchestrator
│
├── value_creation/          ← AI value creation agents (Phase 5)
│   ├── types.py             SizedInitiative, ValueCreationPlan
│   ├── context.py           Serializes data for agent prompts
│   ├── financial_agent.py   Finds EBITDA improvement opportunities
│   ├── ai_transform_agent.py  Researches AI tools (12 Perplexity queries)
│   ├── strategic_agent.py   Exit positioning + risks
│   ├── synthesis_agent.py   Merges + ranks all initiatives
│   └── engine.py            Parallel agent orchestrator
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

## Running

```bash
streamlit run app.py          # Web UI
python main.py                # CLI
```

## Dependencies

anthropic, pandas, streamlit, python-dotenv, openpyxl, pdfplumber, yfinance
