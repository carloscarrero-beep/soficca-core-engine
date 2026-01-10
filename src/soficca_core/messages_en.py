def safe_space(name):
    if name:
        return (
            "Hi " + name + ". I'm Pen.\n\n"
            "Before we start, I want you to know something important:\n"
            "this is your safe space.\n"
            "Nothing you share here means there's something wrong with you, "
            "and most things can be worked through.\n"
            "We'll take this step by step."
        )
    return (
        "Hi. I'm Pen.\n\n"
        "Before we start, I want you to know something important:\n"
        "this is your safe space.\n"
        "Nothing you share here means there's something wrong with you, "
        "and most things can be worked through.\n"
        "We'll take this step by step."
    )


def ask_reason(name):
    prefix = "Tell me" + (", " + name if name else "") + ".\n\n"
    return (
        prefix +
        "Would you like me to guide you around one of these?\n"
        "For example:\n"
        "– changes in your sexual performance\n"
        "– things happening faster than you'd like\n"
        "– losing confidence in bed\n"
        "– or simply trying to understand what's going on\n\n"
        "You don't have to use my words.\n"
        "What feels closest to your situation?"
    )


def ask_main_issue():
    return (
        "To help you properly, I want to understand what happens in real moments.\n\n"
        "When you're with your partner, what bothers you the most?\n"
        "Some people describe it like:\n"
        "– 'I lose the erection'\n"
        "– 'It doesn't last long enough'\n"
        "– 'I finish too fast'\n\n"
        "What feels closest to your experience?"
    )


def ask_frequency():
    return (
        "Does this happen every time, or do you have good days and bad days?\n"
        "Tell me in your own words."
    )


def ask_desire():
    return (
        "How is your desire overall?\n"
        "Do you still feel turned on, but your body doesn't respond the way you'd like?"
    )


def ask_stress():
    return (
        "Over the past few weeks, how have stress or fatigue been for you?\n"
        "Some people say 'normal', others 'pretty loaded', others 'very high'."
    )


def ask_morning_erection():
    return (
        "And in the morning, when you wake up,\n"
        "have you noticed any changes in morning erections compared to before?"
    )


def reflect_and_bridge_to_meds():
    return (
        "Thanks for sharing that.\n\n"
        "From what you're describing, this sounds more like a consistency or performance issue "
        "than something permanent.\n\n"
        "At this point, some people prefer starting with habit support,\n"
        "and others prefer medication support to regain stability faster.\n\n"
        "Where do you feel you'd like to go right now?"
    )


def meds_intro():
    return (
        "That makes sense.\n\n"
        "Using medication in situations like this doesn't mean dependence or failure.\n"
        "Often it's a temporary support to rebuild stability and confidence.\n\n"
        "If you'd like, I can show you available options, what requires medical authorization, "
        "and how we would move forward."
    )


def clarify_soft():
    return (
        "I get it — sometimes it's hard to put into words.\n"
        "In the simplest way, is it more that you lose the erection, it doesn't last, "
        "or things happen too fast?"
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
