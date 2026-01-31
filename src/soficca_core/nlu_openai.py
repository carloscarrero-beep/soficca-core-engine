# src/soficca_core/nlu_openai.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


# -------- Config --------
# Robust defaults for strict schema NLU
DEFAULT_MODEL_NANO = os.getenv("SOFICCA_OPENAI_NLU_MODEL_NANO", "gpt-4o-mini")
DEFAULT_MODEL_MINI = os.getenv("SOFICCA_OPENAI_NLU_MODEL_MINI", "gpt-4o")

CONF_NANO_MIN = float(os.getenv("SOFICCA_OPENAI_NLU_CONF_NANO_MIN", "0.75"))
CONF_MINI_MIN = float(os.getenv("SOFICCA_OPENAI_NLU_CONF_MINI_MIN", "0.65"))

MAX_OUTPUT_TOKENS = int(os.getenv("SOFICCA_OPENAI_NLU_MAX_OUTPUT_TOKENS", "300"))


def ENABLED() -> bool:
    return os.getenv("SOFICCA_OPENAI_NLU_ENABLED", "1").lower() not in ("0", "false", "no", "off")


_client: Optional[Any] = None


def _get_client() -> Any:
    global _client
    if _client is not None:
        return _client
    if OpenAI is None:
        raise RuntimeError("openai SDK not installed")
    _client = OpenAI()
    return _client


def _nlu_schema() -> Dict[str, Any]:
    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}

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
            "slot_fills": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "gender_identity": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "country": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "reason": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "main_issue": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "frequency": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "desire": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "stress": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "morning_erection": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "route_choice": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "wants_meds": {"anyOf": [{"type": "boolean"}, {"type": "null"}]},
                },
                "required": [
                    "name",
                    "gender_identity",
                    "country",
                    "reason",
                    "main_issue",
                    "frequency",
                    "desire",
                    "stress",
                    "morning_erection",
                    "route_choice",
                    "wants_meds",
                ],
            },
            "needs_repair": {"type": "boolean"},
            "repair_style": {"type": "string", "enum": ["NONE", "AB", "MULTICHOICE", "EXAMPLE"]},
        },
        "required": ["intent", "language", "answer_for_last_question", "slot_fills", "needs_repair", "repair_style"],
    }


def _instructions() -> str:
    return (
        "You are an NLU-only interpreter.\n"
        "Return ONLY JSON that matches the schema.\n"
        "Do NOT write clinical advice or assistant replies.\n"
        "If you can answer the last_question_id, set intent='answer'.\n"
    )


def call_openai_nlu(
    user_text: str,
    *,
    last_question_id: Optional[str],
    question_text: Optional[str],
    allowed_values: Optional[list],
    slot_snapshot: Optional[dict],
    mode: Optional[str],
    force_model: str = "nano",
) -> Dict[str, Any]:
    if not ENABLED():
        raise RuntimeError("OpenAI NLU disabled")

    client = _get_client()
    model = DEFAULT_MODEL_MINI if force_model == "mini" else DEFAULT_MODEL_NANO

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": _instructions()},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "USER_MESSAGE": user_text,
                        "last_question_id": last_question_id,
                        "question_text": question_text,
                        "allowed_values": allowed_values,
                        "slot_snapshot": slot_snapshot or {},
                        "mode": mode,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        max_output_tokens=MAX_OUTPUT_TOKENS,
        text={
            "format": {
                "type": "json_schema",
                "name": "soficca_nlu",
                "strict": True,
                "schema": _nlu_schema(),
            }
        },
    )

    raw = response.output_text
    data = json.loads(raw)

    usage_obj = getattr(response, "usage", None)
    if hasattr(usage_obj, "model_dump"):
        usage = usage_obj.model_dump()
    elif hasattr(usage_obj, "to_dict"):
        usage = usage_obj.to_dict()
    elif hasattr(usage_obj, "__dict__"):
        usage = dict(usage_obj.__dict__)
    else:
        usage = usage_obj

    data["_meta"] = {
        "model": model,
        "response_id": getattr(response, "id", None),
        "usage": usage,
    }

    return data


def pick_model_for_confidence(confidence: float, *, used_model: str) -> Tuple[bool, str]:
    # If nano is low confidence -> upgrade to mini
    if used_model == "nano":
        return (confidence >= CONF_NANO_MIN), "mini"
    return (confidence >= CONF_MINI_MIN), "mini"
