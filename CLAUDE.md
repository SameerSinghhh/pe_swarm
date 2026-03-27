# PE Platform — Universal Financial Data Ingestion

## What This Project Is

A universal financial data ingestion and normalization system for private equity firms.
Takes ANY messy financial file (P&L, balance sheet, AR aging, trial balance, etc.)
in ANY format (CSV, Excel, PDF) and normalizes it into clean, consistent, validated output.

**Current focus: Data ingestion ONLY. Analysis comes later.**

## Architecture

```
core/
├── ingest.py          ← Universal orchestrator (entry point: ingest_file())
├── classify.py        ← Document type classification (heuristic + AI fallback)
├── registry.py        ← Schema registry (auto-discovery)
├── readers.py         ← File reading (CSV/Excel/PDF)
├── normalize.py       ← AI normalization engine (Claude API)
├── validate.py        ← Validation engine
├── cleaning.py        ← Shared utilities (_to_numeric, _parse_month, etc.)
├── result.py          ← NormalizedResult dataclass
└── schemas/
    ├── base.py                ← Abstract DocumentSchema class
    ├── income_statement.py    ← P&L
    ├── balance_sheet.py
    ├── cash_flow.py
    ├── trial_balance.py
    ├── revenue_detail.py
    ├── cost_detail.py
    ├── working_capital.py
    └── kpi_operational.py
```

## Pipeline Flow

```
Any File → readers.py → classify.py → normalize.py → validate.py → NormalizedResult
```

1. **Read**: Detect file type, handle encoding, select Excel sheet
2. **Classify**: What type of financial document? (heuristic first, AI fallback)
3. **Fast path**: If columns already match the schema, skip AI
4. **Normalize**: Send preview to Claude, get column mapping, apply it
5. **Validate**: Check type-specific rules (e.g., Assets = Liabilities + Equity)
6. **Return**: Clean DataFrame + metadata

## 8 Supported Document Types

1. Income Statement / P&L
2. Balance Sheet
3. Cash Flow Statement
4. Trial Balance / General Ledger
5. Revenue Detail (by customer/product/segment)
6. Cost Detail (by department/vendor/category)
7. Working Capital / AR-AP Aging
8. KPI / Operational Data

## Key Design Principles

- Each document type is a schema class that registers itself
- Heuristic classification first, AI only when ambiguous
- Fast path: skip AI if data already matches a known schema
- Derive fields when possible (GP = Rev - COGS) rather than requiring all fields
- Always report what couldn't be mapped (unmapped_fields)
- Type-specific validation rules (balance sheet must balance, trial balance debits = credits)
- $000s / $M multiplier detection
- Handle messy real-world data: wrong headers, merged cells, notes, QuickBooks/NetSuite exports

## Dependencies

anthropic, pandas, python-dotenv, openpyxl, pdfplumber

## Running

- CLI: `python main.py <filepath>`
- UI: `streamlit run app.py`
