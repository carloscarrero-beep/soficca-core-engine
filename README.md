# Soficca Core Engine

Explainable, **rule-based** conversational decision engine for modular health domains.

> **Status:** v0.1 (working demo)  
> **API stability:** Experimental (pre-v0.2)  
> **License:** Proprietary (subject to change)

---

## Overview

**Soficca Core Engine** is a deterministic and explainable health decision system designed to
guide sensitive health conversations, interpret user responses, and generate
**transparent, auditable recommendations**.

The engine is intentionally **rule-based** in its initial versions to prioritize:

- safety  
- explainability  
- clinical reviewability  
- controlled data collection  

before introducing machine learning or statistical models.

---

## What it does

The Core Engine:

- Safely validates and processes user input (never crashes)
- Maintains a lightweight **conversational state**
- Interprets free-text responses into structured signals
- Applies deterministic decision rules
- Generates **explainable outcomes** and next actions

Each execution produces:

- **scores** – normalized indicators (optional in v0.1)
- **flags** – rule-based findings
- **recommendations** – actionable next steps
- **reasons** – explicit explanations for each decision
- **chat output** – next assistant message and updated conversation state

---

## What it does NOT do

This Core intentionally does **not**:

1. Provide medical diagnosis or replace clinical judgment.
2. Prescribe treatment autonomously.
3. Use ML models or LLMs as primary decision-makers.
4. Depend on databases, authentication systems, or UI layers.

It is a **pure core logic layer**, designed to be embedded into apps, APIs, or clinical workflows.

---

## Why rule-based first

Health-related systems require clarity and trust.

A rule-based approach ensures the system is:

- **Auditable** – every output is traceable to explicit rules
- **Deterministic** – identical input produces identical output
- **Safe by design** – avoids black-box behavior
- **Iterative** – enables structured data collection before ML adoption

ML-based components can later be layered on top of this stable core.

---

## Conversational engine (v0.1)

In v0.1, the Core Engine supports a **guided conversational flow**.

The conversational layer:

- Tracks conversation **phases**  
  (`reason → symptoms → context → action → end`)
- Maintains structured **slots** (e.g. frequency, desire, stress)
- Accepts open-ended user input (not rigid forms)
- Interprets responses deterministically
- Guides the user without judgment or diagnosis

This enables **human-like, safe conversations** while preserving full explainability.

---

## Decision logic

Based on interpreted signals, the engine selects a deterministic decision path.

Examples:

- `PATH_MORE_QUESTIONS`  
  → more information required

- `PATH_EVAL_FIRST`  
  → suggest clinician evaluation before medication-first approach

- `PATH_MEDS_OK`  
  → medication support can be considered

- `PATH_MEDS_OK + needs_eval_parallel`  
  → medication allowed with parallel clinical evaluation

Each path is backed by explicit **flags**, **reasons**, and **recommendations**.

---

## Public API (contract)

### Input contract

- **Type:** `dict` / JSON  
- **May be incomplete:** yes  
- **May be invalid:** yes  
- **Guarantee:** the engine always returns a response with a stable output shape  

### Required top-level fields (v0.1)

- `user`: object  
- `measurements`: list (may be empty)  
- `context`: object (optional)

### Example input

```json
{
  "user": {
    "name": "Carlos",
    "dob": "1993-01-01"
  },
  "measurements": [],
  "context": {
    "chat_text": "Not always. I have good days and bad days.",
    "chat_state": null
  }
}
```
## Output contract

### Success response

- `ok` : boolean  
- `errors` : list  
- `normalized_input` : object  
- `report` : object  

### Report fields

- `scores`
- `flags`
- `recommendations`
- `reasons`
- `chat`  
  (assistant message, phase, updated conversation state)

The output is **deterministic and fully explainable**.

---

## Demo (recommended)

A full conversational demo is included.

```bash
pip install -e .
python examples/chat_demo.py
```
The demo prints:

- conversation turns  
- assistant messages  
- decision paths  
- flags, reasons, and recommendations  

This demonstrates the Core Engine **end-to-end**, without UI or frontend dependencies.

---

## API (experimental)

A minimal FastAPI wrapper is provided.

```bash
uvicorn api.app:app --reload
```
Then open:
http://127.0.0.1:8000/docs

`POST /v1/report` forwards input directly to the Core Engine.

---

## Testing & CI

The project includes unit tests for:

- output contract stability  
- conversational flow  
- interpretation logic  
- decision rules  

Run locally:

```bash
pytest
```
CI is configured via GitHub Actions to automatically run tests on push and pull requests.

## Project structure

```text
src/soficca_core/
├── engine.py        # Core orchestrator (entry point)
├── validation.py    # Input validation & safety checks
├── normalization.py # Signal normalization
├── interpret_en.py  # Deterministic NLP interpretation
├── chat_state.py    # Conversation state & slots
├── chat_flow.py     # Phase progression
├── rules.py         # Decision logic
├── messages_en.py   # Assistant messages
```

## Roadmap (high level)

v0.2 – richer normalization and scoring

v0.3 – longitudinal tracking and confidence metrics

v1.x – ML-assisted layers on top of rule-based core

## Disclaimer

Soficca Core Engine is a decision-support system, not a medical device.
All outputs are intended to support — not replace — professional clinical judgment.
