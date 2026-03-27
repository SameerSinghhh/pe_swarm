"""
Shared cleaning and parsing utilities used across the ingestion pipeline.
"""

import re
import pandas as pd


# Keywords used for heuristic detection of financial data
FINANCIAL_KEYWORDS = {
    # General
    "revenue", "sales", "income", "cogs", "cost", "gross", "ebitda",
    "operating", "net", "total", "expense", "profit", "margin", "month",
    "date", "period", "quarter", "year", "budget", "actual", "variance",
    "labor", "material", "overhead", "marketing", "admin", "research",
    "development", "selling", "general", "sg&a", "sga", "opex",
    # Balance sheet
    "assets", "liabilities", "equity", "receivable", "payable",
    "inventory", "cash", "debt", "retained", "stockholder",
    # Cash flow
    "capex", "investing", "financing", "depreciation", "amortization",
    # Trial balance / GL
    "debit", "credit", "account", "ledger", "trial", "balance",
    # Working capital
    "aging", "dso", "dpo", "dio", "days", "outstanding", "current",
    # KPI
    "churn", "retention", "cac", "ltv", "arr", "mrr", "headcount",
    "utilization", "throughput", "yield", "nrr", "nps",
}


def to_numeric(series: pd.Series) -> pd.Series:
    """Convert a series to numeric, handling currency formatting."""
    def clean(val):
        if pd.isna(val):
            return val
        s = str(val).strip()
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
        s = re.sub(r"[$,\s]", "", s)
        s = s.rstrip("%")
        try:
            return float(s)
        except ValueError:
            return None

    return series.apply(clean).astype(float)


def parse_period(val: str) -> str | None:
    """Try to parse a date string into YYYY-MM format."""
    if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nan":
        return None

    val = str(val).strip()

    if re.match(r"^\d{4}-\d{2}$", val):
        return val

    formats = [
        "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y",
        "%B %Y", "%b %Y", "%b-%Y", "%b-%y",
        "%B %d, %Y", "%Y/%m/%d", "%d-%b-%Y", "%d-%b-%y",
        "%m-%Y", "%Y%m",
    ]

    for fmt in formats:
        try:
            dt = pd.to_datetime(val, format=fmt)
            return dt.strftime("%Y-%m")
        except (ValueError, TypeError):
            continue

    try:
        dt = pd.to_datetime(val)
        return dt.strftime("%Y-%m")
    except (ValueError, TypeError):
        return None


def detect_header_row(raw_df: pd.DataFrame) -> tuple[int, pd.DataFrame]:
    """
    Find the row most likely to be the header.
    Returns (header_row_index, DataFrame_with_proper_header).
    """
    if columns_look_financial(raw_df.columns):
        return 0, raw_df

    best_row = 0
    best_score = 0

    for i in range(min(15, len(raw_df))):
        row = raw_df.iloc[i]
        score = 0
        for val in row:
            if pd.isna(val):
                continue
            val_str = str(val).lower().strip()
            for kw in FINANCIAL_KEYWORDS:
                if kw in val_str:
                    score += 1
                    break
        if score > best_score:
            best_score = score
            best_row = i

    if best_score >= 2:
        new_header = [
            str(v).strip() if pd.notna(v) else f"col_{i}"
            for i, v in enumerate(raw_df.iloc[best_row])
        ]
        df = raw_df.iloc[best_row + 1:].copy()
        df.columns = new_header
        df = df.reset_index(drop=True)
        return best_row, df

    return 0, raw_df


def columns_look_financial(columns) -> bool:
    """Check if column names contain financial keywords."""
    hits = 0
    for col in columns:
        col_str = str(col).lower()
        for kw in FINANCIAL_KEYWORDS:
            if kw in col_str:
                hits += 1
                break
    return hits >= 3


def build_preview(df: pd.DataFrame) -> str:
    """Build a text preview: first 5 rows + last 2 rows."""
    lines = []
    lines.append("FIRST 5 ROWS:")
    lines.append(df.head(5).to_string(index=True))
    lines.append("")
    lines.append("LAST 2 ROWS:")
    lines.append(df.tail(2).to_string(index=True))
    return "\n".join(lines)


def get_pre_header_context(raw_df: pd.DataFrame, header_row_idx: int) -> str:
    """Capture pre-header rows (titles, notes like '$000s')."""
    if header_row_idx <= 0:
        return ""
    pre_rows = []
    for i in range(header_row_idx):
        row_vals = [str(v) for v in raw_df.iloc[i] if pd.notna(v) and str(v).strip()]
        if row_vals:
            pre_rows.append(" | ".join(row_vals))
    if pre_rows:
        return "FILE HEADER/TITLE ROWS (above the data):\n" + "\n".join(pre_rows) + "\n\n"
    return ""
