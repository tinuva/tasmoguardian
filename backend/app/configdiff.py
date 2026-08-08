"""Structured diff between two decoded config JSONs."""
from typing import Any


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dicts/lists into dotted paths for stable comparison."""
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def diff_configs(a: dict, b: dict) -> list[dict[str, Any]]:
    """Return a list of {path, kind, a, b} entries. kind: added|removed|changed."""
    fa, fb = _flatten(a), _flatten(b)
    entries: list[dict[str, Any]] = []
    for path in sorted(set(fa) | set(fb)):
        in_a, in_b = path in fa, path in fb
        if in_a and not in_b:
            entries.append({"path": path, "kind": "removed", "a": fa[path], "b": None})
        elif in_b and not in_a:
            entries.append({"path": path, "kind": "added", "a": None, "b": fb[path]})
        elif fa[path] != fb[path]:
            entries.append({"path": path, "kind": "changed", "a": fa[path], "b": fb[path]})
    return entries
