"""Append-only audit trail for the agent loop.

Every entry is one JSON object on its own line (JSON Lines) in
`output/audit_trail.json`. The file is only ever opened in append mode — there
is no code path in this project that truncates, rewrites or rotates it — so the
record survives restarts and accumulates across runs.

Reading it back:

    import json
    with open("output/audit_trail.json", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"

_lock = threading.Lock()


def brief(value: Any, limit: int = 160) -> Any:
    """Shorten a value for the log — arguments and results are summarized, not dumped."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= limit else value[: limit - 1] + "…"
    if isinstance(value, (list, tuple)):
        shown = [brief(v, 60) for v in value[:5]]
        return shown + [f"…+{len(value) - 5} more"] if len(value) > 5 else shown
    if isinstance(value, dict):
        return {k: brief(v, 60) for k, v in list(value.items())[:8]}
    return brief(str(value), limit)


def record(event: str, **fields: Any) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "event": event,
        **fields,
    }
    line = json.dumps(entry, ensure_ascii=False)
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Append mode only. Never "w".
        with AUDIT_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def tool_call(run_id: str, tool: str, args: dict, result: Any, ms: float) -> None:
    record(
        "tool_call",
        run_id=run_id,
        tool=tool,
        args=brief({k: v for k, v in args.items() if v is not None}),
        result=brief(result),
        ms=round(ms, 1),
    )
