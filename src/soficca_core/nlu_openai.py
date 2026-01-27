# src/soficca_core/nlu_openai.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


# -------- Config (env-driven) --------
DEFAULT_MODEL_NANO = os.getenv("SOFICCA_OPENAI_NLU_MODEL_NANO", "gpt-5-nano")
DEFAULT_MODEL_MINI = os.getenv("SOFICCA_OPENAI_NLU_MODEL_MINI", "gpt-5-mini")

# Confidence thresholds
CONF_NANO_MIN = float(os.getenv("SOFICCA_OPENAI_NLU_CONF_NANO_MIN", "0.75"))
CONF_MINI_MIN = float(os.getenv("SOFICCA_OPENAI_NLU_CONF_MINI_MIN", "0.65"))

# Token guardrails (keep output small)
MAX_OUTPUT_TOKENS = int(os.getenv("SOFICCA_OPENAI_NLU_MAX_OUTPUT_TOKENS", "300"))

# If you want to disable OpenAI usage at runtime without changing code:
ENABLED = os.getenv("SOFICCA_OPENAI_NLU_ENABLED", "1") not in ("0", "false", "False")


_client: Optional[Any] = None


def _get_client() -> Any:
    global _client
    if _client is not None:
        return _client
    if OpenAI is None:
        raise RuntimeError("openai SDK not installed. `pip install openai`.")
    _client = OpenAI()
    return _client


def _nlu_schema() -> Dict[str, Any]:
    """
    Strict schema: stable keys, no hallucinated keys, and bounded enums.
    Note: keep it compact to reduce tokens and maximize cache reuse.
    """
    # Reusable "nullable string" and "nullable bool" defs
    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    nullable_bool = {"anyOf": [{"type": "boolean"}, {"type": "null"}]}

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["answer", "user_question", "meta_pause", "file_handoff", "greeting", "emotional", "ambiguous"],
            },
            "language": {"type": "string", "enum": ["en", "es", "mix", "unknown"]},
            "answer_for_last_question": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "question_id": nullable_string,
                    "value": {"anyOf": [{"type": "string"}, {"type": "boolean"}, {"type": "null"}]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "normalized": {"type": "boolean"},
                },
                "required": ["question_id", "value", "confidence", "normalized"],
            },
            # Slot fills can include *other* slots mentioned in the same message,
            # not only the one currently asked. This is how we solve:
            # "I'm Carlos, male, from Colombia" in one turn.
            "slot_fills": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": nullable_string,
                    "gender_identity": nullable_string,
                    "country": nullable_string,
                    "reason": nullable_string,
                    "main_issue": nullable_string,
                    "frequency": nullable_string,
                    "desire": nullable_string,
                    "stress": nullable_string,
                    "morning_erection": nullable_string,
                    "route_choice": nullable_string,
                    "wants_meds": nullable_bool,
                },
                "required": [],
            },
            "needs_repair": {"type": "boolean"},
            "repair_style": {"type": "string", "enum": ["NONE", "AB", "MULTICHOICE", "EXAMPLE"]},
        },
        "required": ["intent", "language", "answer_for_last_question", "slot_fills", "needs_repair", "repair_style"],
    }


def _build_instructions() -> str:
    # Keep system instructions stable to help prompt caching.
    return (
        "You are an NLU-only interpreter for a clinical conversation engine.\n"
        "You MUST NOT provide medical advice or write assistant replies.\n"
        "Your job: read the USER_MESSAGE and return JSON that matches the schema.\n\n"
        "Rules:\n"
        "1) If the user is asking a question, set intent='user_question'.\n"
        "2) If the user says wait/pause or is sending files/logs/repo, set meta_pause/file_handoff.\n"
        "3) Otherwise, treat the message as an answer to last_question_id if provided.\n"
        "4) Normalize answers to allowed_values when possible.\n"
        "5) Extract any other slot values present in the same message into slot_fills.\n"
        "6) If you cannot confidently normalize, set value=null and needs_repair=true.\n"
        "7) Never invent new keys. Output must match the schema exactly.\n"
    )


def _build_user_payload(
    user_text: str,
    *,
    last_question_id: Optional[str],
    question_text: Optional[str],
    allowed_values: Optional[list],
    slot_snapshot: Optional[dict],
    mode: Optional[str],
) -> str:
    payload = {
        "last_question_id": last_question_id,
        "question_text": question_text,
        "allowed_values": allowed_values,
        "mode": mode,
        "slot_snapshot": slot_snapshot or {},
        "USER_MESSAGE": user_text,
    }
    return json.dumps(payload, ensure_ascii=False)


def call_openai_nlu(
    user_text: str,
    *,
    last_question_id: Optional[str] = None,
    question_text: Optional[str] = None,
    allowed_values: Optional[list] = None,
    slot_snapshot: Optional[dict] = None,
    mode: Optional[str] = None,
    force_model: Optional[str] = None,  # "nano" | "mini" | None
) -> Dict[str, Any]:
    """
    Returns dict in the schema shape.

    force_model:
      - None: start with nano
      - "nano": force nano
      - "mini": force mini
    """
    if not ENABLED:
        raise RuntimeError("OpenAI NLU is disabled via SOFICCA_OPENAI_NLU_ENABLED=0")

    client = _get_client()

    # Decide model
    if force_model == "mini":
        model = DEFAULT_MODEL_MINI
    else:
        model = DEFAULT_MODEL_NANO

    schema = _nlu_schema()

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": _build_instructions()},
            {
                "role": "user",
                "content": _build_user_payload(
                    user_text,
                    last_question_id=last_question_id,
                    question_text=question_text,
                    allowed_values=allowed_values,
                    slot_snapshot=slot_snapshot,
                    mode=mode,
                ),
            },
        ],
        max_output_tokens=MAX_OUTPUT_TOKENS,
        text={
            "format": {
                "type": "json_schema",
                "name": "soficca_nlu",
                "strict": True,
                "schema": schema,
            }
        },
    )

    raw = getattr(response, "output_text", None)
    if not raw:
        # Some SDK versions may store it elsewhere; try best-effort.
        raw = str(response)

    try:
        data = json.loads(raw)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"NLU JSON parse failed: {e}. Raw: {raw[:2000]}")

    return data


def pick_model_for_confidence(confidence: float, *, used_model: str) -> Tuple[bool, str]:
    """
    Decide whether to accept or retry on mini.

    Returns: (accept, next_force_model)
    """
    if used_model == "nano":
        if confidence >= CONF_NANO_MIN:
            return True, "nano"
        return False, "mini"
    # used_model == "mini"
    if confidence >= CONF_MINI_MIN:
        return True, "mini"
    return False, "mini"
