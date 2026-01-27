PHASE_INTRO = "INTRO"
PHASE_REASON = "REASON"
PHASE_SYMPTOMS = "SYMPTOMS"
PHASE_CONTEXT = "CONTEXT"
PHASE_INTERPRETATION = "INTERPRETATION"
PHASE_ACTION = "ACTION"
PHASE_END = "END"

MODE_NORMAL = "NORMAL"
MODE_SAFETY_LOCK = "SAFETY_LOCK"

Q_REASON = "reason"
Q_MAIN_ISSUE = "main_issue"
Q_FREQUENCY = "frequency"
Q_DESIRE = "desire"
Q_STRESS = "stress"
Q_MORNING_ERECTION = "morning_erection"
Q_NAME = "name"
Q_GENDER_ID = "gender_identity"
Q_COUNTRY = "country"  # for safety resources / localization
Q_ROUTE_CHOICE = "route_choice"


def new_state(user_profile=None):
    return {
        "mode": MODE_NORMAL,
        "phase": PHASE_INTRO,
        "user": user_profile or {},
        "meta": {
            "safe_space_shown": False,
            "welcomed": False,
            "awaiting_files": False,
            "unknown_slot_writes": [],
        },
        "slots": {
            "reason": None,
            "main_issue": None,
            "frequency": None,
            "desire": None,
            "stress": None,
            "morning_erection": None,
            "wants_meds": None,
            "country": None,
            "name": None,
            "gender_identity": None,
        },
        "last_question_id": None,
        "turn": 0,
    }


def set_slot(state, key, value):
    # Prevent silent creation of wrong keys (typos, unexpected ids)
    slots = state.get("slots") or {}
    if key not in slots:
        meta = state.setdefault("meta", {})
        meta.setdefault("unknown_slot_writes", []).append({"key": key, "value": value})
        return state

    slots[key] = value
    state["slots"] = slots
    return state


def get_slot(state, key):
    return (state.get("slots") or {}).get(key)


def is_done(state):
    return state.get("phase") == PHASE_END

