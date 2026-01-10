PHASE_INTRO = "INTRO"
PHASE_REASON = "REASON"
PHASE_SYMPTOMS = "SYMPTOMS"
PHASE_CONTEXT = "CONTEXT"
PHASE_INTERPRETATION = "INTERPRETATION"
PHASE_ACTION = "ACTION"
PHASE_END = "END"

Q_REASON = "reason"
Q_MAIN_ISSUE = "main_issue"
Q_FREQUENCY = "frequency"
Q_DESIRE = "desire"
Q_STRESS = "stress"
Q_MORNING_ERECTION = "morning_erection"


def new_state(user_profile=None):
    return {
        "phase": PHASE_INTRO,
        "user": user_profile or {},
        "slots": {
            "reason": None,
            "main_issue": None,
            "frequency": None,
            "desire": None,
            "stress": None,
            "morning_erection": None,
            "wants_meds": None,
        },
        "last_question_id": None,
        "turn": 0,
    }


def set_slot(state, key, value):
    state["slots"][key] = value
    return state


def get_slot(state, key):
    return state["slots"].get(key)


def is_done(state):
    return state.get("phase") == PHASE_END
