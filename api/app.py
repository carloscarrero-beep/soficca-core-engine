from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Any, Dict, List

from soficca_core.engine import generate_report

app = FastAPI(title="Soficca Core API", version="0.1.0")


class CoreRequest(BaseModel):
    user: Dict[str, Any] = Field(default_factory=dict)
    measurements: List[Any] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


@app.post("/v1/report")
def v1_report(payload: CoreRequest):
    return generate_report(payload.model_dump())


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Soficca Core API",
        "version": "0.1.0",
        "endpoints": ["/docs", "/v1/report"],
    }


