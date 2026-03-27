"""
Document type classification. Heuristic first, AI fallback for ambiguous cases.
"""

import json
import os

import pandas as pd
from dotenv import load_dotenv

from core.registry import DocumentTypeRegistry
from core.schemas.base import DocumentSchema
from core.cleaning import detect_header_row, build_preview

load_dotenv()


def classify_document(
    raw_df: pd.DataFrame,
    metadata: dict,
    doc_type_hint: str | None = None,
) -> tuple[DocumentSchema, str]:
    """
    Classify a document and return (schema, confidence).

    If doc_type_hint is provided and valid, uses it directly.
    Otherwise: heuristic scoring, then AI fallback if ambiguous.
    """
    # Ensure schemas are loaded
    import core.schemas  # noqa: F401

    # Explicit hint
    if doc_type_hint:
        schema = DocumentTypeRegistry.get(doc_type_hint)
        if schema:
            return schema, "hint"

    # Heuristic classification
    _, df_with_header = detect_header_row(raw_df)
    columns = [str(c).lower().strip() for c in df_with_header.columns]
    col_text = " ".join(columns)

    # Also look at first few rows of data for keywords
    data_text = ""
    for i in range(min(5, len(df_with_header))):
        row_vals = [str(v).lower() for v in df_with_header.iloc[i] if pd.notna(v)]
        data_text += " ".join(row_vals) + " "

    full_text = col_text + " " + data_text

    scores: dict[str, int] = {}
    for schema in DocumentTypeRegistry.all_schemas():
        score = 0
        for keyword, weight in schema.classification_keywords.items():
            if keyword.lower() in full_text:
                score += weight
        scores[schema.doc_type_id] = score

    if not scores:
        raise ValueError("No document schemas registered")

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_id, best_score = sorted_scores[0]
    runner_up_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0

    # High confidence: best score > 2x runner-up and score >= 10
    if best_score >= 10 and (runner_up_score == 0 or best_score > runner_up_score * 2):
        schema = DocumentTypeRegistry.get(best_id)
        return schema, "high"

    # Medium confidence: best score > runner-up
    if best_score > runner_up_score and best_score >= 5:
        schema = DocumentTypeRegistry.get(best_id)
        return schema, "medium"

    # Low confidence / ambiguous: try AI classification
    try:
        schema, confidence = _ai_classify(raw_df, metadata)
        return schema, confidence
    except Exception:
        # Fallback to best heuristic guess
        schema = DocumentTypeRegistry.get(best_id)
        return schema, "low"


def _ai_classify(raw_df: pd.DataFrame, metadata: dict) -> tuple[DocumentSchema, str]:
    """Use Claude to classify an ambiguous document."""
    try:
        from anthropic import Anthropic
    except ImportError:
        raise RuntimeError("anthropic package required for AI classification")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError("No API key for AI classification")

    _, df_with_header = detect_header_row(raw_df)
    preview = build_preview(df_with_header)
    columns = [str(c) for c in df_with_header.columns]

    type_list = DocumentTypeRegistry.summary()

    prompt = f"""You are a financial document classifier for a PE analytics platform.

Given this data preview, determine which type of financial document this is.

DOCUMENT TYPES:
{type_list}

COLUMNS: {columns}

{preview}

Return ONLY: {{"doc_type": "<id from the list above>", "confidence": "high" or "medium" or "low", "reasoning": "<brief>"}}
No markdown. No code fences. Only the JSON."""

    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
        if text.endswith("```"):
            text = text[:-3].strip()

    result = json.loads(text)
    doc_type_id = result.get("doc_type", "")
    confidence = result.get("confidence", "medium")

    schema = DocumentTypeRegistry.get(doc_type_id)
    if not schema:
        raise ValueError(f"AI returned unknown doc type: {doc_type_id}")

    return schema, confidence
