# src/soficca_core/nlu_specs.py
"""
Question specs for NLU (OpenAI or deterministic).

Keep these short to reduce tokens and keep the NLU call stable.
"""

from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class QuestionSpec(TypedDict, total=False):
    question_text: str
    allowed_values: Optional[List[str]]
    value_type: str  # "enum" | "free_text" | "string" | "bool"


QUESTION_SPECS: Dict[str, QuestionSpec] = {
    "name": {
        "question_text": "What name would you like me to use?",
        "allowed_values": None,
        "value_type": "string",
    },
    "gender_identity": {
        "question_text": "How do you identify? (male/female/non-binary/prefer not to say)",
        "allowed_values": ["male", "female", "non_binary", "prefer_not_say"],
        "value_type": "enum",
    },
    "country": {
        "question_text": "What country are you in right now?",
        "allowed_values": None,
        "value_type": "string",
    },
    "reason": {
        "question_text": "What feels closest to your situation?",
        "allowed_values": None,
        "value_type": "free_text",
    },
    "main_issue": {
        "question_text": "Which is closest? lose erection / doesn't last / finish too fast",
        "allowed_values": ["erection_lost", "short_duration", "early_ejaculation", "something_else"],
        "value_type": "enum",
    },
    "frequency": {
        "question_text": "Does this happen every time or good days/bad days?",
        "allowed_values": ["always", "sometimes"],
        "value_type": "enum",
    },
    "desire": {
        "question_text": "Is desire still there or lower than before?",
        "allowed_values": ["present", "reduced"],
        "value_type": "enum",
    },
    "stress": {
        "question_text": "Stress/fatigue lately: low / moderate / high?",
        "allowed_values": ["low", "moderate", "high"],
        "value_type": "enum",
    },
    "morning_erection": {
        "question_text": "Morning erections compared to before: no change / reduced / rarely?",
        "allowed_values": ["normal", "reduced", "rare"],
        "value_type": "enum",
    },
    "route_choice": {
        "question_text": "Which path now: medication support OR habit/support first?",
        "allowed_values": ["meds", "support"],
        "value_type": "enum",
    },
}
