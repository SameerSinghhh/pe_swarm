"""
AI code-generation fallback.

When the standard mapping approach fails, ask Claude to write a custom
Python function that transforms the raw DataFrame into a clean one.
Execute it in a sandboxed scope (pandas/numpy only).
"""

import os
import signal
from dataclasses import dataclass

import pandas as pd
import numpy as np
from dotenv import load_dotenv

from core.schemas.base import DocumentSchema
from core.cleaning import build_preview, detect_header_row

load_dotenv()

MAX_ATTEMPTS = 2
TIMEOUT_SECONDS = 30


@dataclass
class FallbackResult:
    df: pd.DataFrame
    code: str
    explanation: str
    attempt: int


class FallbackError(Exception):
    def __init__(self, message: str, diagnostics: dict | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


# Restricted builtins for sandbox
import re as _re

SAFE_BUILTINS = {
    "range": range, "len": len, "int": int, "float": float,
    "str": str, "list": list, "dict": dict, "tuple": tuple,
    "set": set, "enumerate": enumerate, "zip": zip,
    "map": map, "filter": filter, "sorted": sorted, "reversed": reversed,
    "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
    "isinstance": isinstance, "type": type, "any": any, "all": all,
    "True": True, "False": False, "None": None, "print": print,
    "ValueError": ValueError, "KeyError": KeyError, "TypeError": TypeError,
    "IndexError": IndexError, "Exception": Exception,
    "__import__": __import__,  # needed for generated code that uses import
}

# Additional safe modules available in sandbox
SAFE_MODULES = {
    "re": _re,
}


def attempt_code_fallback(
    raw_df: pd.DataFrame,
    metadata: dict,
    schema: DocumentSchema,
    error_context: str,
    business_type: str = "",
    raw_profile=None,
) -> FallbackResult:
    """
    Ask Claude to write a transform function, execute it sandboxed.
    Retries once if the first attempt fails.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        raise FallbackError("anthropic package required")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        raise FallbackError("ANTHROPIC_API_KEY not set")

    _, df_with_header = detect_header_row(raw_df)
    preview = build_preview(df_with_header)
    columns = list(df_with_header.columns)

    # Profile text
    profile_text = ""
    if raw_profile:
        try:
            from core.profiler import format_profile_for_prompt
            profile_text = format_profile_for_prompt(raw_profile)
        except Exception:
            pass

    # Build target schema description
    schema_fields = []
    for f in schema.fields:
        req = "REQUIRED" if f.required else "optional"
        schema_fields.append(f"  - {f.name}: {f.description} [{req}]")
    schema_desc = "\n".join(schema_fields)

    client = Anthropic()
    last_error = None
    last_code = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt == 1:
            prompt = _build_initial_prompt(
                preview, columns, schema_desc, error_context, profile_text, business_type
            )
            messages = [{"role": "user", "content": prompt}]
        else:
            # Retry with error feedback
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": last_code},
                {"role": "user", "content": f"That code failed with this error:\n{last_error}\n\nFix the code. Return ONLY the corrected Python code."},
            ]

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=messages,
        )

        text = response.content[0].text.strip()

        # Extract code from markdown if present
        code = _extract_code(text)
        last_code = code

        # Execute in sandbox
        try:
            result_df = _execute_sandboxed(code, raw_df.copy())
        except Exception as e:
            last_error = str(e)
            if attempt == MAX_ATTEMPTS:
                raise FallbackError(
                    f"Code-gen failed after {MAX_ATTEMPTS} attempts: {last_error}",
                    diagnostics={"code": code, "error": last_error, "attempts": attempt},
                )
            continue

        # Extract explanation from Claude's response
        explanation = ""
        if "```" in text:
            parts = text.split("```")
            non_code = [p for p in parts if not p.startswith("python")]
            explanation = " ".join(non_code).strip()

        return FallbackResult(
            df=result_df,
            code=code,
            explanation=explanation or "Code-gen fallback produced the result.",
            attempt=attempt,
        )

    raise FallbackError("Code-gen exhausted all attempts", {"attempts": MAX_ATTEMPTS})


def _build_initial_prompt(
    preview: str,
    columns: list,
    schema_desc: str,
    error_context: str,
    profile_text: str,
    business_type: str,
) -> str:
    return f"""You are a financial data cleaning expert. The standard ingestion pipeline failed on this file. Write a Python function to clean and normalize it.

ERROR THAT OCCURRED:
{error_context}

RAW DATA PREVIEW:
Columns: {columns}
{preview}

{profile_text}

BUSINESS TYPE: {business_type or "Unknown"}

TARGET OUTPUT SCHEMA (the function must produce a DataFrame with these columns):
{schema_desc}

REQUIREMENTS:
1. Write a function: def transform(df: pd.DataFrame) -> pd.DataFrame
2. The input `df` is the raw data read from the file (as shown above)
3. The output must have the target columns listed above
4. Use only pandas (pd) and numpy (np) — no other imports
5. Handle messy data: strip whitespace, convert currencies, handle encoding issues
6. Drop total/subtotal/header/notes rows
7. Parse dates into YYYY-MM format
8. If values are in $000s or $M, multiply appropriately
9. Derive missing fields where possible (e.g., gross_profit = revenue - cogs)

Return ONLY the Python code. No explanation outside the code block."""


def _extract_code(text: str) -> str:
    """Extract Python code from Claude's response."""
    if "```python" in text:
        parts = text.split("```python")
        code = parts[1].split("```")[0].strip()
        return code
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            return parts[1].strip()
    # No code fences — assume the whole response is code
    return text.strip()


def _execute_sandboxed(code: str, raw_df: pd.DataFrame) -> pd.DataFrame:
    """Execute the generated code in a restricted environment."""
    restricted_globals = {
        "__builtins__": SAFE_BUILTINS,
        "pd": pd,
        "np": np,
        "re": _re,
    }

    # Set timeout (Unix only)
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Code execution timed out after {TIMEOUT_SECONDS}s")

    old_handler = None
    try:
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(TIMEOUT_SECONDS)
    except (AttributeError, ValueError):
        pass  # Windows or non-main thread

    try:
        exec(code, restricted_globals)

        if "transform" not in restricted_globals:
            raise ValueError("Code must define a 'transform(df)' function")

        transform_fn = restricted_globals["transform"]
        result = transform_fn(raw_df)

        if not isinstance(result, pd.DataFrame):
            raise ValueError(f"transform() returned {type(result)}, expected pd.DataFrame")

        return result
    finally:
        try:
            signal.alarm(0)
            if old_handler is not None:
                signal.signal(signal.SIGALRM, old_handler)
        except (AttributeError, ValueError):
            pass
