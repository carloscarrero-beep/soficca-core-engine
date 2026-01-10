import re


def interpret(user_text, question_id):
    text = (user_text or "").strip()
    lower = text.lower()

    if not text:
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    if "?" in text:
        return {"type": "user_question", "value": text, "confidence": "high"}

    if re.search(r"\b(anxious|stressed|ashamed|embarrassed|worried|sad)\b", lower):
        return {"type": "emotional", "value": text, "confidence": "high"}

    if question_id == "frequency":
        lower = (text or "").lower()

        sometimes_cues = [
            "sometimes",
            "not always",
            "good days",
            "bad days",
            "good day",
            "bad day",
            "on and off",
            "depends",
            "occasionally",
            "from time to time",
        ]

        always_cues = [
            "every time",
            "all the time",
            "consistently",
            "always",
            "never works",
        ]

        if any(cue in lower for cue in sometimes_cues):
            return {"type": "answer", "value": "sometimes", "confidence": "high"}

        if any(cue in lower for cue in always_cues):
            return {"type": "answer", "value": "always", "confidence": "high"}

        return {"type": "ambiguous", "value": None, "confidence": "low"}

    if question_id == "desire":
        if re.search(r"\b(still|same|normal)\b", lower):
            return {"type": "answer", "value": "present", "confidence": "high"}
        if re.search(r"\b(lower|reduced|less)\b", lower):
            return {"type": "answer", "value": "reduced", "confidence": "high"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    if question_id == "stress":
        if re.search(r"\b(high|very high|overwhelmed|stressed)\b", lower):
            return {"type": "answer", "value": "high", "confidence": "high"}
        if re.search(r"\b(moderate|medium)\b", lower):
            return {"type": "answer", "value": "moderate", "confidence": "high"}
        if re.search(r"\b(low|normal|fine)\b", lower):
            return {"type": "answer", "value": "low", "confidence": "high"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    if question_id == "morning_erection":
        if re.search(r"\b(normal|same as before)\b", lower):
            return {"type": "answer", "value": "normal", "confidence": "high"}
        if re.search(r"\b(less|reduced|decreased)\b", lower):
            return {"type": "answer", "value": "reduced", "confidence": "high"}
        if re.search(r"\b(rarely|almost never)\b", lower):
            return {"type": "answer", "value": "rare", "confidence": "high"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    if question_id == "main_issue":
        if re.search(r"\b(lose|losing).*erection\b", lower):
            return {"type": "answer", "value": "erection_lost", "confidence": "high"}
        if re.search(r"\b(not last|doesn't last|short)\b", lower):
            return {"type": "answer", "value": "short_duration", "confidence": "high"}
        if re.search(r"\b(too fast|finish fast|premature)\b", lower):
            return {"type": "answer", "value": "early_ejaculation", "confidence": "moderate"}
        return {"type": "ambiguous", "value": None, "confidence": "low"}

    if question_id == "reason":
        return {"type": "answer", "value": text, "confidence": "high"}

    if re.search(r"\b(meds|medication|pill|treatment|prescription|something fast)\b", lower):
        return {"type": "answer", "value": True, "confidence": "high"}

    return {"type": "answer", "value": text, "confidence": "low"}
