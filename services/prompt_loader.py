from __future__ import annotations

import re
from pathlib import Path
from typing import MutableMapping

ROOT = Path(__file__).resolve().parents[1]


def list_prompt_versions(kind: str) -> list[str]:
    folder = ROOT / "prompts" / kind
    versions = [p.stem for p in folder.glob("*.md")]
    return sorted(versions, key=_version_sort_key)


def _version_sort_key(version: str) -> tuple[tuple[int, int | str], ...]:
    parts = re.split(r"(\d+)", version)
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in parts
        if part
    )


def sync_prompt_selection(
    session_state: MutableMapping[str, object],
    selection_key: str,
    default_marker_key: str,
    versions: list[str],
    default_version: str | None = None,
) -> str | None:
    """Apply a changed default once while preserving later user selections."""
    if not versions:
        return None

    effective_default = default_version if default_version in versions else versions[-1]
    if session_state.get(default_marker_key) != effective_default:
        session_state[selection_key] = effective_default
        session_state[default_marker_key] = effective_default
    elif session_state.get(selection_key) not in versions:
        session_state[selection_key] = effective_default

    return str(session_state[selection_key])


def prompt_widget_key(prefix: str, kind: str, version: str) -> str:
    """Give each prompt kind/version pair independent editable widget state."""
    return f"{prefix}_{kind}_{version}"


def load_prompt(kind: str, version: str) -> str:
    path = ROOT / "prompts" / kind / f"{version}.md"
    return path.read_text(encoding="utf-8")
