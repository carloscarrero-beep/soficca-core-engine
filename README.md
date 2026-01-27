# Soficca Core Engine

Explainable, rule‑based **clinical conversational decision engine** with hybrid NLU.

> **Status:** v0.2 (working, hybrid NLU)  
> **API stability:** Experimental (pre‑v1)  
> **License:** Proprietary (subject to change)

---

## Overview

**Soficca Core Engine** is a deterministic, explainable decision system designed to guide
**sensitive health conversations** safely.

The Core Engine is intentionally **rule‑based** for decision‑making and safety, while using
**OpenAI models only as a Natural Language Understanding (NLU) layer** to interpret user input.

> OpenAI is never used to make clinical decisions or generate clinical advice.
> It acts only as a structured language sensor.

---

## Core principles

- **Clinical safety first** – deterministic rules, explicit gates
- **Explainability** – every outcome is traceable
- **No black‑box decisions** – ML assists interpretation only
- **Fail safely** – ambiguity triggers repair or escalation
- **Cost‑efficient** – hybrid deterministic + LLM routing

---

## What it does

The Core Engine:

- Validates and normalizes user input (never crashes)
- Maintains a structured **conversation state**
- Interprets free‑text responses into structured signals
- Applies deterministic clinical decision rules
- Produces **auditable recommendations and reasons**
- Prevents conversational loops automatically

Each turn produces:

- **path** – decision outcome
- **flags** – detected rule‑based signals
- **recommendations** – next safe steps
- **reasons** – explicit explanations
- **chat output** – assistant message + updated state

---

## What it does NOT do

This system does **not**:

- Diagnose medical conditions
- Prescribe medication
- Replace clinical judgment
- Use LLMs for decision logic
- Store user data or manage accounts

It is a **pure decision engine**, meant to be embedded into apps, APIs, or clinical workflows.

---

## Hybrid NLU architecture (v0.2)

### Why hybrid?

Human language is variable, ambiguous, and context‑dependent.
Pure regex or rules are fragile; pure LLM systems are unsafe.

Soficca combines both.

### Flow

1. **Deterministic parsing first**
   - Enumerated answers
   - Short responses
   - Simple slot fills

2. **OpenAI NLU (fallback only)**
   - Contextual interpretation (yes/no/maybe)
   - Multi‑slot extraction in one message
   - Confidence scoring
   - Structured JSON output

3. **Engine decides**
   - Advance
   - Repair
   - Escalate
   - End conversation

### OpenAI usage

- **NLU‑only**
- **Structured Outputs (JSON Schema)**
- No clinical text generation
- No history sent
- No personal identifiers required

Models:
- `gpt‑5‑nano` (default)
- `gpt‑5‑mini` (fallback on low confidence)

---

## Conversational flow

Phases:

```
INTRO → REASON → SYMPTOMS → CONTEXT → INTERPRETATION → ACTION → END
```

Features:

- Slot‑based state
- Context‑aware interpretation
- Automatic repair prompts
- Anti‑loop protection
- Safety lock escalation

---

## Decision logic

Deterministic rule engine (`rules.py`) evaluates normalized signals:

Example paths:

- `PATH_MORE_QUESTIONS`
- `PATH_EVAL_FIRST`
- `PATH_MEDS_OK`
- `PATH_ESCALATE_HUMAN`

Each path includes:
- reasons
- flags
- recommendations

---

## Safety design

- Local red‑flag detection (self‑harm, acute symptoms)
- Immediate safety lock
- Country‑aware escalation prompts
- No LLM‑based safety decisions

---

## Public API contract

### Input

```json
{
  "user": {},
  "measurements": [],
  "context": {
    "chat_text": "I’m Carlos, male, from Colombia",
    "chat_state": null
  }
}
```

### Output

```json
{
  "ok": true,
  "errors": [],
  "normalized_input": {},
  "report": {
    "path": "PATH_MORE_QUESTIONS",
    "flags": [],
    "recommendations": [],
    "reasons": [],
    "chat": {
      "assistant_message": "...",
      "phase": "INTRO",
      "done": false,
      "state": {}
    }
  }
}
```

The output shape is **guaranteed stable**.

---

## Demo

```bash
pip install -e .
python examples/chat_demo.py
```

---

## API (optional)

```bash
uvicorn api.app:app --reload
```

OpenAPI docs:
http://127.0.0.1:8000/docs

---

## Testing

```bash
pytest
```

Tests cover:

- Output contract stability
- NLU interpretation
- Slot extraction
- Anti‑loop behavior
- Safety escalation

---

## Project structure

```
src/soficca_core/
├── engine.py
├── chat_state.py
├── chat_flow.py
├── rules.py
├── normalization.py
├── interpret_en.py
├── nlu_openai.py
├── nlu_specs.py
├── safety_en.py
├── messages_en.py
```

---

## Roadmap

- v0.3 – longitudinal tracking
- v0.4 – clinician‑facing summaries
- v1.0 – production clinical workflows

---

## Disclaimer

Soficca Core Engine is a **clinical decision‑support system**, not a medical device.
All outputs are intended to support — not replace — professional clinical judgment.
