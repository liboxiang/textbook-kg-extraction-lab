from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from schemas.models import Stage1LLMResult, Stage2LLMResult


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/validate_codex_result.py <task_dir>")
    task_dir = Path(sys.argv[1])
    input_data = json.loads((task_dir / "input.json").read_text(encoding="utf-8"))
    result_data = json.loads((task_dir / "result.json").read_text(encoding="utf-8"))
    stage = task_dir.name.rsplit("_", 1)[-1].upper()
    if stage == "STAGE1":
        parsed = Stage1LLMResult.model_validate(result_data)
        block_ids = [b["block_id"] for b in input_data["source_blocks"]]
        used = []
        idx = {bid: i for i, bid in enumerate(block_ids)}
        for ku in sorted(parsed.knowledge_units, key=lambda x: x.order_index):
            if ku.start_block_id not in idx or ku.end_block_id not in idx:
                raise ValueError("Unknown source block ID")
            s, e = idx[ku.start_block_id], idx[ku.end_block_id]
            if s > e:
                raise ValueError("Invalid KU block range")
            used.extend(block_ids[s:e+1])
        if used != block_ids:
            raise ValueError("Stage1 must cover every block exactly once, in order")
    elif stage == "STAGE2":
        parsed = Stage2LLMResult.model_validate(result_data)
        expected = {u["temp_ku_id"] for u in input_data["knowledge_units"]}
        actual = {u.temp_ku_id for u in parsed.knowledge_units}
        if expected != actual:
            raise ValueError(f"KU ID mismatch expected={expected} actual={actual}")
    else:
        raise ValueError(f"Unknown task stage: {stage}")
    print("VALIDATION PASS")


if __name__ == "__main__":
    main()
