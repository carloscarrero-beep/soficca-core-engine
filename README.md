# Soficca Core Engine
Explainable **rule-based** decision engine for modular health domains.

> **Status:** Draft – v0.1  
> **API stability:** Unstable (pre-v0.2)  
> **License:** Proprietary (subject to change) 

## What it does
The Core Engine evaluates structured user signals, validates and normalizes the input,
applies domain-specific decision rules, and generates a **deterministic and explainable**
health analysis report.

The engine returns:
- `scores` (normalized quantitative indicators, 0–100)
- `flags` (rule-based findings)
- `recommendations` (actionable suggestions)
- `reasons` (explicit explanations backing every decision)

## What it does NOT do
This Core **does not**:
1. Provide medical diagnosis, prescribe treatment, or replace clinical judgment.
2. Rely on ML models or LLMs as the primary decision-maker (for now). It is intentionally **rule-based** for traceability.
3. Require UI, databases, or external services to function (pure core logic with minimal dependencies).

## Why rule-based first
- **Auditable:** every decision is backed by a traceable and reviewable reason.
- **Deterministic:** the same input always produces the same output.
- **Safe by design:** avoids “black box” behavior in health-related contexts and simplifies clinical and technical validation.
- **Iterative:** enables controlled data collection and domain understanding before introducing ML-based approaches.

---

## Public API (Contract)

## Input contract
- **Type:** `dict` (or equivalent JSON)
- **May be incomplete:** yes (the engine must handle missing fields)
- **May be invalid:** yes (the engine must **never crash**)
- **Invalid input behavior:** validation errors are reported explicitly; no implicit corrections are made without being surfaced.
- **Guarantee:** the engine always returns a response with a stable output shape

### Required top-level fields (v0.1)
- `user`: object
- `metrics`: object
- `context`: object (optional, with defaults)

### Example input
```json
{
    "user": {
        "id": "user01",
        "sex": "male",
        "birth_date": "2001-01-06"
    },
    "measurements": [
        {
          "name": "anthropometrics.weight",
          "value": 70,
          "unit" : "kg",
          "source": "self_report",
          "observed_at": "2025-12-01T00:00:00-05:00"
            
        },
        {
          "name": "anthropometrics.height",
          "value": 170,
          "unit" : "cm",
          "source": "self_report",
          "observed_at": "2025-12-01T00:00:00-05:00"
            
        },
        {
          "name": "sleep.avg_hours_7d",
          "value": 7,
          "unit" : "h",
          "source": "device",
          "observed_at": "2025-12-01T00:00:00-05:00"
           
        }
    ]   
    ,
    "context":{
        "timezone": "America/Bogota",
        "locale": "es-CO",
        "request_source": "app",
        "enabled_domains": ["sleep","mood","stress","hair","sexual_health","hormones","cognition","weight"]
    }
}

```

## Output contract

### Success response
- ok: true
- errors: []
- normalized_input: object
- report: object

**normalized_input** represents the normalized internal state derived from raw measurements.

### Report
- scores: object
- flags: list
- recommendations: list
- reasons: list

The report contains deterministic, explainable outputs derived from the normalized input state.

### Example output (illustrative)
```json
{
  "ok": true,
  "errors": [],
  "normalized_input": {
    "anthropometrics": {
      "height_cm": 170,
      "weight_kg": 70
    },
    "sleep": {
      "avg_hours_7d": 7
    }
  },
  "report": {
    "scores": {
      "sleep_score": 75,
      "overall_score": 72
    },
    "flags": [
      {
        "id": "sleep.ok_duration",
        "severity": "info",
        "message": "Average sleep duration appears within a typical range."
      }
    ],
    "recommendations": [
      {
        "id": "sleep.track_consistency",
        "priority": "low",
        "text": "Track sleep consistency over time to improve confidence in trends."
      }
    ],
    "reasons": [
      {
        "id": "sleep_score.based_on_avg_hours_7d",
        "text": "sleep_score is derived from avg_hours_7d using deterministic rules."
      },
      {
        "id": "flag.sleep.ok_duration",
        "text": "The flag was added because avg_hours_7d met the current rule threshold."
      }
    ]
  }
}
```