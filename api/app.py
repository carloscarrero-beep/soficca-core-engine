from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict

from soficca_core.engine import generate_report

app = FastAPI(title="Soficca Core API", version="0.1.0")


class CoreRequest(BaseModel):
    user: Dict[str, Any]
    measurements: list = []
    context: Dict[str, Any] = {}


@app.post("/v1/report")
def v1_report(payload: CoreRequest):
    # superficial validation is handled by Pydantic + validate_input inside core
    return generate_report(payload.model_dump())
@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Soficca Core API",
        "version": "0.1.0",
        "endpoints": ["/docs", "/v1/report"],
    }

