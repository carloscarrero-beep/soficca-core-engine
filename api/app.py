import soficca_core.engine as engine
import soficca_core.interpret_en as interpret_mod
import os

print("ENGINE FILE:", engine.__file__)
print("INTERPRET FILE:", interpret_mod.__file__)
print("OPENAI KEY LOADED:", bool(os.getenv("OPENAI_API_KEY")))
print("NLU MODE:", os.getenv("SOFICCA_NLU_MODE"))
print("NLU ENABLED:", os.getenv("SOFICCA_OPENAI_NLU_ENABLED"))

import io
import csv
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.responses import HTMLResponse
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import sqlite3
import uuid
import json
from datetime import datetime, timezone

from soficca_core.engine import generate_report

app = FastAPI(title="Soficca Core API", version="0.1.0")

DB_PATH = Path(__file__).with_name("soficca_demo.sqlite")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        user_json TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        user_text TEXT NOT NULL,
        assistant_text TEXT NOT NULL,
        phase TEXT,
        path TEXT,
        flags_json TEXT,
        reasons_json TEXT,
        recommendations_json TEXT,
        trace_json TEXT,
        state_json TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(session_id)
    );
    """)

    conn.commit()
    conn.close()


_init_db()


class CoreRequest(BaseModel):
    user: Dict[str, Any] = Field(default_factory=dict)
    measurements: List[Any] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class SessionCreateResponse(BaseModel):
    session_id: str


class SessionResetRequest(BaseModel):
    session_id: str


@app.post("/v1/session", response_model=SessionCreateResponse)
def create_session(payload: CoreRequest):
    """
    Creates a new anonymous session_id for demo usage (no login).
    Stores the initial user profile snapshot.
    """
    session_id = str(uuid.uuid4())
    conn = _db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sessions(session_id, created_at, user_json) VALUES (?, ?, ?)",
        (session_id, _utc_now_iso(), json.dumps(payload.user or {})),
    )
    conn.commit()
    conn.close()
    return {"session_id": session_id}


@app.post("/v1/session/reset")
def reset_session(payload: SessionResetRequest):
    """
    Clears all turns for a session. Keeps the session record.
    """
    conn = _db()
    cur = conn.cursor()
    cur.execute("DELETE FROM turns WHERE session_id = ?", (payload.session_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "session_id": payload.session_id}


@app.post("/v1/report")
def v1_report(payload: CoreRequest):
    """
    Standard report endpoint, now with session logging.
    Expects: context.session_id (optional but recommended for demo).
    """
    session_id = (payload.context or {}).get("session_id")

    # If no session_id, we still run but won't log
    result = generate_report(payload.model_dump())

    # Attach session_id back to client so UI can persist it
    try:
        result.setdefault("meta", {})
        if session_id:
            result["meta"]["session_id"] = session_id
    except Exception:
        pass

    if not session_id:
        return result

    report = (result or {}).get("report") or {}
    chat = report.get("chat") or {}

    user_text = (payload.context or {}).get("chat_text") or ""
    assistant_text = chat.get("assistant_message") or ""

    conn = _db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO turns(
            session_id, created_at, user_text, assistant_text,
            phase, path,
            flags_json, reasons_json, recommendations_json, trace_json,
            state_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            _utc_now_iso(),
            user_text,
            assistant_text,
            chat.get("phase"),
            report.get("path"),
            json.dumps(report.get("flags", [])),
            json.dumps(report.get("reasons", [])),
            json.dumps(report.get("recommendations", [])),
            json.dumps(report.get("trace", {}), default=str),
            json.dumps(chat.get("state", {}), default=str),
        ),
    )
    conn.commit()
    conn.close()

    return result


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Soficca Core API",
        "version": "0.1.0",
        "endpoints": ["/docs", "/v1/session", "/v1/report", "/demo"],
    }


@app.get("/demo", response_class=HTMLResponse)
def demo():
    html_path = Path(__file__).with_name("demo.html")
    return html_path.read_text(encoding="utf-8")

@app.get("/v1/session/{session_id}/export.json")
def export_session_json(session_id: str):
    conn = _db()
    cur = conn.cursor()

    cur.execute("SELECT session_id, created_at, user_json FROM sessions WHERE session_id = ?", (session_id,))
    s = cur.fetchone()
    if not s:
        conn.close()
        raise HTTPException(status_code=404, detail="session_id not found")

    cur.execute("""
        SELECT
            id, created_at, user_text, assistant_text,
            phase, path,
            flags_json, reasons_json, recommendations_json, trace_json,
            state_json
        FROM turns
        WHERE session_id = ?
        ORDER BY id ASC
    """, (session_id,))
    rows = cur.fetchall()
    conn.close()

    turns = []
    for r in rows:
        turns.append({
            "id": r["id"],
            "created_at": r["created_at"],
            "user_text": r["user_text"],
            "assistant_text": r["assistant_text"],
            "phase": r["phase"],
            "path": r["path"],
            "flags": json.loads(r["flags_json"] or "[]"),
            "reasons": json.loads(r["reasons_json"] or "[]"),
            "recommendations": json.loads(r["recommendations_json"] or "[]"),
            "trace": json.loads(r["trace_json"] or "{}"),
            "state": json.loads(r["state_json"] or "{}"),
        })

    payload = {
        "session_id": s["session_id"],
        "created_at": s["created_at"],
        "user": json.loads(s["user_json"] or "{}"),
        "turns": turns,
        "turn_count": len(turns),
    }
    return JSONResponse(payload)


@app.get("/v1/session/{session_id}/export.csv")
def export_session_csv(session_id: str):
    conn = _db()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="session_id not found")

    cur.execute("""
        SELECT
            id, created_at, user_text, assistant_text,
            phase, path,
            flags_json, reasons_json, recommendations_json, trace_json
        FROM turns
        WHERE session_id = ?
        ORDER BY id ASC
    """, (session_id,))
    rows = cur.fetchall()
    conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "created_at", "user_text", "assistant_text",
        "phase", "path", "flags", "reasons", "recommendations", "trace"
    ])

    for r in rows:
        writer.writerow([
            r["id"],
            r["created_at"],
            r["user_text"],
            r["assistant_text"],
            r["phase"],
            r["path"],
            r["flags_json"] or "[]",
            r["reasons_json"] or "[]",
            r["recommendations_json"] or "[]",
            r["trace_json"] or "{}",
        ])

    buf.seek(0)
    filename = f"pen2_session_{session_id}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

