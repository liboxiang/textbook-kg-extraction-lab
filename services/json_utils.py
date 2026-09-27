from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise ValueError("Expected top-level JSON object")
        return obj
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            obj = json.loads(text[start : end + 1])
            if not isinstance(obj, dict):
                raise ValueError("Expected top-level JSON object")
            return obj
        raise
