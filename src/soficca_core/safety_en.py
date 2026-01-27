# src/soficca_core/safety_en.py
import re
from typing import List

# Minimal, conservative red flags for a health chat demo (not medical diagnosis).
# Goal: "stop + escalate to human / emergency guidance" when obvious risk signals appear.

def detect_red_flags(user_text: str) -> List[str]:
    text = (user_text or "").lower().strip()
    if not text:
        return []

    flags: List[str] = []

    # Self-harm / suicide
    if re.search(r"\b(suicide|kill myself|end my life|self harm|hurt myself)\b", text):
        flags.append("RED_FLAG_SELF_HARM")

    # Chest pain / severe cardio-respiratory symptoms
    if re.search(r"\b(chest pain|pressure in chest|can't breathe|shortness of breath|fainting|passed out)\b", text):
        flags.append("RED_FLAG_ACUTE_CARDIORESP")

    # Stroke-like symptoms (very coarse)
    if re.search(r"\b(face droop|slurred speech|one side weak|sudden weakness|stroke)\b", text):
        flags.append("RED_FLAG_NEURO")

    # Priapism / dangerous erection duration
    if re.search(r"\b(erection.*(4 hours|four hours)|priapism)\b", text):
        flags.append("RED_FLAG_PRIAPISM")

    # Severe bleeding / severe pain (coarse)
    if re.search(r"\b(severe pain|unbearable pain|bleeding a lot|heavy bleeding)\b", text):
        flags.append("RED_FLAG_SEVERE_PAIN_BLEEDING")

    return flags
