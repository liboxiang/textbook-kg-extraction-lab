from __future__ import annotations

import re
from schemas.models import SourceBlock

# Technical segmentation only. Every character remains in exactly one block.
# We cut after Chinese/English sentence punctuation and after line breaks.
_BOUNDARY_RE = re.compile(r"[。！？；;!?]|\r\n|\n|\r")


def segment_source_text(text: str) -> list[SourceBlock]:
    if not text:
        return []

    cut_positions: list[int] = []
    for m in _BOUNDARY_RE.finditer(text):
        cut_positions.append(m.end())
    if not cut_positions or cut_positions[-1] != len(text):
        cut_positions.append(len(text))

    blocks: list[SourceBlock] = []
    start = 0
    idx = 1
    for end in cut_positions:
        if end <= start:
            continue
        piece = text[start:end]
        # Avoid emitting pure-empty zero-length slices; whitespace is preserved by attaching
        # it to the current slice because piece is exact from the source.
        block = SourceBlock(
            block_id=f"S{idx:04d}",
            index=idx,
            start_offset=start,
            end_offset=end,
            text=piece,
        )
        blocks.append(block)
        idx += 1
        start = end

    if start < len(text):
        blocks.append(
            SourceBlock(
                block_id=f"S{idx:04d}",
                index=idx,
                start_offset=start,
                end_offset=len(text),
                text=text[start:],
            )
        )

    assert "".join(b.text for b in blocks) == text
    return blocks


def render_blocks_for_prompt(blocks: list[SourceBlock]) -> str:
    return "".join(f"[{b.block_id}]{b.text}" for b in blocks)
