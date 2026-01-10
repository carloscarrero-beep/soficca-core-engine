from __future__ import annotations

from typing import Any, Dict, Optional


def make_error(code: str, message: str, path: str = "$", meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {
        "code": code,
        "message": message,
        "path": path,
    }
    if meta:
        err["meta"] = meta
    return err

