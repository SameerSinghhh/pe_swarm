# PE Value Creation Platform

An AI-powered platform for private equity firms that ingests messy portfolio company financial data, runs comprehensive analysis, models forward projections, gathers competitive intelligence, and uses multi-agent AI to identify specific, dollar-sized value creation opportunities.

LLMs are used throughout the entire pipeline — not just for chat, but as core infrastructure for data transformation, document classification, schema normalization, code generation, market research synthesis, company profiling, and multi-agent value creation analysis.

## How LLMs Are Used (Deeply Integrated, Not Just a Wrapper)

### 1. Data Ingestion — LLM as Data Engineer
When a messy financial file is uploaded (QuickBooks export with junk header rows, a manufacturing Excel with merged cells, a PDF board pack), the system uses **Claude with structured tool-use** to:
- **Classify the document type** from 8 possible schemas by analyzing column names and sample data (heuristic-first, Claude fallback for ambiguous cases)
- **Normalize non-standard formats** — Claude receives a 7-row preview + column names and returns a JSON column mapping (source field → target schema field), handling: different naming conventions, multi-column aggregation (COGS = Materials + Labor + Overhead), $000s multiplier detection, date format parsing
- **Code-generation fallback** — When standard mapping fails, Claude writes a custom `transform(df)` Python function that gets executed in a sandboxed environment (restricted builtins, only pandas/numpy available, 30-second timeout). This handles truly weird formats that no generic mapper can parse.

### 2. Company Profiling — LLM as Industry Analyst
Before any research happens, Claude analyzes the company's financial metrics and determines:
- What the company actually does (specific sub-sector, not just "SaaS")
- Revenue scale bracket and business model
- 5 real comparable public companies (with ticker symbols and reasoning)
- 5 targeted research queries specific to this company's niche
- Key competitive factors

This means the downstream research is targeted, not generic.

### 3. Market Research — LLM + Perplexity for Deep Intelligence
The research pipeline combines:
- **Perplexity API** (search + AI synthesis) for real-time web research with citations
- **yfinance** for live public company financials (peer margins, growth, multiples)
- **Claude** for gap analysis synthesis — connecting the company's metrics to peer benchmarks and producing a strategic narrative

### 4. Multi-Agent Value Creation — LLMs as Specialist PE Analysts
Four Claude-powered agents run in parallel (ThreadPoolExecutor), each with a different analytical role:

| Agent | What It Does | API Calls |
|-------|-------------|-----------|
| **Financial Agent** | Analyzes margin gaps, cost inefficiencies, working capital opportunities. Sizes each in dollars using LTM revenue. | 1 Claude call |
| **AI Transform Agent** | Systematically researches AI tools for every department (AP automation, sales intelligence, customer support, HR, FP&A, marketing). Identifies product AI features to build, AI-native competitor threats, and proprietary AI opportunities. | 12 Perplexity searches + 1 Claude synthesis |
| **Strategic Agent** | Evaluates exit positioning, key risks with probability/impact, growth vs profitability tradeoffs. | 1 Claude call |
| **Synthesis Agent** | Takes all 3 specialist outputs, resolves conflicts, deduplicates, ranks by impact/effort, writes executive summary. | 1 Claude call |

Every recommendation is a `SizedInitiative` with: name, category, description, annual EBITDA impact ($), implementation cost ($), timeline, confidence level, and specific tools/tactics.

### 5. Conversational AI Analyst — LLM with Real Tool Use
The chat agent uses Claude's tool-use capability to call real analysis functions:
- `get_current_metrics` — pulls from the 240-tested analysis engine
- `run_scenario` — actually re-runs the projection model with modified assumptions
- `search_market` — calls Perplexity for real-time external data
- `get_peer_comparison` — fetches live peer financials from yfinance

The agent never makes up numbers — every response is grounded in a tool call to a verified function.

## Architecture

```
Upload (CSV/Excel/PDF)
    │
    ▼
Data Ingestion (Claude for normalization + code-gen fallback)
    │
    ▼
8 Analysis Modules (deterministic math, 240 tests, 0 failures)
    │  EBITDA Bridge · Variance · Margins · Working Capital
    │  FCF · Revenue Analytics · LTM/Rule of 40 · Trend Detection
    │
    ▼
Assumption-Driven Modeling (auto-suggested from history)
    │  P&L + Balance Sheet + Cash Flow projections
    │  IRR · MOIC · Sensitivity tables · Scenarios
    │
    ▼
External Research (Perplexity + yfinance + Claude synthesis)
    │  Peer benchmarking · Gap analysis · Industry context
    │
    ▼
Multi-Agent Value Creation (4 parallel Claude agents)
    │  Financial · AI Transformation · Strategic · Synthesis
    │
    ▼
Output: Prioritized value creation plan with sized EBITDA impact
        + 10-tab formatted Excel workbook
```

## What's Built

### Data Ingestion
- 8 document type schemas (P&L, Balance Sheet, Cash Flow, Trial Balance, Working Capital, Revenue Detail, Cost Detail, KPI)
- CSV, Excel (multi-sheet), PDF support
- AI normalization via Claude for non-standard formats
- Code-generation fallback with sandboxed execution
- Data profiling with quality scoring (0-100)
- Full audit trail of every transformation
- 14 test files across all types and formats

### Analysis Engine (240 tests, 0 failures)
- EBITDA Bridge (MoM, vs Budget, vs Prior Year) with verification
- Three-way Variance Analysis on every P&L line item
- All margin percentages and growth rates (MoM, YoY)
- Working Capital metrics (DSO/DPO/DIO/CCC, AR aging)
- Free Cash Flow, cash conversion, leverage ratios
- Revenue concentration (HHI), price/volume/mix decomposition
- LTM rollups and Rule of 40
- Trend detection (consecutive decline, margin compression, anomalies)
- 10-tab formatted Excel export

### Forward Modeling
- Auto-suggestion engine (reads historical data, proposes assumption defaults)
- P&L + Balance Sheet + Cash Flow projections month by month
- Scenario modeling (Base/Upside/Downside)
- Returns calculator (IRR, MOIC)
- Sensitivity tables
- Initiative ramp modeling with confidence weighting

### External Research
- Claude-powered company profiling (understands the business, suggests real comps)
- yfinance peer financials (live margins, growth, multiples)
- Perplexity API for industry research with citations
- Static industry benchmarks by sector
- Gap analysis (company vs peer median, sized in dollars)

### AI Value Creation Agents
- 4-agent parallel system (Financial, AI Transform, Strategic, Synthesis)
- AI Transform agent makes 12 targeted Perplexity searches per run
- Every recommendation sized with dollar EBITDA impact
- Conflict resolution between agents
- Prioritized initiative ranking by impact/effort

## Quick Start

```bash
pip install anthropic pandas streamlit python-dotenv openpyxl pdfplumber yfinance

# Set API keys
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "PERPLEXITY_API_KEY=pplx-..." >> .env

# Web UI
streamlit run app.py

# CLI
python main.py
python main.py data/test/quickbooks_export.csv --company "Acme Corp"
```

## Project Structure

```
pe_swarm/
├── core/               Data ingestion pipeline (8 schemas, AI normalization)
├── analysis/           Deterministic analysis engine (240 tests)
├── modeling/           Assumption-driven projections (P&L + BS + CF)
├── research/           External data (Perplexity + yfinance + Claude)
├── value_creation/     Multi-agent value creation (4 parallel agents)
├── chat/               Conversational AI with tool-use
├── tests/              240 tests, 0 failures
├── data/test/          14 test files across all formats
├── app.py              Streamlit UI
└── main.py             CLI
```

## Tech Stack

- **Claude API (Anthropic)** — Document classification, schema normalization, code-gen fallback, company profiling, research synthesis, 4 value creation agents, conversational analyst with tool-use
- **Perplexity API** — Real-time web research with citations (industry trends, competitor intelligence, AI tool research)
- **yfinance** — Live public company financials for peer benchmarking
- **Python/pandas** — All deterministic financial math
- **Streamlit** — Web UI
- **openpyxl** — Formatted Excel workbook generation
- **pdfplumber** — PDF table extraction
