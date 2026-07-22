"""Lens NL-to-SQL API endpoints.

POST /api/lens/query    — natural-language question -> SQL + results
GET  /api/lens/ontology — browsable semantic ontology for the UI
GET  /api/lens/examples — example questions the user can ask
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.services.lens import LensEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lens", tags=["lens"])

# Singleton engine (reused across requests)
_engine = LensEngine()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class LensQueryRequest(BaseModel):
    """Payload for a natural-language query."""

    question: str = Field(..., min_length=1, max_length=500, description="Natural-language question about marketing data")


class LensQueryResponse(BaseModel):
    """Result of a Lens NL-to-SQL query."""

    sql: str = Field(..., description="Generated SQL query")
    columns: list[str] = Field(default_factory=list, description="Column names in the result set")
    rows: list[list[Any]] = Field(default_factory=list, description="Result rows")
    summary: str = Field(..., description="Natural-language summary of the results")
    chart_type: str | None = Field(default=None, description="Suggested chart type: line, bar, table, metric_card")
    error: str | None = Field(default=None, description="Error message if the query could not be executed")


class OntologyColumn(BaseModel):
    """A single queryable column or derived expression."""

    name: str
    description: str
    format: str
    is_derived: bool


class OntologyConcept(BaseModel):
    """A user-facing concept grouping related columns."""

    label: str
    description: str
    columns: list[OntologyColumn]


class OntologyResponse(BaseModel):
    """The full semantic ontology for the Lens UI."""

    concepts: list[OntologyConcept]
    tables: list[str]


class ExampleQuestion(BaseModel):
    """An example question the user can ask."""

    question: str
    category: str


class ExamplesResponse(BaseModel):
    """List of example questions."""

    examples: list[ExampleQuestion]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/query", response_model=LensQueryResponse)
def query(body: LensQueryRequest) -> LensQueryResponse:
    """Accept a natural-language question and return SQL + results.

    The engine converts the question to a safe SELECT query, executes it
    against the DuckDB warehouse, and returns structured results with a
    plain-English summary.  If the query fails, fallback mock data is
    returned so the endpoint never errors out.
    """
    logger.info("Lens query: %s", body.question)
    result = _engine.ask(body.question)
    return LensQueryResponse(
        sql=result.sql,
        columns=result.columns,
        rows=result.rows,
        summary=result.summary,
        chart_type=result.chart_type,
        error=result.error,
    )


@router.get("/ontology", response_model=OntologyResponse)
def ontology() -> OntologyResponse:
    """Return the semantic ontology so the UI can show available concepts.

    Each concept groups related columns with their descriptions and
    format hints (currency, percent, integer, etc.).
    """
    data = _engine.get_ontology()
    concepts = [
        OntologyConcept(
            label=c["label"],
            description=c["description"],
            columns=[
                OntologyColumn(
                    name=col["name"],
                    description=col["description"],
                    format=col["format"],
                    is_derived=col["is_derived"],
                )
                for col in c["columns"]
            ],
        )
        for c in data["concepts"]
    ]
    return OntologyResponse(concepts=concepts, tables=data["tables"])


@router.get("/examples", response_model=ExamplesResponse)
def examples() -> ExamplesResponse:
    """Return example questions the user can click to try Lens."""
    items = _engine.get_examples()
    return ExamplesResponse(
        examples=[
            ExampleQuestion(question=e["question"], category=e["category"])
            for e in items
        ]
    )
