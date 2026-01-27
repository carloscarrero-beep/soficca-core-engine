# src/soficca_core/engine.py
from soficca_core.normalization import normalize
from soficca_core.rules import apply_rules
from soficca_core.validation import validate_input

from soficca_core.chat_state import (
    new_state,
    set_slot,
    get_slot,
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

from soficca_core.nlu_specs import QUESTION_SPECS

ENGINE_VERSION = "0.1.0"
RULESET_VERSION = "0.1.0"


def uniq_keep_order(items):
    seen = set()
    out = []
    for x in items or []:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


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


def _apply_slot_fills(state, slot_fills):
    """
    Apply any slot fills extracted by NLU.
    Safety: never overwrite a non-empty slot.
    """
    if not slot_fills:
        return state

    for k, v in (slot_fills or {}).items():
        if v is None:
            continue
        # Only fill if missing (prevents silent overwrites)
        if get_slot(state, k) in (None, "", []):
            set_slot(state, k, v)
    return state


def _question_context(question_id):
    spec = QUESTION_SPECS.get(question_id) or {}
    return spec.get("question_text"), spec.get("allowed_values")


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
        meta.setdefault("repair_counts", {})  # per-question repair counter (anti-loop)

        assistant_message = None
        global_intent = interpret(chat_text, "global")

        # ---------------- SAFETY LOCK ----------------
        red_flags_now = detect_red_flags(chat_text)
        if red_flags_now:
            state["mode"] = MODE_SAFETY_LOCK
            existing = state.get("safety_flags") or []
            state["safety_flags"] = uniq_keep_order(existing + red_flags_now)

        # ---------------- SAFETY FLOW ----------------
        if state.get("mode") == MODE_SAFETY_LOCK:
            last_q = state.get("last_question_id")

            if last_q == Q_COUNTRY:
                qt, av = _question_context(Q_COUNTRY)
                parsed = interpret(chat_text, Q_COUNTRY, state=state, question_text=qt, allowed_values=av)
                # slot fills (if any)
                state = _apply_slot_fills(state, parsed.get("slot_fills"))
                if parsed.get("type") == "answer" and parsed.get("value"):
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
                    assistant_message = messages.meta_ack_waiting_files() + "\n\n" + messages.safety_escalation_with_country(country)
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
            report["recommendations"] = (decision.get("recommendations", []) or []) + ["Escalate to human support / urgent care guidance."]
            report["trace"] = {
                "intermittent_pattern": signals.get("intermittent_pattern"),
                "morning_erection_reduced": signals.get("morning_erection_reduced"),
                "user_requests_meds": signals.get("user_requests_meds"),
            }
            report["path"] = "PATH_ESCALATE_HUMAN"

            chat_payload = {"phase": state.get("phase"), "assistant_message": assistant_message, "last_question_id": state.get("last_question_id"), "done": done, "intent": global_intent.get("type")}
            chat_payload["state"] = state if debug else _chat_state_public(state)
            report["chat"] = chat_payload

            return {"ok": True, "errors": [], "normalized_input": normalized_input, "report": report}

        # ---------------- NORMAL FLOW ----------------

        if meta.get("awaiting_files") and global_intent.get("type") not in ("meta_pause", "file_handoff"):
            meta["awaiting_files"] = False

        # Meta pause / file handoff: ack and keep the same pending question
        if global_intent.get("type") in ("meta_pause", "file_handoff"):
            meta["awaiting_files"] = True
            last_q = state.get("last_question_id")
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

        # Greeting: greet back, then re-ask pending question
        if assistant_message is None and global_intent.get("type") == "greeting":
            last_q = state.get("last_question_id")
            name = _get_name_from_state(state)
            if last_q:
                assistant_message = messages.greet_back(name) + "\n\n" + render_question(state, last_q)
            else:
                state = ensure_phase_progress(state)

        if assistant_message is None:
            state = ensure_phase_progress(state)

        # Interpretation bridge
        if assistant_message is None and state.get("phase") == PHASE_INTERPRETATION:
            assistant_message = render_interpretation_and_action(state)

        if assistant_message is None:
            last_q = state.get("last_question_id")

            if last_q:
                # Anti-loop: after 2 repairs, force mini for better disambiguation
                repairs = int((meta.get("repair_counts") or {}).get(last_q, 0))
                force_model = "mini" if repairs >= 2 else None

                qt, av = _question_context(last_q)
                parsed = interpret(chat_text, last_q, state=state, question_text=qt, allowed_values=av, force_model=force_model)

                # Apply multi-slot fills first (big win)
                state = _apply_slot_fills(state, parsed.get("slot_fills"))

                # If NLU filled the last_q slot via slot_fills, treat as answer.
                if parsed.get("type") != "answer":
                    maybe_v = (parsed.get("slot_fills") or {}).get(last_q)
                    if maybe_v is not None:
                        parsed = {"type": "answer", "value": maybe_v, "confidence": "moderate"}

                if parsed.get("type") == "user_question":
                    assistant_message = messages.answer_user_question_brief() + "\n\n" + render_question(state, last_q)

                elif parsed.get("type") == "emotional":
                    assistant_message = messages.emotional_validation() + "\n\n" + render_question(state, last_q)

                elif parsed.get("type") != "answer" or parsed.get("value") is None:
                    # repair loop counter
                    rc = meta.setdefault("repair_counts", {})
                    rc[last_q] = int(rc.get(last_q, 0)) + 1

                    assistant_message = render_repair_question(state, last_q)

                else:
                    # reset repair count on successful parse
                    rc = meta.setdefault("repair_counts", {})
                    rc[last_q] = 0

                    # Route choice finalize
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
                        assistant_message = None

            # Meds intent any time
            if assistant_message is None and state.get("phase") != PHASE_END:
                if global_intent.get("type") == "meds_intent":
                    set_slot(state, "wants_meds", True)
                    assistant_message = render_meds_step_and_close(state)

            # Ask next question
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

        # Decision layer
        signals = normalize(state.get("slots", {}))
        decision = apply_rules(signals)

        report["flags"] = uniq_keep_order(decision.get("flags", []))
        report["recommendations"] = decision.get("recommendations", [])
        report["reasons"] = decision.get("reasons", [])
        report["trace"] = {
            "intermittent_pattern": signals.get("intermittent_pattern"),
            "morning_erection_reduced": signals.get("morning_erection_reduced"),
            "user_requests_meds": signals.get("user_requests_meds"),
        }
        report["path"] = decision.get("path", "PATH_MORE_QUESTIONS")

        # Eval-first override
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
        errors = [{
            "code": "UNEXPECTED_ERROR",
            "message": "Unexpected error while generating report",
            "path": "$",
            "meta": {"type": type(e).__name__},
        }]
        return {"ok": False, "errors": errors, "normalized_input": {}, "report": _empty_report()}




