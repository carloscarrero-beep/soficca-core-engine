# src/soficca_core/interpret_en.py
from __future__ import annotations

from typing import Any, Dict, Optional
import re
from difflib import SequenceMatcher

from soficca_core.nlu_specs import QUESTION_SPECS

from soficca_core.nlu_openai import call_openai_nlu, pick_model_for_confidence
from soficca_core.nlu_openai import ENABLED as OPENAI_NLU_ENABLED


_FAST_PATH_INTENTS = {"meta_pause", "file_handoff" , "gratitude"}  # greeting handled separately

_GREETING_RE = re.compile(r"^\s*(hi|hello|hey|hola|buenas|buenos días|buenas tardes|buenas noches)\b", re.IGNORECASE)
_META_PAUSE_RE = re.compile(r"\b(wait|hold on|give me a moment|one sec|sec|pause|espera|espere|un momento|dame un momento|aguanta)\b", re.IGNORECASE)
_FILE_HANDOFF_RE = re.compile(r"\b(send|sending|share|upload|files|file|logs|repo|github|te mando|te enviar(e|é)|voy a mandar|voy a enviar|subiendo|adjunto|archivos)\b", re.IGNORECASE)

_GRATITUDE_RE = re.compile(r"\b(thanks|thank you|thx|appreciate it|much appreciated|ty)\b", re.IGNORECASE)

_EMOTIONAL_RE = re.compile(r"\b(anxious|stressed|ashamed|embarrassed|worried|sad|ansioso|estresado|avergonzado|preocupado|triste)\b", re.IGNORECASE)
_MEDS_RE = re.compile(r"\b(meds|medication|pill|treatment|prescription|sildenafil|tadalafil|viagra|cialis|pastilla|medicamento|tratamiento|receta)\b", re.IGNORECASE)

_IDK_RE = re.compile(r"\b(i don'?t know|idk|not sure|no idea|i'm unsure|ni idea|no sé|no se|no estoy seguro|no estoy segura)\b", re.IGNORECASE)

_Q_RE = re.compile(
    r"^\s*(what|why|how|can you|could you|should i|do you|is it|are you|"
    r"que|qué|por qué|porque|cómo|como|puedes|debo)\b",
    re.IGNORECASE,
)

_YES_WORDS = {
    "yes", "yep", "yeah", "y", "sure", "ok", "okay", "correct", "right", "exactly", "that's it", "thats it",
    "si", "sí", "claro", "vale", "okey", "exacto", "tal cual", "asi", "así", "correcto",
}
_NO_WORDS = {"no", "nope", "nah", "not", "not really", "never", "para nada", "nunca", "no realmente"}
_MAYBE_WORDS = {"maybe", "perhaps", "kinda", "kind of", "sort of", "a bit", "somewhat", "depends",
                "quizas", "quizás", "tal vez", "puede ser", "mas o menos", "más o menos", "depende", "un poco"}

_FREE_TEXT_SLOTS = {"reason"}


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _looks_like_question(text: str) -> bool:
    if not text:
        return False
    if "?" in text:
        return True
    return bool(_Q_RE.search(text))


def _is_greeting_only(text: str) -> bool:
    t = (text or "").strip()
    if not _GREETING_RE.search(t):
        return False
    t2 = re.sub(_GREETING_RE, "", t, count=1).strip(" ,.!?-")
    return len(t2) == 0


def _short_yes_no_maybe(text: str) -> Optional[str]:
    t = (text or "").strip().lower()
    if t in _YES_WORDS:
        return "yes"
    if t in _NO_WORDS:
        return "no"
    if t in _MAYBE_WORDS:
        return "maybe"
    if len(t) <= 24:
        for w in _MAYBE_WORDS:
            if _ratio(t, w) >= 0.86:
                return "maybe"
        for w in _YES_WORDS:
            if _ratio(t, w) >= 0.90:
                return "yes"
        for w in _NO_WORDS:
            if _ratio(t, w) >= 0.90:
                return "no"
    return None


def _map_short_answer_to_allowed(short: str, allowed_values: Optional[list]) -> Optional[Any]:
    if not allowed_values:
        return None
    av = [str(x).strip().lower() for x in allowed_values if x is not None]
    if short == "yes":
        if "yes" in av:
            return "yes"
        if "true" in av:
            return True
    if short == "no":
        if "no" in av:
            return "no"
        if "false" in av:
            return False
    if short == "maybe":
        if "maybe" in av:
            return "maybe"
    return None


def _interpret_deterministic(user_text: str, question_id: str, *, allowed_values: Optional[list] = None) -> Dict[str, Any]:
    text = (user_text or "").strip()

    if question_id == "global":
        if not text:
            return {"type": "ambiguous", "value": None, "confidence": "low"}

        if _META_PAUSE_RE.search(text) and _FILE_HANDOFF_RE.search(text):
            return {"type": "file_handoff", "value": True, "confidence": "high"}
        if _FILE_HANDOFF_RE.search(text):
            return {"type": "file_handoff", "value": True, "confidence": "high"}
        if _META_PAUSE_RE.search(text):
            return {"type": "meta_pause", "value": True, "confidence": "high"}

        if _is_greeting_only(text):
            return {"type": "greeting", "value": True, "confidence": "high"}

        if _looks_like_question(text):
            return {"type": "user_question", "value": text, "confidence": "high"}

        if _EMOTIONAL_RE.search(text):
            return {"type": "emotional", "value": text, "confidence": "high"}

        if _MEDS_RE.search(text):
            return {"type": "meds_intent", "value": True, "confidence": "high"}

        return {"type": "unknown", "value": text, "confidence": "low"}

    if not text:
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    if _looks_like_question(text):
        return {"type": "user_question", "value": text, "confidence": "high"}

    if _EMOTIONAL_RE.search(text):
        return {"type": "emotional", "value": text, "confidence": "high"}

    if _IDK_RE.search(text):
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    short = _short_yes_no_maybe(text)
    if short in ("yes", "no", "maybe"):
        mapped = _map_short_answer_to_allowed(short, allowed_values)
        if mapped is not None:
            return {"type": "answer", "value": mapped, "confidence": "moderate"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    if question_id in _FREE_TEXT_SLOTS and not allowed_values:
        return {"type": "answer", "value": text, "confidence": "moderate"}

    return {"type": "ambiguous", "value": None, "confidence": "low"}


def interpret(
    user_text: str,
    question_id: str,
    *,
    state: Optional[dict] = None,
    question_text: Optional[str] = None,
    allowed_values: Optional[list] = None,
) -> Dict[str, Any]:
    text = (user_text or "").strip()
    stage = "global" if question_id == "global" else "question"

    spec = QUESTION_SPECS.get(question_id, {})
    qt = question_text or spec.get("question_text")
    av = allowed_values or spec.get("allowed_values")

    if not text:
        out = {"type": "ambiguous", "value": None, "confidence": "low", "nlu_used": "no_user_text"}
        _store_last_nlu(state, out, question_id, stage)
        return out

    det = _interpret_deterministic(text, question_id, allowed_values=av)

    # Fast-path only for meta/file, plus greeting-only in global
    if det.get("type") in _FAST_PATH_INTENTS or (question_id == "global" and det.get("type") == "greeting"):
        det["nlu_used"] = "deterministic_fast"
        _store_last_nlu(state, det, question_id, stage)
        return det

    if OPENAI_NLU_ENABLED():
        slot_snapshot = (state.get("slots") or {}).copy() if state else {}
        mode = (state or {}).get("mode") if state else None

        try:
            data = call_openai_nlu(
                text,
                last_question_id=question_id,
                question_text=qt,
                allowed_values=av,
                slot_snapshot=slot_snapshot,
                mode=mode,
                force_model="nano",
            )

            ans = (data or {}).get("answer_for_last_question") or {}
            conf = float(ans.get("confidence") or 0.0)

            accept, next_force = pick_model_for_confidence(confidence=conf, used_model="nano")
            if (not accept) and next_force == "mini":
                data = call_openai_nlu(
                    text,
                    last_question_id=question_id,
                    question_text=qt,
                    allowed_values=av,
                    slot_snapshot=slot_snapshot,
                    mode=mode,
                    force_model="mini",
                )
                ans = (data or {}).get("answer_for_last_question") or {}
                conf = float(ans.get("confidence") or 0.0)

            intent = (data or {}).get("intent") or "ambiguous"
            value = ans.get("value")
            # Treat string-null as None
            if isinstance(value, str) and value.strip().lower() in ("null", "none", "n/a", "na"):
                value = None
            slot_fills = (data or {}).get("slot_fills") or {}
            if isinstance(slot_fills, dict):
                for _k,_v in list(slot_fills.items()):
                    if isinstance(_v, str) and _v.strip().lower() in ("null", "none", "n/a", "na"):
                        slot_fills[_k] = None

            # --------- Post-processing robustness ----------
            # A) user_question must look like a question
            if intent == "user_question" and not _looks_like_question(text):
                intent = "ambiguous"

            
            # IDK: never counts as an answer for structured slots
            if question_id != "global" and (question_id not in _FREE_TEXT_SLOTS) and _IDK_RE.search(text):
                intent = "ambiguous"
                value = None
                conf = min(conf, 0.40)
                data["needs_repair"] = True
# B) If we have evidence of an answer, force answer.
            if question_id != "global":
                if value is not None:
                    intent = "answer"
                elif isinstance(slot_fills, dict) and slot_fills.get(question_id) is not None:
                    intent = "answer"
                    value = slot_fills.get(question_id)

            # C) Free-text slot: accept normal statements even if model called it ambiguous
            if question_id in _FREE_TEXT_SLOTS and not av:
                if intent not in ("user_question", "emotional", "meta_pause", "file_handoff") and not _IDK_RE.search(text):
                    if intent != "answer":
                        intent = "answer"
                        value = text
                        conf = max(conf, 0.70)

            out: Dict[str, Any] = {
                "type": intent,
                "value": value,
                "confidence": "high" if conf >= 0.80 else ("moderate" if conf >= 0.65 else "low"),
                "slot_fills": slot_fills,
                "needs_repair": data.get("needs_repair"),
                "language": data.get("language"),
                "nlu_used": (data.get("_meta") or {}).get("model") or "openai",
                "nlu_meta": data.get("_meta") or {},
            }

            _store_last_nlu(state, out, question_id, stage)
            return out

        except Exception as e:
            det["nlu_used"] = "openai_error_fallback"
            det["nlu_error"] = f"{type(e).__name__}: {e}"
            _store_last_nlu(state, det, question_id, stage)
            return det

    det["nlu_used"] = "deterministic"
    _store_last_nlu(state, det, question_id, stage)
    return det


def _store_last_nlu(state: Optional[dict], out: Dict[str, Any], question_id: str, stage: str) -> None:
    if state is None:
        return
    meta = state.setdefault("meta", {})
    meta["last_nlu"] = {
        "question_id": question_id,
        "stage": stage,
        "nlu_used": out.get("nlu_used"),
        "confidence": out.get("confidence"),
        "nlu_meta": out.get("nlu_meta"),
        "nlu_error": out.get("nlu_error"),
        "type": out.get("type"),
    }