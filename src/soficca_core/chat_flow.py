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
    Q_NAME,
    Q_GENDER_ID,
    Q_COUNTRY,
    Q_ROUTE_CHOICE,
)

from soficca_core import messages_en as messages


def next_question_id(state):
    slots = state.get("slots") or {}
    phase = state.get("phase")

    if phase == PHASE_INTRO:
        if not slots.get("name"):
            return Q_NAME
        if not slots.get("gender_identity"):
            return Q_GENDER_ID
        if not slots.get("country"):
            return Q_COUNTRY
        return None

    if phase == PHASE_REASON:
        if not slots.get("reason"):
            return Q_REASON
        return None

    if phase == PHASE_SYMPTOMS:
        if not slots.get("main_issue"):
            return Q_MAIN_ISSUE
        if not slots.get("frequency"):
            return Q_FREQUENCY
        if not slots.get("desire"):
            return Q_DESIRE
        return None

    if phase == PHASE_CONTEXT:
        if not slots.get("stress"):
            return Q_STRESS
        if not slots.get("morning_erection"):
            return Q_MORNING_ERECTION
        return None

    return None


def ensure_phase_progress(state):
    slots = state.get("slots") or {}
    phase = state.get("phase")

    if phase == PHASE_INTRO:
        if slots.get("name") and slots.get("gender_identity") and slots.get("country"):
            state["phase"] = PHASE_REASON
        return state

    if phase == PHASE_REASON:
        if slots.get("reason"):
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
    name = (state.get("slots") or {}).get("name") or (state.get("user") or {}).get("name")

    if question_id == Q_NAME:
        return messages.greet() + "\n\n" + messages.ask_name()

    if question_id == Q_GENDER_ID:
        return messages.ask_gender_identity()

    if question_id == Q_COUNTRY:
        return messages.ask_country_general()

    if question_id == Q_REASON:
        meta = state.setdefault("meta", {})
        if not meta.get("safe_space_shown", False):
            meta["safe_space_shown"] = True
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


def render_repair_question(state, question_id):
    name = (state.get("slots") or {}).get("name") or (state.get("user") or {}).get("name")
    return messages.repair_for_question(question_id, name=name)


def render_interpretation_and_action(state):
    state["phase"] = PHASE_ACTION
    state["last_question_id"] = Q_ROUTE_CHOICE
    return messages.ask_route_choice()


def render_meds_step_and_close(state):
    state["phase"] = PHASE_END
    state["last_question_id"] = None
    return messages.meds_intro()

