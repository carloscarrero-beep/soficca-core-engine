def safe_space(name):
    who = "Pen²"
    if name:
        return (
            "Hi " + name + ". I'm " + who + ".\n\n"
            "Before we start, I want you to know something important:\n"
            "this is your safe space.\n"
            "Nothing you share here means there's something wrong with you, "
            "and most things can be worked through.\n"
            "We'll take this step by step."
        )
    return (
        "Hi. I'm " + who + ".\n\n"
        "Before we start, I want you to know something important:\n"
        "this is your safe space.\n"
        "Nothing you share here means there's something wrong with you, "
        "and most things can be worked through.\n"
        "We'll take this step by step."
    )


def ask_reason(name):
    prefix = "Tell me" + (", " + name if name else "") + ".\n\n"
    return (
        prefix
        + "Would you like me to guide you around one of these?\n"
        + "For example:\n"
        + "– changes in your sexual performance\n"
        + "– things happening faster than you'd like\n"
        + "– losing confidence in bed\n"
        + "– or simply trying to understand what's going on\n\n"
        + "You don't have to use my words.\n"
        + "What feels closest to your situation?"
    )


def ask_main_issue():
    return (
        "To help you properly, I want to understand what happens in real moments.\n\n"
        "When you're with your partner, what bothers you the most?\n"
        "You can answer with one of these:\n"
        "• “I lose the erection”\n"
        "• “It doesn’t last long enough”\n"
        "• “I finish too fast”"
    )


def ask_frequency():
    return (
        "Does this happen every time, or do you have good days and bad days?\n"
        "You can answer: “every time” or “good days / bad days”."
    )


def ask_desire():
    return (
        "How is your desire overall?\n"
        "Would you say your desire is still there, or lower than before?\n"
        "You can answer: “still there” or “lower”."
    )


def ask_stress():
    return (
        "Over the past few weeks, how have stress or fatigue been for you?\n"
        "You can answer: “low”, “moderate”, or “high”."
    )


def ask_morning_erection():
    return (
        "And in the morning, when you wake up — have you noticed changes in morning erections compared to before?\n"
        "You can answer: “no change”, “reduced”, or “rarely”."
    )


def clarify_soft():
    # Keep it as a generic fallback, but we will STOP using it for every repair.
    return (
        "I get it — sometimes it's hard to put into words.\n"
        "Let’s make it simpler."
    )


def answer_user_question_brief():
    return (
        "That's a good question.\n"
        "Short answer: in most cases, this is workable.\n"
        "Let me ask you one more thing so I can guide you properly."
    )


def emotional_validation():
    return (
        "That makes sense. This can feel heavy.\n"
        "We'll take it calmly, step by step."
    )


def escalate_human_or_emergency():
    return (
        "Thanks for telling me. Based on what you shared, I’m not comfortable continuing this as a self-guided flow.\n\n"
        "The safest next step is to get immediate human help.\n"
        "If you feel you’re in danger or have severe symptoms, please seek urgent care or emergency services now.\n\n"
        "If you want, tell me your country and whether you can talk to a clinician right now, and I’ll guide you to the safest next step."
    )


def safety_need_country():
    return (
        "I hear you. I’m going to pause the self-guided flow so we can prioritize safety.\n\n"
        "To point you to the safest next step, what country are you in right now?"
    )


def safety_escalation_with_country(country: str | None = None):
    place = f"in {country}" if country else "in your area"
    return (
        "Thank you.\n\n"
        "I’m not able to handle this safely as a self-guided chat.\n"
        "If you feel in immediate danger, please contact your local emergency number right now.\n\n"
        f"If you can, try to reach a trusted person {place} or a healthcare professional today.\n"
        "If you want, tell me whether you’re alone right now, and whether you can call someone you trust."
    )


def greet():
    return "Hi. I’m Pen²."


def greet_back(name=None):
    if name:
        return f"Hi {name} — I’m here."
    return "Hi — I’m here."


def ask_name():
    return "Before we start — what name would you like me to use?"


def ask_gender_identity():
    return (
        "How do you identify?\n"
        "You can say: male, female, non-binary, or prefer not to say."
    )


def ask_country_general():
    return "And what country are you in right now?"


def meta_ack_waiting_files():
    return (
        "Got it — take your time.\n"
        "Send the files or details when you're ready, and we’ll continue right where we left off."
    )


def meta_ack_waiting_then_ask_country():
    return (
        "Got it — take your time.\n\n"
        "When you're ready, I still need one thing first so I can point you to the safest next step:\n"
        "What country are you in right now?"
    )


# -----------------------------
# Repair prompts (critical!)
# -----------------------------
def repair_reason(name=None):
    n = f", {name}" if name else ""
    return (
        "Got it.\n\n"
        f"In one sentence{n}, what feels closest?\n"
        "You can say: performance changes, finishing too fast, losing erection, or “something else”."
    )


def repair_main_issue():
    return (
        "Quick check — which feels closest?\n"
        "• lose the erection\n"
        "• it doesn’t last long enough\n"
        "• finish too fast"
    )


def repair_frequency():
    return (
        "Which one is closer?\n"
        "• every time\n"
        "• good days / bad days"
    )


def repair_desire():
    return (
        "When I say “desire”, I mean how turned on you feel.\n"
        "Which is closer?\n"
        "• still there\n"
        "• lower than before"
    )


def repair_stress():
    return (
        "For stress/fatigue, which is closer lately?\n"
        "• low\n"
        "• moderate\n"
        "• high"
    )


def repair_morning_erection():
    return (
        "For morning erections compared to before, which is closer?\n"
        "• no change\n"
        "• reduced\n"
        "• rarely"
    )


def repair_gender_identity():
    return (
        "You can answer with one:\n"
        "• male\n"
        "• female\n"
        "• non-binary\n"
        "• prefer not to say"
    )


def repair_route_choice():
    return (
        "Just to confirm, which path do you want right now?\n"
        "• medication support\n"
        "• habit/support first"
    )


def repair_for_question(question_id, name=None):
    if question_id == "reason":
        return repair_reason(name=name)
    if question_id == "main_issue":
        return repair_main_issue()
    if question_id == "frequency":
        return repair_frequency()
    if question_id == "desire":
        return repair_desire()
    if question_id == "stress":
        return repair_stress()
    if question_id == "morning_erection":
        return repair_morning_erection()
    if question_id == "gender_identity":
        return repair_gender_identity()
    if question_id == "route_choice":
        return repair_route_choice()
    if question_id == "name":
        return ask_name()
    if question_id == "country":
        return ask_country_general()
    # fallback
    return clarify_soft()


def end_meds_options(name=None, needs_eval_parallel=False):
    intro = f"Got it{name and (', ' + name) or ''}.\n\n"
    safety = ""
    if needs_eval_parallel:
        safety = (
            "One important note: because there are signals worth evaluating, "
            "the safest approach is medication support **with** a clinician review in parallel.\n\n"
        )

    return (
        intro
        + safety
        + "Here are common **medication support options** people consider for erectile performance issues:\n\n"
        + "1) **On-demand PDE5 support** (examples: sildenafil, vardenafil, avanafil)\n"
        + "   • Often used situationally to improve reliability\n"
        + "   • Typically requires medical authorization\n\n"
        + "2) **Longer-window PDE5 support** (example: tadalafil)\n"
        + "   • Longer window, less “timing pressure” for some people\n"
        + "   • Typically requires medical authorization\n\n"
        + "3) **Non-med options** (device-based support)\n"
        + "   • Some people consider vacuum devices or similar options\n\n"
        + "I can’t prescribe or diagnose — but I *can* help you choose the safest next step.\n\n"
        + "Two quick questions so I can guide you responsibly:\n"
        + "• Do you take any heart medications (especially nitrates)?\n"
        + "• Do you prefer **on-demand** support or a **longer window** option?"
    )


def end_support_plan(name=None):
    intro = f"That makes sense{name and (', ' + name) or ''}.\n\n"
    return (
        intro
        + "Let’s go with a **support-first plan** to rebuild stability and confidence.\n\n"
        + "Here’s what Pen² will do with you:\n\n"
        + "**1) Emotional support (lightweight, practical):**\n"
        + "• Daily check-in: mood (0–10), performance anxiety (0–10), confidence (0–10)\n"
        + "• One short reflection: “What was the hardest part this week?”\n\n"
        + "**2) Symptom & context tracking (not medical diagnosis):**\n"
        + "• Good day / bad day pattern\n"
        + "• Sleep hours, stress level, fatigue\n"
        + "• Morning erections trend (only as a signal to decide if evaluation is needed)\n\n"
        + "**3) Small weekly actions:**\n"
        + "• Sleep + stress reset (2 small habits)\n"
        + "• A simple exposure plan to reduce performance pressure\n\n"
        + "If anything suggests a safety risk or a physiological red flag, I’ll recommend clinician evaluation.\n\n"
        + "To start: over the next 7 days, do you want **daily** check-ins or **every 3 days**?"
    )


def end_eval_first(name=None):
    intro = f"Thanks{name and (', ' + name) or ''}.\n\n"
    return (
        intro
        + "Based on the pattern you described, the safest next step is a **clinician evaluation first**.\n\n"
        + "That doesn’t mean anything is “wrong” — it just means we should rule out common contributors "
        + "(sleep, stress, cardiometabolic factors, meds, etc.) before a medication-first path.\n\n"
        + "What Pen² can do now:\n"
        + "• Help you prepare a short summary to share with a clinician (symptoms, timeline, stress/sleep)\n"
        + "• Track your pattern over 7–14 days so the evaluation is faster and clearer\n\n"
        + "Do you want me to generate a **clinician summary** you can copy/paste?"
    )


def ask_route_choice():
    return (
        "Where do you feel you'd like to go right now?\n"
        "You can answer:\n"
        "• “medication support”\n"
        "• “habit/support first”"
    )


def meds_intro():
    return (
        "That makes sense.\n\n"
        "Using medication in situations like this doesn't mean dependence or failure.\n"
        "Often it's a temporary support to rebuild stability and confidence.\n\n"
        "If you'd like, I can show you available options, what requires medical authorization, "
        "and how we would move forward."
    )

