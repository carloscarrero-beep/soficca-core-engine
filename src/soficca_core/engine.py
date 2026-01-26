from soficca_core.normalization import normalize
from soficca_core.rules import apply_rules

from soficca_core.validation import validate_input

from soficca_core.chat_state import new_state, set_slot
from soficca_core.chat_flow import (
    ensure_phase_progress,
    next_question_id,
    render_question,
    render_interpretation_and_action,
    render_meds_step_and_close,
)

from soficca_core.interpret_en import interpret
from soficca_core import messages_en as messages


def _empty_report():
    return {
        "path": None,
        "scores": {},
        "flags": [],
        "recommendations": [],
        "reasons": [],
        "chat": {},
    }


def generate_report(input_data):
    errors = []
    normalized_input = {}
    report = _empty_report()

    try:
        errors, cleaned = validate_input(input_data)
        ok = len(errors) == 0
        if not ok:
            return {
                "ok": False,
                "errors": errors,
                "normalized_input": {},
                "report": report,
            }

        normalized_input = {
            "user": cleaned.get("user") or {},
            "measurements": cleaned.get("measurements") or [],
            "context": cleaned.get("context") or {},
        }

        user = normalized_input["user"]
        context = normalized_input["context"]
        chat_text = context.get("chat_text", "")
        state = context.get("chat_state") or new_state(user_profile=user)

        # Turn counter (assistant turns)
        state["turn"] = int(state.get("turn", 0)) + 1

        assistant_message = None

        # First: keep phases consistent with what we already have
        state = ensure_phase_progress(state)

        # If we've collected the essentials, produce the interpretation/action bridge
        if state.get("phase") == "INTERPRETATION":
            assistant_message = render_interpretation_and_action(state)

        else:
            # If we asked something before, attempt to interpret the user's reply
            last_q = state.get("last_question_id")

            if last_q:
                parsed = interpret(chat_text, last_q)

                if parsed["type"] == "user_question":
                    assistant_message = messages.answer_user_question_brief()

                elif parsed["type"] == "emotional":
                    assistant_message = messages.emotional_validation()

                elif parsed["type"] == "ambiguous":
                    assistant_message = messages.clarify_soft()

                else:
                    # Save value into the matching slot key (we use same ids)
                    set_slot(state, last_q, parsed["value"])
                    assistant_message = None

            # Global meds intent (can appear any time)
            meds_probe = interpret(chat_text, "any")
            if meds_probe["type"] == "answer" and meds_probe.get("value") is True:
                set_slot(state, "wants_meds", True)
                assistant_message = render_meds_step_and_close(state)

            # If we still don't have a message, ask the next guided-open question
            if assistant_message is None:
                state = ensure_phase_progress(state)

                if state.get("phase") == "INTERPRETATION":
                    assistant_message = render_interpretation_and_action(state)
                else:
                    qid = next_question_id(state)
                    state["last_question_id"] = qid
                    assistant_message = render_question(state, qid)

        # DS layer: slots -> signals -> decision
        signals = normalize(state.get("slots", {}))
        decision = apply_rules(signals)

        report["flags"] = decision.get("flags", [])
        report["recommendations"] = decision.get("recommendations", [])
        report["reasons"] = decision.get("reasons", [])
        report["path"] = decision.get("path", "PATH_MORE_QUESTIONS")

        report["chat"] = {
            "phase": state.get("phase"),
            "assistant_message": assistant_message,
            "last_question_id": state.get("last_question_id"),
            "done": state.get("phase") == "END",
            "state": state,  # OK for demo; later you can remove or sanitize for privacy
        }

        return {
            "ok": True,
            "errors": [],
            "normalized_input": normalized_input,  # ✅ now populated
            "report": report,
        }

    except Exception as e:
        errors = [{
            "code": "UNEXPECTED_ERROR",
            "message": "Unexpected error while generating report",
            "path": "$",
            "meta": {"type": type(e).__name__},
        }]
        return {
            "ok": False,
            "errors": errors,
            "normalized_input": {},
            "report": _empty_report(),
        }

