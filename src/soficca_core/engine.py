# src/soficca_core/engine.py
import re
from soficca_core.normalization import normalize
from soficca_core.rules import apply_rules
from soficca_core.validation import validate_input

from soficca_core.chat_state import (
    new_state,
    set_slot,
    MODE_SAFETY_LOCK,
    PHASE_END,
    PHASE_INTERPRETATION,
    Q_COUNTRY,
    Q_ROUTE_CHOICE,
)
from soficca_core.chat_flow import (
    ensure_phase_progress,
    next_question_id,
    render_question,
    render_repair_question,
    render_interpretation_and_action,
    render_meds_step_and_close,
)

from soficca_core.interpret_en import interpret
from soficca_core.safety_en import detect_red_flags
from soficca_core import messages_en as messages

ENGINE_VERSION = "0.2.1"
RULESET_VERSION = "0.1.0"


def uniq_keep_order(items):
    seen = set()
    out = []
    for x in items or []:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _nullish_to_none(v):
    if isinstance(v, str) and v.strip().lower() in ("null", "none", "n/a", "na"):
        return None
    return v

def _empty_report():
    return {
        "engine_version": ENGINE_VERSION,
        "ruleset_version": RULESET_VERSION,
        "path": None,
        "scores": {},
        "flags": [],
        "recommendations": [],
        "reasons": [],
        "trace": {},
        "chat": {},
    }


def _get_name_from_state(state):
    return (state.get("slots") or {}).get("name") or (state.get("user") or {}).get("name")


def _chat_state_public(state):
    return {
        "mode": state.get("mode", "NORMAL"),
        "phase": state.get("phase"),
        "slots": state.get("slots", {}),
        "last_question_id": state.get("last_question_id"),
        "turn": state.get("turn", 0),
        "end_reason": state.get("end_reason"),
        "safety_flags": state.get("safety_flags", []),
        "meta": state.get("meta", {}),
    }


def _update_trace_from_parse(report, parsed):
    try:
        t = (parsed or {}).get("_trace") or {}
        if not t:
            return
        trace = report.setdefault("trace", {})
        for k in ("nlu_used", "nlu_meta", "nlu_confidence"):
            if k in t:
                trace[k] = t.get(k)
    except Exception:
        return


def _apply_slot_fills(state, slot_fills, *, fill_only_if_empty=True):
    if not slot_fills:
        return
    slots = state.get("slots") or {}
    for k, v in (slot_fills or {}).items():
        v = _nullish_to_none(v)
        if v is None:
            continue
        if fill_only_if_empty and slots.get(k) not in (None, "", []):
            continue
        set_slot(state, k, v)


def _increment_repair_count(state, question_id: str) -> int:
    meta = state.setdefault("meta", {})
    rc = meta.setdefault("repair_counts", {})
    rc[question_id] = int(rc.get(question_id, 0)) + 1
    return rc[question_id]


def _repair_count(state, question_id: str) -> int:
    meta = state.get("meta") or {}
    rc = meta.get("repair_counts") or {}
    return int(rc.get(question_id, 0))


_Q_RE = re.compile(
    r"^\s*(what|why|how|can you|could you|should i|do you|is it|are you|"
    r"que|qué|por qué|porque|cómo|como|puedes|debo)\b",
    re.IGNORECASE,
)


def _looks_like_question(text: str) -> bool:
    if not text:
        return False
    if "?" in text:
        return True
    return bool(_Q_RE.search(text))


def generate_report(input_data):
    errors = []
    normalized_input = {}
    report = _empty_report()

    try:
        errors, cleaned = validate_input(input_data)
        ok = len(errors) == 0
        if not ok:
            return {"ok": False, "errors": errors, "normalized_input": {}, "report": report}

        normalized_input = {
            "user": cleaned.get("user") or {},
            "measurements": cleaned.get("measurements") or [],
            "context": cleaned.get("context") or {},
        }

        user = normalized_input["user"]
        context = normalized_input["context"]
        chat_text = context.get("chat_text", "")
        debug = bool(context.get("debug", False))

        state = context.get("chat_state") or new_state(user_profile=user)
        state["turn"] = int(state.get("turn", 0)) + 1

        meta = state.setdefault("meta", {})
        meta.setdefault("safe_space_shown", False)
        meta.setdefault("welcomed", False)
        meta.setdefault("awaiting_files", False)
        meta.setdefault("unknown_slot_writes", [])
        meta.setdefault("repair_counts", {})

        assistant_message = None

        global_intent = interpret(chat_text, "global", state=state)
        _update_trace_from_parse(report, global_intent)

        red_flags_now = detect_red_flags(chat_text)
        if red_flags_now:
            state["mode"] = MODE_SAFETY_LOCK
            existing = state.get("safety_flags") or []
            state["safety_flags"] = uniq_keep_order(existing + red_flags_now)

        # ---------------- SAFETY FLOW ----------------
        if state.get("mode") == MODE_SAFETY_LOCK:
            last_q = state.get("last_question_id")
            parsed = None
            if last_q == Q_COUNTRY:
                parsed = interpret(chat_text, Q_COUNTRY, state=state)
                # normalize nullish strings from NLU
                if isinstance(parsed, dict):
                    parsed["value"] = _nullish_to_none(parsed.get("value"))
                _update_trace_from_parse(report, parsed)
                _apply_slot_fills(state, (parsed or {}).get("slot_fills") or {}, fill_only_if_empty=False)
                if parsed.get("type") == "answer" and parsed.get("value") is not None:
                    set_slot(state, "country", parsed["value"])
                    state["last_question_id"] = None

            country = (state.get("slots") or {}).get("country")

            if global_intent.get("type") in ("meta_pause", "file_handoff"):
                meta["awaiting_files"] = True
                if not country:
                    assistant_message = messages.meta_ack_waiting_then_ask_country()
                    state["last_question_id"] = Q_COUNTRY
                    done = False
                else:
                    assistant_message = (
                        messages.meta_ack_waiting_files()
                        + "\n\n"
                        + messages.safety_escalation_with_country(country)
                    )
                    state["last_question_id"] = None
                    state["phase"] = PHASE_END
                    done = True
            else:
                if not country:
                    assistant_message = messages.safety_need_country()
                    state["last_question_id"] = Q_COUNTRY
                    done = False
                else:
                    assistant_message = messages.safety_escalation_with_country(country)
                    state["last_question_id"] = None
                    state["phase"] = PHASE_END
                    done = True

            signals = normalize(state.get("slots", {}))
            decision = apply_rules(signals)

            report["flags"] = uniq_keep_order((decision.get("flags", []) or []) + (state.get("safety_flags") or []))
            report["reasons"] = (decision.get("reasons", []) or []) + ["Red flag signals detected; escalation required."]
            report["recommendations"] = (decision.get("recommendations", []) or []) + [
                "Escalate to human support / urgent care guidance."
            ]

            last_nlu = (state.get("meta") or {}).get("last_nlu") or {}
            report["trace"].update(
                {
                    "intermittent_pattern": signals.get("intermittent_pattern"),
                    "morning_erection_reduced": signals.get("morning_erection_reduced"),
                    "user_requests_meds": signals.get("user_requests_meds"),
                }
            )
            if last_nlu:
                report["trace"].update(
                    {
                        "nlu_used": last_nlu.get("nlu_used"),
                        "nlu_error": last_nlu.get("nlu_error"),
                        "nlu_meta": last_nlu.get("nlu_meta"),
                        "nlu_stage": last_nlu.get("stage"),
                        "nlu_question_id": last_nlu.get("question_id"),
                        "nlu_confidence": last_nlu.get("confidence"),
                    }
                )

            report["path"] = "PATH_ESCALATE_HUMAN"

            chat_payload = {
                "phase": state.get("phase"),
                "assistant_message": assistant_message,
                "last_question_id": state.get("last_question_id"),
                "done": done,
                "intent": global_intent.get("type"),
            }
            chat_payload["state"] = state if debug else _chat_state_public(state)
            report["chat"] = chat_payload

            return {"ok": True, "errors": [], "normalized_input": normalized_input, "report": report}

        # ---------------- NORMAL FLOW ----------------



        # If the conversation already ended and user says thanks, acknowledge (do not reopen flow).
        if state.get("phase") == PHASE_END and global_intent.get("type") == "gratitude":
            name = _get_name_from_state(state)
            assistant_message = messages.end_thanks(name=name)
        if meta.get("awaiting_files") and global_intent.get("type") not in ("meta_pause", "file_handoff"):
            meta["awaiting_files"] = False

        last_q = state.get("last_question_id")

        # Meta / file: ack then keep going
        if global_intent.get("type") in ("meta_pause", "file_handoff"):
            meta["awaiting_files"] = True
            if last_q:
                assistant_message = messages.meta_ack_waiting_files() + "\n\n" + render_question(state, last_q)
            else:
                state = ensure_phase_progress(state)
                qid = next_question_id(state)
                if qid:
                    state["last_question_id"] = qid
                    assistant_message = messages.meta_ack_waiting_files() + "\n\n" + render_question(state, qid)
                else:
                    assistant_message = messages.meta_ack_waiting_files()

        # Greeting: never "steals" the turn. If it answered pending question, ask next question same turn.
        if assistant_message is None and global_intent.get("type") == "greeting":
            name = _get_name_from_state(state)

            if last_q:
                parsed = interpret(chat_text, last_q, state=state)
                # normalize nullish strings from NLU
                if isinstance(parsed, dict):
                    parsed["value"] = _nullish_to_none(parsed.get("value"))
                _update_trace_from_parse(report, parsed)
                _apply_slot_fills(state, (parsed or {}).get("slot_fills") or {}, fill_only_if_empty=False)

                if parsed.get("type") == "answer" and parsed.get("value") is not None:
                    set_slot(state, last_q, parsed.get("value"))
                    state["last_question_id"] = None
                    name = _get_name_from_state(state)
                    state = ensure_phase_progress(state)

                    qid = next_question_id(state)
                    if qid:
                        state["last_question_id"] = qid
                        assistant_message = messages.greet_back(name) + "\n\n" + render_question(state, qid)
                    else:
                        assistant_message = messages.greet_back(name)
                else:
                    assistant_message = messages.greet_back(name) + "\n\n" + render_question(state, last_q)
            else:
                assistant_message = messages.greet_back(name)

        if assistant_message is None:
            state = ensure_phase_progress(state)

        if assistant_message is None and state.get("phase") == PHASE_INTERPRETATION:
            assistant_message = render_interpretation_and_action(state)

        if assistant_message is None:
            last_q = state.get("last_question_id")

            if last_q:
                parsed = interpret(chat_text, last_q, state=state)
                # normalize nullish strings from NLU
                if isinstance(parsed, dict):
                    parsed["value"] = _nullish_to_none(parsed.get("value"))
                _update_trace_from_parse(report, parsed)
                _apply_slot_fills(state, (parsed or {}).get("slot_fills") or {}, fill_only_if_empty=False)

                # If NLU explicitly asks for repair, do not advance.
                if parsed.get("needs_repair"):
                    name = _get_name_from_state(state)
                    c = _repair_count(state, last_q)
                    if c == 0:
                        _increment_repair_count(state, last_q)
                        assistant_message = messages.clarify_once_for_question(last_q, name=name)
                    else:
                        assistant_message = render_repair_question(state, last_q)


                if parsed.get("type") == "user_question" and _looks_like_question((parsed.get("value") or chat_text)):
                    assistant_message = messages.answer_user_question_brief() + "\n\n" + render_question(state, last_q)

                elif parsed.get("type") == "emotional":
                    assistant_message = messages.emotional_validation() + "\n\n" + render_question(state, last_q)

                elif parsed.get("type") == "answer" and parsed.get("value") is not None:
                    if last_q == Q_ROUTE_CHOICE:
                        choice = parsed.get("value")
                        name = _get_name_from_state(state)

                        _signals = normalize(state.get("slots", {}))
                        _decision = apply_rules(_signals)
                        needs_eval_parallel = "needs_eval_parallel" in (_decision.get("flags", []) or [])

                        state["phase"] = PHASE_END
                        state["last_question_id"] = None
                        state["end_reason"] = "END_MEDS_OPTIONS" if choice == "meds" else "END_SUPPORT_PLAN"

                        if choice == "meds":
                            assistant_message = messages.end_meds_options(name=name, needs_eval_parallel=needs_eval_parallel)
                        else:
                            assistant_message = messages.end_support_plan(name=name)
                    else:
                        set_slot(state, last_q, parsed["value"])
                        state["last_question_id"] = None
                        assistant_message = None

                else:
                    name = _get_name_from_state(state)
                    c = _repair_count(state, last_q)
                    if c == 0:
                        _increment_repair_count(state, last_q)
                        assistant_message = messages.clarify_once_for_question(last_q, name=name)
                    else:
                        assistant_message = render_repair_question(state, last_q)

            if assistant_message is None and state.get("phase") != PHASE_END:
                if global_intent.get("type") == "meds_intent":
                    set_slot(state, "wants_meds", True)
                    assistant_message = render_meds_step_and_close(state)

            if assistant_message is None and state.get("phase") != PHASE_END:
                state = ensure_phase_progress(state)
                if state.get("phase") == PHASE_INTERPRETATION:
                    assistant_message = render_interpretation_and_action(state)
                else:
                    qid = next_question_id(state)
                    if qid:
                        state["last_question_id"] = qid
                        assistant_message = render_question(state, qid)
                    else:
                        assistant_message = messages.clarify_soft()

        signals = normalize(state.get("slots", {}))
        decision = apply_rules(signals)

        report["flags"] = uniq_keep_order(decision.get("flags", []))
        report["recommendations"] = decision.get("recommendations", [])
        report["reasons"] = decision.get("reasons", [])
        last_nlu = (state.get("meta") or {}).get("last_nlu") or {}

        report["trace"].update(
            {
                "intermittent_pattern": signals.get("intermittent_pattern"),
                "morning_erection_reduced": signals.get("morning_erection_reduced"),
                "user_requests_meds": signals.get("user_requests_meds"),
            }
        )
        if last_nlu:
            report["trace"].update(
                {
                    "nlu_used": last_nlu.get("nlu_used"),
                    "nlu_error": last_nlu.get("nlu_error"),
                    "nlu_meta": last_nlu.get("nlu_meta"),
                    "nlu_stage": last_nlu.get("stage"),
                    "nlu_question_id": last_nlu.get("question_id"),
                    "nlu_confidence": last_nlu.get("confidence"),
                }
            )

        report["path"] = decision.get("path", "PATH_MORE_QUESTIONS")

        if state.get("phase") != PHASE_END and report["path"] == "PATH_EVAL_FIRST":
            name = _get_name_from_state(state)
            state["phase"] = PHASE_END
            state["last_question_id"] = None
            state["end_reason"] = "END_EVAL_FIRST"
            assistant_message = messages.end_eval_first(name=name)

        chat_payload = {
            "phase": state.get("phase"),
            "assistant_message": assistant_message,
            "last_question_id": state.get("last_question_id"),
            "done": state.get("phase") == PHASE_END,
            "intent": global_intent.get("type"),
        }
        chat_payload["state"] = state if debug else _chat_state_public(state)
        report["chat"] = chat_payload

        return {"ok": True, "errors": [], "normalized_input": normalized_input, "report": report}

    except Exception as e:
        errors = [
            {
                "code": "UNEXPECTED_ERROR",
                "message": "Unexpected error while generating report",
                "path": "$",
                "meta": {"type": type(e).__name__},
            }
        ]
        return {"ok": False, "errors": errors, "normalized_input": {}, "report": _empty_report()}