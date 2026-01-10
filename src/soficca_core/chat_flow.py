from soficca_core.chat_state import (
    PHASE_INTRO,
    PHASE_REASON,
    PHASE_SYMPTOMS,
    PHASE_CONTEXT,
    PHASE_INTERPRETATION,
    PHASE_ACTION,
    PHASE_END,
    Q_REASON,
    Q_MAIN_ISSUE,
    Q_FREQUENCY,
    Q_DESIRE,
    Q_STRESS,
    Q_MORNING_ERECTION,
)

from soficca_core import messages_en as messages


def next_question_id(state):
    slots = state["slots"]
    phase = state["phase"]

    if phase == PHASE_INTRO:
        return Q_REASON

    if phase == PHASE_REASON:
        if not slots.get("reason"):
            return Q_REASON
        return Q_MAIN_ISSUE

    if phase == PHASE_SYMPTOMS:
        if not slots.get("main_issue"):
            return Q_MAIN_ISSUE
        if not slots.get("frequency"):
            return Q_FREQUENCY
        if not slots.get("desire"):
            return Q_DESIRE
        return Q_STRESS

    if phase == PHASE_CONTEXT:
        if not slots.get("stress"):
            return Q_STRESS
        if not slots.get("morning_erection"):
            return Q_MORNING_ERECTION
        return None

    return None


def ensure_phase_progress(state):
    slots = state["slots"]
    phase = state["phase"]

    if phase == PHASE_INTRO:
        state["phase"] = PHASE_REASON
        return state

    if phase == PHASE_REASON and slots.get("reason"):
        state["phase"] = PHASE_SYMPTOMS
        return state

    if phase == PHASE_SYMPTOMS:
        if slots.get("main_issue") and slots.get("frequency") and slots.get("desire"):
            state["phase"] = PHASE_CONTEXT
            return state

    if phase == PHASE_CONTEXT:
        if slots.get("stress") and slots.get("morning_erection"):
            state["phase"] = PHASE_INTERPRETATION
            return state

    return state


def render_question(state, question_id):
    name = (state.get("user") or {}).get("name")

    # On very first assistant turn, we show safe-space + reason prompt together.
    if question_id == Q_REASON:
        if int(state.get("turn", 0)) == 1:
            return messages.safe_space(name) + "\n\n" + messages.ask_reason(name)
        return messages.ask_reason(name)

    if question_id == Q_MAIN_ISSUE:
        return messages.ask_main_issue()

    if question_id == Q_FREQUENCY:
        return messages.ask_frequency()

    if question_id == Q_DESIRE:
        return messages.ask_desire()

    if question_id == Q_STRESS:
        return messages.ask_stress()

    if question_id == Q_MORNING_ERECTION:
        return messages.ask_morning_erection()

    return messages.clarify_soft()


def render_interpretation_and_action(state):
    state["phase"] = PHASE_ACTION
    state["last_question_id"] = None
    return messages.reflect_and_bridge_to_meds()


def render_meds_step_and_close(state):
    state["phase"] = PHASE_END
    state["last_question_id"] = None
    return messages.meds_intro()
