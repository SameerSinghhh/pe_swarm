# PE Value Creation Platform

An AI-powered platform that replicates the PE value creation analytical workflow. Upload messy financial data from any portfolio company — the system ingests, normalizes, and analyzes it automatically.

## What It Does

**Today:** Universal financial data ingestion. Throw any financial file at it (CSV, Excel, PDF) and get clean, structured, validated output. Auto-detects 8 document types. Handles messy real-world data — QuickBooks exports, multi-sheet Excel workbooks, PDFs, files in $000s, wrong headers, you name it.

**Next:** Automated analysis engine — EBITDA bridges, variance analysis, working capital optimization, trend detection. All the math PE analysts do monthly, automated.

**Future:** AI agent swarms that analyze the data from multiple angles and identify where value needs to be created.

## Quick Start

```bash
# Install
pip install anthropic pandas streamlit python-dotenv openpyxl pdfplumber

# Set API key (needed for messy files only)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# CLI
python main.py                                    # Sample P&L data
python main.py data/test/quickbooks_export.csv    # Any financial file

# Web UI
streamlit run app.py
```

## Supported Document Types

| Type | Example |
|------|---------|
| Income Statement / P&L | Monthly P&L, QuickBooks export, board pack |
| Balance Sheet | Quarterly balance sheet, PDF report |
| Cash Flow Statement | Monthly cash flow |
| Trial Balance / GL | General ledger export, chart of accounts |
| Revenue Detail | Revenue by customer, product, segment |
| Cost Detail | Expenses by department, vendor |
| Working Capital / AR-AP | AR aging, AP aging, DSO/DPO |
| KPI / Operational | SaaS metrics, manufacturing KPIs |

## How It Works

1. **Upload** any financial file (CSV, Excel, PDF)
2. **Auto-classify** — system detects the document type
3. **Normalize** — AI maps messy columns to standard schema (or fast path if already clean)
4. **Validate** — accounting identity checks, reasonableness bounds
5. **Score** — quality score (0-100) based on completeness, consistency, coverage
6. **Output** — clean DataFrame with full audit trail of every transformation

## Tech Stack

- Python, pandas
- Claude API (Anthropic) for AI normalization
- Streamlit for UI
- pdfplumber for PDF extraction
