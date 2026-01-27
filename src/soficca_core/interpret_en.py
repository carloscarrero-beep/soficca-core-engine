# src/soficca_core/interpret_en.py
"""
Deterministic + (optional) OpenAI-backed NLU interpreter.

Why:
- Deterministic rules are fast and cheap, but they will always miss edge cases.
- OpenAI (Structured Outputs) is used ONLY as an interpreter (NLU), never to write clinical replies.

Engine usage:
- interpret(chat_text, "global") -> intent classification
- interpret(chat_text, last_question_id, state=..., question_text=..., allowed_values=..., force_model=...) -> slot parsing
"""
from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Any, Dict, Optional

from soficca_core.nlu_specs import QUESTION_SPECS

# Optional OpenAI NLU
try:
    from soficca_core.nlu_openai import call_openai_nlu, pick_model_for_confidence
except Exception:  # pragma: no cover
    call_openai_nlu = None  # type: ignore
    pick_model_for_confidence = None  # type: ignore


# -----------------------------
# Mode
# -----------------------------
# "deterministic" -> never call OpenAI
# "hybrid" -> deterministic first, OpenAI fallback on ambiguity / multi-slot
NLU_MODE = os.getenv("SOFICCA_NLU_MODE", "hybrid").lower().strip()


# -----------------------------
# Helpers
# -----------------------------
def _clean(user_text: str) -> tuple[str, str]:
    text = (user_text or "").strip()
    lower = text.lower()
    return text, lower


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _looks_like_question(text: str) -> bool:
    if "?" in text:
        return True
    return bool(
        re.match(
            r"^\s*(what|why|how|can you|could you|should i|que|qué|por qué|porque|cómo|como|puedes|debo)\b",
            text,
            re.IGNORECASE,
        )
    )


# Short confirmations (EN/ES)
_YES_WORDS = {
    "yes",
    "yep",
    "yeah",
    "y",
    "sure",
    "ok",
    "okay",
    "correct",
    "right",
    "exactly",
    "thats it",
    "that's it",
    "si",
    "sí",
    "claro",
    "vale",
    "okey",
    "exacto",
    "tal cual",
    "asi",
    "así",
    "correcto",
}
_NO_WORDS = {"no", "nope", "nah", "not", "not really", "never", "para nada", "nunca", "no realmente"}
_MAYBE_WORDS = {
    "maybe",
    "perhaps",
    "kinda",
    "sort of",
    "a bit",
    "somewhat",
    "depends",
    "quizas",
    "quizás",
    "tal vez",
    "puede ser",
    "mas o menos",
    "más o menos",
    "depende",
    "un poco",
}


def _short_yes_no_maybe(text: str) -> str | None:
    """
    Detects short confirmations like: yes/no/kinda/depende.
    Returns: "yes" | "no" | "maybe" | None
    """
    t = (text or "").strip().lower()

    # exact match
    if t in _YES_WORDS:
        return "yes"
    if t in _NO_WORDS:
        return "no"
    if t in _MAYBE_WORDS:
        return "maybe"

    # fuzzy (only if message is short)
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


_EMOTIONAL_RE = re.compile(
    r"\b(anxious|stressed|ashamed|embarrassed|worried|sad|ansioso|estresado|avergonzado|preocupado|triste)\b",
    re.IGNORECASE,
)
_MEDS_RE = re.compile(
    r"\b(meds|medication|pill|treatment|prescription|sildenafil|tadalafil|viagra|cialis|pastilla|medicamento|tratamiento|receta)\b",
    re.IGNORECASE,
)

_GREETING_RE = re.compile(r"^\s*(hi|hello|hey|hola|buenas|buenos días|buenas tardes|buenas noches)\b", re.IGNORECASE)
_META_PAUSE_RE = re.compile(r"\b(wait|hold on|give me a moment|one sec|sec|pause|espera|espere|un momento|dame un momento|aguanta)\b", re.IGNORECASE)
_FILE_HANDOFF_RE = re.compile(r"\b(send|sending|share|upload|files|file|logs|repo|github|te mando|te enviar(e|é)|voy a mandar|voy a enviar|subiendo|adjunto|archivos)\b", re.IGNORECASE)


# Name extraction patterns
_NAME_PATTERNS = [
    re.compile(r"^\s*i\s*['’]?\s*m\s+(?P<name>.+)\s*$", re.IGNORECASE),  # I'm Carlos
    re.compile(r"^\s*i\s*am\s+(?P<name>.+)\s*$", re.IGNORECASE),  # I am Carlos
    re.compile(r"^\s*my\s+name\s+is\s+(?P<name>.+)\s*$", re.IGNORECASE),  # my name is Carlos
    re.compile(r"^\s*soy\s+(?P<name>.+)\s*$", re.IGNORECASE),  # soy Carlos
    re.compile(r"^\s*me\s+llamo\s+(?P<name>.+)\s*$", re.IGNORECASE),  # me llamo Carlos
    re.compile(r"^\s*mi\s+nombre\s+es\s+(?P<name>.+)\s*$", re.IGNORECASE),  # mi nombre es Carlos
]

# Country extraction patterns
_COUNTRY_PATTERNS = [
    re.compile(r"^\s*i\s*['’]?\s*m\s+in\s+(?P<country>.+)\s*$", re.IGNORECASE),  # I'm in Colombia
    re.compile(r"^\s*i\s+am\s+in\s+(?P<country>.+)\s*$", re.IGNORECASE),
    re.compile(r"^\s*estoy\s+en\s+(?P<country>.+)\s*$", re.IGNORECASE),  # estoy en Colombia
    re.compile(r"^\s*en\s+(?P<country>.+)\s*$", re.IGNORECASE),  # en Colombia
]


def _first_segment(raw: str) -> str:
    """
    Prevent bad captures like: "Carlos, male, from Colombia" -> "Carlos"
    """
    if not raw:
        return raw
    # Split on commas / semicolons / "from" / "de" / "in"
    s = raw.strip()
    s = re.split(r"[;,]|(\bfrom\b)|(\ben\b)|(\bde\b)|(\bin\b)", s, maxsplit=1, flags=re.IGNORECASE)[0]
    return s.strip()


def _normalize_name(raw: str) -> str | None:
    if not raw:
        return None
    s = _first_segment(raw)

    # Remove filler, punctuation
    s = re.sub(r"[^\w\s\-’']", "", s)  # keep letters, spaces, hyphen
    s = re.sub(r"\s+", " ", s).strip()

    # too long becomes suspicious
    if len(s) < 2 or len(s) > 40:
        return None
    # avoid capturing whole sentences
    if len(s.split()) > 3:
        return None
    return " ".join([p.capitalize() for p in s.split()])


def _extract_name(text: str) -> str | None:
    for pat in _NAME_PATTERNS:
        m = pat.match(text)
        if m:
            return _normalize_name(m.group("name"))

    # If user started with greeting and then name: "Hi, I'm Carlos"
    m2 = re.search(r"\b(i\s*['’]?\s*m|i\s+am|soy|me\s+llamo)\s+(?P<name>[^,.;\n]+)", text, re.IGNORECASE)
    if m2:
        return _normalize_name(m2.group("name"))

    # If user just typed a single token like "Carlos"
    simple = _normalize_name(text)
    if simple and len(simple.split()) <= 2:
        return simple
    return None


def _extract_country(text: str) -> str | None:
    t = (text or "").strip()
    for pat in _COUNTRY_PATTERNS:
        m = pat.match(t)
        if m:
            c = _first_segment(m.group("country").strip())
            c = re.sub(r"[^\w\s\-\']", "", c)
            c = re.sub(r"\s+", " ", c).strip()
            if 2 <= len(c) <= 56:
                return c
    # fallback accept as-is if short
    if 2 <= len(t) <= 56 and len(t.split()) <= 4:
        return _first_segment(t)
    return None


def _extract_gender_identity(text_lower: str) -> Optional[str]:
    # Returns internal values used by your slots
    if "prefer not" in text_lower or "prefer not to" in text_lower or "prefiero no" in text_lower:
        return "prefer_not_say"
    if "non-binary" in text_lower or "non binary" in text_lower or "no binario" in text_lower:
        return "non_binary"
    if re.search(r"\b(male|man|hombre|masculino)\b", text_lower):
        return "male"
    if re.search(r"\b(female|woman|mujer|femenino)\b", text_lower):
        return "female"
    return None


def _should_call_openai(user_text: str, question_id: str, deterministic: Dict[str, Any]) -> bool:
    if NLU_MODE != "hybrid":
        return False
    if call_openai_nlu is None:
        return False

    # Always use deterministic for global intent; it's good enough and cheaper.
    if question_id == "global":
        return False

    t = (user_text or "").strip()
    if not t:
        return False

    # If deterministic already got a confident answer, skip OpenAI.
    if deterministic.get("type") == "answer" and deterministic.get("confidence") in ("high", "moderate"):
        # Still: if the message likely contains multiple slots (commas / "I'm X, male, in Y"), we can gain value.
        if len(t) <= 40:
            return False
        if "," not in t and " and " not in t.lower() and " y " not in t.lower():
            return False
        return True

    # Ambiguous or not-an-answer: call OpenAI
    return True


def _map_openai_to_interpret(openai_data: Dict[str, Any], *, question_id: str) -> Dict[str, Any]:
    """
    Map OpenAI JSON to your existing engine expectations.
    Returns the usual dict, plus optional `slot_fills`.
    """
    intent = openai_data.get("intent") or "ambiguous"
    ans = openai_data.get("answer_for_last_question") or {}
    slot_fills = openai_data.get("slot_fills") or {}

    out: Dict[str, Any] = {"type": "ambiguous", "value": None, "confidence": "low", "slot_fills": slot_fills}

    if intent in ("user_question", "meta_pause", "file_handoff", "greeting", "emotional"):
        out["type"] = intent
        out["value"] = openai_data.get("answer_for_last_question", {}).get("value") or None
        out["confidence"] = "high" if intent != "user_question" else "high"
        return out

    # intent == answer/ambiguous
    if question_id != "global":
        v = ans.get("value")
        conf = float(ans.get("confidence") or 0.0)
        if v is not None and conf >= 0.65:
            out["type"] = "answer"
            out["value"] = v
            out["confidence"] = "high" if conf >= 0.80 else "moderate"
        else:
            out["type"] = "ambiguous"
            out["value"] = None
            out["confidence"] = "low"

    return out


def interpret(
    user_text: str,
    question_id: str,
    *,
    state: Optional[dict] = None,
    question_text: Optional[str] = None,
    allowed_values: Optional[list] = None,
    force_model: Optional[str] = None,  # None|"nano"|"mini"
) -> Dict[str, Any]:
    """
    Main entrypoint used by engine.

    Returns:
      {type, value, confidence, slot_fills?}
    """
    # 1) Deterministic first (cheap)
    deterministic = _interpret_deterministic(user_text, question_id)

    # 2) Optional OpenAI fallback
    if _should_call_openai(user_text, question_id, deterministic):
        spec = QUESTION_SPECS.get(question_id, {})
        qt = question_text or spec.get("question_text")
        av = allowed_values or spec.get("allowed_values")

        # minimize state sent
        slot_snapshot = {}
        if state:
            slot_snapshot = (state.get("slots") or {}).copy()

        mode = (state or {}).get("mode") if state else None

        # Try nano, then mini if needed
        used = "nano" if force_model != "mini" else "mini"
        try:
            data = call_openai_nlu(
                user_text,
                last_question_id=question_id,
                question_text=qt,
                allowed_values=av,
                slot_snapshot=slot_snapshot,
                mode=mode,
                force_model=force_model or "nano",
            )

            # confidence gating
            ans = data.get("answer_for_last_question") or {}
            conf = float(ans.get("confidence") or 0.0)
            accept = True
            next_force = "nano"
            if pick_model_for_confidence is not None:
                accept, next_force = pick_model_for_confidence(confidence=conf, used_model=used)

            if not accept and next_force == "mini" and force_model != "mini":
                data2 = call_openai_nlu(
                    user_text,
                    last_question_id=question_id,
                    question_text=qt,
                    allowed_values=av,
                    slot_snapshot=slot_snapshot,
                    mode=mode,
                    force_model="mini",
                )
                return _map_openai_to_interpret(data2, question_id=question_id)

            return _map_openai_to_interpret(data, question_id=question_id)

        except Exception:
            # Never crash the engine because of OpenAI failures; keep deterministic output.
            return deterministic

    return deterministic


def _interpret_deterministic(user_text: str, question_id: str) -> Dict[str, Any]:
    text, lower = _clean(user_text)

    # -----------------------------
    # GLOBAL intent classifier
    # -----------------------------
    if question_id == "global":
        if not text:
            return {"type": "ambiguous", "value": None, "confidence": "low"}

        if _META_PAUSE_RE.search(text) and _FILE_HANDOFF_RE.search(text):
            return {"type": "file_handoff", "value": True, "confidence": "high"}
        if _FILE_HANDOFF_RE.search(text):
            return {"type": "file_handoff", "value": True, "confidence": "high"}
        if _META_PAUSE_RE.search(text):
            return {"type": "meta_pause", "value": True, "confidence": "high"}

        if _GREETING_RE.search(text):
            return {"type": "greeting", "value": True, "confidence": "high"}

        if _looks_like_question(text):
            return {"type": "user_question", "value": text, "confidence": "high"}

        if _EMOTIONAL_RE.search(text):
            return {"type": "emotional", "value": text, "confidence": "high"}

        if _MEDS_RE.search(text):
            return {"type": "meds_intent", "value": True, "confidence": "high"}

        return {"type": "unknown", "value": text, "confidence": "low"}

    # -----------------------------
    # Per-question parsing
    # -----------------------------
    if not text:
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    if _looks_like_question(text):
        return {"type": "user_question", "value": text, "confidence": "high"}

    if _EMOTIONAL_RE.search(text):
        return {"type": "emotional", "value": text, "confidence": "high"}

    short = _short_yes_no_maybe(text)

    # name
    if question_id == "name":
        name = _extract_name(text)
        if name:
            # Also try to pick up gender/country if present (cheap win)
            slot_fills = {}
            gi = _extract_gender_identity(lower)
            if gi:
                slot_fills["gender_identity"] = gi
            ctry = None
            if "colombia" in lower or "mexico" in lower or "usa" in lower:
                ctry = _extract_country(text)
            if ctry:
                slot_fills["country"] = ctry
            out = {"type": "answer", "value": name, "confidence": "high"}
            if slot_fills:
                out["slot_fills"] = slot_fills
            return out
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    # country
    if question_id == "country":
        country = _extract_country(text)
        if country:
            return {"type": "answer", "value": country, "confidence": "high"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    # reason (open text)
    if question_id == "reason":
        return {"type": "answer", "value": text, "confidence": "high"}

    # frequency
    if question_id == "frequency":
        sometimes_cues = [
            "sometimes",
            "not always",
            "good days",
            "bad days",
            "on and off",
            "depends",
            "occasionally",
            "a veces",
            "no siempre",
            "depende",
            "ocasionalmente",
            "unas veces",
            "otras veces",
            "buenos días",
            "malos días",
            "buenos y malos",
        ]
        always_cues = [
            "every time",
            "all the time",
            "consistently",
            "always",
            "never works",
            "siempre",
            "cada vez",
            "todo el tiempo",
            "nunca funciona",
        ]
        if any(cue in lower for cue in sometimes_cues):
            return {"type": "answer", "value": "sometimes", "confidence": "high"}
        if any(cue in lower for cue in always_cues):
            return {"type": "answer", "value": "always", "confidence": "high"}
        # if user answers "yes/no" it's ambiguous here
        if short in ("yes", "no", "maybe"):
            return {"type": "ambiguous", "value": None, "confidence": "low"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    # desire
    if question_id == "desire":
        if short == "yes":
            return {"type": "answer", "value": "present", "confidence": "high"}
        if short == "no":
            return {"type": "answer", "value": "reduced", "confidence": "high"}
        if short == "maybe":
            return {"type": "ambiguous", "value": None, "confidence": "low"}

        if re.search(r"\b(still|same|normal|present|igual|normal|presente)\b", lower):
            return {"type": "answer", "value": "present", "confidence": "high"}
        if re.search(r"\b(lower|reduced|less|bajo|reducido|menos)\b", lower):
            return {"type": "answer", "value": "reduced", "confidence": "high"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    # stress
    if question_id == "stress":
        if short in ("yes", "no", "maybe"):
            return {"type": "ambiguous", "value": None, "confidence": "low"}

        if re.search(r"\b(high|very high|overwhelmed|stressed|alto|muy alto|estresado|abrumado|agotado)\b", lower):
            return {"type": "answer", "value": "high", "confidence": "high"}
        if re.search(r"\b(moderate|medium|moderado|medio)\b", lower):
            return {"type": "answer", "value": "moderate", "confidence": "high"}
        if re.search(r"\b(low|normal|fine|bajo|bien)\b", lower):
            return {"type": "answer", "value": "low", "confidence": "high"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    # morning erection
    if question_id == "morning_erection":
        # If user says "no", it's usually "no change" => normal
        if short == "no":
            return {"type": "answer", "value": "normal", "confidence": "high"}
        if short in ("yes", "maybe"):
            return {"type": "ambiguous", "value": None, "confidence": "low"}

        if re.search(r"\b(no change|normal|same as before|igual que antes|sin cambios)\b", lower):
            return {"type": "answer", "value": "normal", "confidence": "high"}
        if re.search(r"\b(rarely|almost never|rara vez|casi nunca)\b", lower):
            return {"type": "answer", "value": "rare", "confidence": "high"}
        if re.search(r"\b(less|reduced|decreased|menos|reducidas|disminuido)\b", lower):
            return {"type": "answer", "value": "reduced", "confidence": "high"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    # main issue
    if question_id == "main_issue":
        if short in ("yes", "no", "maybe"):
            return {"type": "ambiguous", "value": None, "confidence": "low"}

        if re.search(r"\b(lose|losing|pierdo|pierde).*(erection|erección)\b", lower):
            return {"type": "answer", "value": "erection_lost", "confidence": "high"}
        if re.search(r"\b(not last|doesn'?t last|short|no dura|dura poco|muy poco)\b", lower):
            return {"type": "answer", "value": "short_duration", "confidence": "high"}
        if re.search(r"\b(too fast|finish fast|premature|muy rápido|termino rápido|eyaculación precoz)\b", lower):
            return {"type": "answer", "value": "early_ejaculation", "confidence": "moderate"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    # gender identity
    if question_id == "gender_identity":
        gi = _extract_gender_identity(lower)
        if gi:
            return {"type": "answer", "value": gi, "confidence": "high"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    # route choice
    if question_id == "route_choice":
        if re.search(r"\b(med|meds|medication|pill|treatment|prescription|medicamento|pastilla)\b", lower):
            return {"type": "answer", "value": "meds", "confidence": "high"}
        if re.search(r"\b(habit|support|lifestyle|therapy|anxiety|coach|no meds|hábitos|apoyo|sin medicación|sin meds)\b", lower):
            return {"type": "answer", "value": "support", "confidence": "high"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    # default: conservative
    return {"type": "ambiguous", "value": None, "confidence": "low"}






