"""
File reading layer. Handles CSV, Excel (multi-sheet), and PDF.
"""

import csv
import io
from pathlib import Path

import pandas as pd


class FileReadError(Exception):
    """Cannot read or parse the file."""


# Sheet selection keywords
PL_SHEET_POSITIVE = {"p&l", "pnl", "income", "profit", "loss", "p & l", "income statement",
                     "monthly", "financial", "detail", "summary", "actual", "revenue",
                     "operating", "expense"}
PL_SHEET_NEGATIVE = {"balance", "cash flow", "notes", "assumptions", "headcount",
                     "kpi", "dashboard", "chart", "cover", "contents"}


def read_file(filepath: str) -> tuple[pd.DataFrame, dict]:
    """Read any supported file into a raw DataFrame + metadata."""
    ext = Path(filepath).suffix.lower()
    metadata = {"file_type": ext, "source": filepath}

    if ext == ".csv":
        df = _read_csv(filepath)
    elif ext in (".xlsx", ".xls"):
        df, sheet_name = _read_excel(filepath)
        metadata["sheet_name"] = sheet_name
    elif ext == ".pdf":
        df = _read_pdf(filepath)
    else:
        raise FileReadError(f"Unsupported file type: {ext}")

    metadata["raw_shape"] = df.shape
    return df, metadata


def _read_csv(filepath: str) -> pd.DataFrame:
    """Read CSV with encoding fallback and messy-file handling."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            return pd.read_csv(filepath, encoding=encoding)
        except UnicodeDecodeError:
            continue
        except pd.errors.ParserError:
            try:
                with open(filepath, encoding=encoding) as f:
                    lines = f.readlines()
                max_fields = 0
                for line in lines:
                    reader = csv.reader(io.StringIO(line))
                    for row in reader:
                        max_fields = max(max_fields, len(row))
                df = pd.read_csv(
                    filepath, encoding=encoding, header=None,
                    names=[f"col_{i}" for i in range(max_fields)],
                    on_bad_lines="warn",
                )
                return df
            except Exception:
                continue
    raise FileReadError(f"Could not read CSV: {filepath}")


def _read_excel(filepath: str) -> tuple[pd.DataFrame, str]:
    """Read Excel file. For multi-sheet, select the best sheet."""
    try:
        xls = pd.ExcelFile(filepath)
    except Exception as e:
        raise FileReadError(f"Cannot open Excel file: {e}")

    sheet_name = _select_sheet(xls.sheet_names)
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)
    return df, sheet_name


def _select_sheet(sheet_names: list[str]) -> str:
    """Pick the sheet most likely to contain financial data."""
    if len(sheet_names) == 1:
        return sheet_names[0]

    scores = {}
    for name in sheet_names:
        name_lower = name.lower().strip()
        score = 0
        for kw in PL_SHEET_POSITIVE:
            if kw in name_lower:
                score += 10
        for kw in PL_SHEET_NEGATIVE:
            if kw in name_lower:
                score -= 10
        scores[name] = score

    return max(scores, key=scores.get)


def _read_pdf(filepath: str) -> pd.DataFrame:
    """Extract tables from PDF using pdfplumber. Merges multiple tables if needed."""
    try:
        import pdfplumber
    except ImportError:
        raise FileReadError("pdfplumber required for PDF. Install: pip install pdfplumber")

    try:
        with pdfplumber.open(filepath) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_tables()
                all_tables.extend(tables)

            if not all_tables:
                raise FileReadError("No tables found in PDF")

            # If we have one big table, use it directly
            largest = max(all_tables, key=lambda t: len(t) * len(t[0]) if t and t[0] else 0)
            if len(largest) >= 5:
                df = pd.DataFrame(largest[1:], columns=largest[0])
                return df

            # Multiple small tables — try to merge them
            # Find the most common column count
            col_counts = [len(t[0]) for t in all_tables if t and t[0]]
            if not col_counts:
                raise FileReadError("No valid tables found in PDF")

            target_cols = max(set(col_counts), key=col_counts.count)

            # Use the first table with target_cols as the header source
            header = None
            rows = []
            for table in all_tables:
                if not table or not table[0]:
                    continue
                if len(table[0]) != target_cols:
                    continue
                if header is None:
                    # Check if first row looks like a header (has non-numeric text)
                    first_row = table[0]
                    non_numeric = sum(1 for v in first_row if v and not v.replace(",", "").replace(".", "").replace("-", "").strip().isdigit())
                    if non_numeric >= 2:
                        header = first_row
                        rows.extend(table[1:])
                    else:
                        rows.extend(table)
                else:
                    rows.extend(table)

            if not rows:
                # Fallback: just use the largest table
                df = pd.DataFrame(largest[1:], columns=largest[0])
                return df

            if header:
                df = pd.DataFrame(rows, columns=header)
            else:
                df = pd.DataFrame(rows)

            # Drop fully empty rows
            df = df.dropna(how="all").reset_index(drop=True)

            return df
    except FileReadError:
        raise
    except Exception as e:
        raise FileReadError(f"Error reading PDF: {e}")
