# PE Value Creation Platform

Upload messy portfolio company financials. Get clean analysis, forward projections, competitive benchmarks, and a prioritized value creation plan with sized EBITDA impact.

## What It Does

**Ingest** — Drop any financial file (CSV, Excel, PDF). The system auto-detects the document type, normalizes messy formats, and validates the data. Handles QuickBooks exports, multi-sheet workbooks, PDFs, files in $000s, wrong headers.

**Analyze** — EBITDA bridges, variance analysis, margins, working capital, FCF, revenue concentration, trend detection. All math is deterministic and tested (240 tests, 0 failures).

**Model** — Auto-suggests assumptions from historical data. Projects P&L, balance sheet, and cash flow forward. Scenarios, sensitivity tables, IRR/MOIC.

**Research** — Pulls live peer financials, industry benchmarks, and competitive intelligence. Gap analysis shows exactly where the company is above or below peers.

**Find Value** — AI agents analyze the financials and research to produce a ranked list of initiatives with dollar-sized EBITDA impact, specific tools to implement, and confidence levels.

## Quick Start

```bash
pip install anthropic pandas streamlit python-dotenv openpyxl pdfplumber yfinance
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "PERPLEXITY_API_KEY=pplx-..." >> .env
streamlit run app.py
```

## Structure

```
core/               Data ingestion (8 document types, AI normalization)
analysis/           Financial analysis engine (240 tests)
modeling/           Projections, scenarios, returns
research/           Peer benchmarks, market intelligence
value_creation/     AI agents that identify EBITDA opportunities
chat/               Conversational analyst with tool use
```

## Tech

Python, Claude API, Perplexity API, yfinance, pandas, Streamlit
