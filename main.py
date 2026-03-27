"""
CLI entry point — ingestion only.

Usage:
    python main.py                                   # Sample P&L
    python main.py data/test/quickbooks_export.csv   # Any file
    python main.py file.xlsx --company "Acme" --type "Manufacturing"
"""

import json
import os
import sys
from datetime import date

from core.ingest import ingest_file


def main():
    filepath = "data/sample_pl.csv"
    company_name = ""
    business_type = ""
    doc_type_hint = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--company" and i + 1 < len(args):
            company_name = args[i + 1]
            i += 2
        elif args[i] == "--type" and i + 1 < len(args):
            business_type = args[i + 1]
            i += 2
        elif args[i] == "--doc-type" and i + 1 < len(args):
            doc_type_hint = args[i + 1]
            i += 2
        elif not args[i].startswith("--"):
            filepath = args[i]
            i += 1
        else:
            i += 1

    w = 60

    print(f"\n{'═' * w}")
    print(f"  FINANCIAL DATA INGESTION")
    print(f"{'═' * w}")

    print(f"\n📂 Input: {filepath}")

    try:
        result = ingest_file(filepath, company_name=company_name,
                           business_type=business_type, doc_type_hint=doc_type_hint)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    # Classification
    print(f"\n🏷  Document Type: {result.doc_type_name} (confidence: {result.classification_confidence})")

    # Normalization method
    method = "Fast path" if not result.used_ai else ("Code-gen fallback" if result.used_fallback else "AI (Claude)")
    print(f"🔄 Method: {method}")
    print(f"📊 Rows: {len(result.df)} | Columns: {len(result.df.columns)}")

    # Quality score
    qs = result.quality_score
    if qs >= 80:
        indicator = "🟢"
    elif qs >= 50:
        indicator = "🟡"
    else:
        indicator = "🔴"
    print(f"\n{indicator} Quality Score: {qs}/100")

    if result.quality_report:
        qr = result.quality_report
        print(f"{'─' * w}")
        print(f"  Completeness:    {qr.completeness_score:5.1f}/100  (non-null required cells)")
        print(f"  Consistency:     {qr.consistency_score:5.1f}/100  (accounting identities)")
        print(f"  Coverage:        {qr.coverage_score:5.1f}/100  (temporal completeness)")
        print(f"  Reasonableness:  {qr.reasonableness_score:5.1f}/100  (values in expected range)")

    # Audit trail
    if result.audit_trail:
        print(f"\n📝 Audit Trail ({len(result.audit_trail)} transformations)")
        print(f"{'─' * w}")
        for entry in result.audit_trail:
            action = entry["action"]
            field = entry.get("field", "")
            detail = entry["detail"]
            icon = {
                "renamed": "📛",
                "auto_fill_zero": "⚠️",
                "derived": "🔢",
                "auto_corrected": "🔧",
                "row_dropped": "🗑️",
                "multiplier_applied": "✖️",
                "mapped_sum": "➕",
                "fallback_used": "🆘",
                "auto_sorted": "📅",
            }.get(action, "•")
            print(f"  {icon} {detail}")

    # Warnings
    if result.warnings:
        print(f"\n⚠️  Warnings")
        print(f"{'─' * w}")
        for warning in result.warnings:
            print(f"  {warning}")

    if result.unmapped_fields:
        print(f"\n❓ Unmapped fields: {result.unmapped_fields}")

    # Data preview
    print(f"\n📋 Data Preview")
    print(f"{'─' * w}")
    row = result.df.iloc[-1]
    for col in result.df.columns:
        v = row[col]
        if isinstance(v, float) and abs(v) >= 1000:
            print(f"  {col:>20}: ${v:>14,.0f}")
        else:
            print(f"  {col:>20}: {v}")

    # Save
    os.makedirs("output", exist_ok=True)
    output_file = f"output/normalized_{date.today().isoformat()}.json"
    output = {
        "source_file": filepath,
        "doc_type": result.doc_type,
        "quality_score": result.quality_score,
        "used_ai": result.used_ai,
        "used_fallback": result.used_fallback,
        "audit_trail": result.audit_trail,
        "warnings": result.warnings,
        "unmapped_fields": result.unmapped_fields,
        "rows": len(result.df),
        "columns": list(result.df.columns),
        "data": result.df.to_dict(orient="records"),
    }
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n{'═' * w}")
    print(f"  Saved: {output_file}")
    print(f"{'═' * w}\n")


if __name__ == "__main__":
    main()
