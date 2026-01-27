# src/soficca_core/rules.py

PATH_MORE_QUESTIONS = "PATH_MORE_QUESTIONS"
PATH_EVAL_FIRST = "PATH_EVAL_FIRST"
PATH_MEDS_OK = "PATH_MEDS_OK"
PATH_ESCALATE_HUMAN = "PATH_ESCALATE_HUMAN"  # triggered by safety gate (engine), not by these signals


def apply_rules(signals):
    decision = {
        "path": PATH_MORE_QUESTIONS,
        "flags": [],
        "reasons": [],
        "recommendations": [],
    }

    intermittent = signals.get("intermittent_pattern")
    user_requests_meds = signals.get("user_requests_meds")
    morning_reduced = signals.get("morning_erection_reduced") is True

    if intermittent is True:
        decision["path"] = PATH_MEDS_OK
        decision["reasons"].append("Symptoms appear intermittent.")
        decision["recommendations"].append("Medication support can be considered.")

        if user_requests_meds is True:
            decision["reasons"].append("You asked for medication support.")
            decision["recommendations"].append("Show medication options (authorization as needed).")

        if morning_reduced:
            decision["flags"].append("physiology_signal")
            decision["flags"].append("needs_eval_parallel")
            decision["reasons"].append("Reduced morning erections can be a physiological signal worth evaluating.")
            decision["recommendations"].append("Recommend clinician evaluation in parallel.")

    elif intermittent is False:
        if user_requests_meds is True:
            decision["path"] = PATH_MEDS_OK
            decision["flags"].append("needs_eval_parallel")
            decision["reasons"].append("You asked for medication support.")
            decision["reasons"].append(
                "Because the pattern seems persistent, it's best paired with clinician review."
            )
            decision["recommendations"].append("Show medication options (authorization as needed).")
            decision["recommendations"].append("Recommend clinician evaluation in parallel.")
        else:
            decision["path"] = PATH_EVAL_FIRST
            decision["flags"].append("persistent_pattern")
            decision["reasons"].append("Symptoms seem consistent rather than intermittent.")
            decision["recommendations"].append("Consider clinician evaluation before a medication-first approach.")

        if morning_reduced and "physiology_signal" not in decision["flags"]:
            decision["flags"].append("physiology_signal")
            decision["reasons"].append("Reduced morning erections can be a physiological signal worth evaluating.")

    return decision







