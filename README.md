# PE Value Creation Platform

Upload messy portfolio company financials. Get clean analysis, forward projections, competitive benchmarks, and a prioritized value creation plan with sized EBITDA impact.

Built around an agentic AI system where specialized agents work together across the full pipeline — one handles data ingestion and normalization (turning any messy file into clean structured data), another runs financial analysis and forward modeling, a research agent pulls live competitive intelligence and peer benchmarks, and a team of value creation agents (financial, AI transformation, strategic) independently analyze the business from different angles before a synthesis agent merges their findings into a single ranked plan. The agents call deterministic math functions for all calculations (never hallucinating numbers) and use web research APIs for external context.

## What It Does

**Ingest** — Drop any financial file (CSV, Excel, PDF). AI agents auto-detect the document type, normalize messy formats, and validate the data. Handles QuickBooks exports, multi-sheet workbooks, PDFs, files in $000s, wrong headers. Falls back to AI code generation for truly weird formats.

**Analyze** — EBITDA bridges, variance analysis, margins, working capital, FCF, revenue concentration, trend detection. All math is deterministic and tested (240 tests, 0 failures).

**Model** — Auto-suggests assumptions from historical trends. Projects P&L, balance sheet, and cash flow forward. Scenarios, sensitivity tables, IRR/MOIC.

**Research** — Agents pull live peer financials, run targeted industry searches, and benchmark the company against comparable public companies. Gap analysis shows exactly where the company stands vs peers.

**Find Value** — A team of AI agents analyzes the financials, market research, and competitive landscape in parallel. Each agent specializes in a different lens (financial optimization, AI transformation opportunities, strategic positioning). A synthesis agent resolves conflicts between them and produces a prioritized plan with dollar-sized EBITDA impact and specific implementation recommendations.

## Quick Start

```bash
pip install anthropic pandas streamlit python-dotenv openpyxl pdfplumber yfinance
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "PERPLEXITY_API_KEY=pplx-..." >> .env
streamlit run app.py
```

## Structure

```
core/               Data ingestion (8 document types, AI normalization, code-gen fallback)
analysis/           Financial analysis engine (240 tests, 0 failures)
modeling/           Projections, scenarios, returns, auto-suggested assumptions
research/           Peer benchmarks, competitive intelligence, market research
value_creation/     Agentic value creation (4 specialized agents working in parallel)
chat/               Conversational analyst with tool use
```

## Tech

Python, Claude API (Anthropic), Perplexity API, yfinance, pandas, Streamlit
