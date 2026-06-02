"""LLMVisibilityScore — brand mention tracking across LLM/AEO platforms.

Tracks whether a brand appears in LLM responses for a given prompt,
including mention position and sentiment for AEO (Answer Engine Optimization).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field

from src.models.base import ApexBase


class LLMPlatform(str, Enum):
    GOOGLE_AI_OVERVIEWS = "google_ai_overviews"
    CHATGPT = "chatgpt"
    PERPLEXITY = "perplexity"
    CLAUDE = "claude"
    GEMINI = "gemini"
    COPILOT = "copilot"


class LLMVisibilityScore(ApexBase):
    """Brand visibility in an LLM response for a specific prompt and week."""

    platform: LLMPlatform
    prompt_text: str = Field(min_length=1, description="The prompt submitted to the LLM")
    prompt_category: str = Field(min_length=1, description="Category/intent of the prompt")
    market_dma: str = Field(description="DMA market identifier")
    brand: str = Field(min_length=1, description="Brand being tracked")
    week_start: date = Field(description="ISO date for the Monday of the tracking week")

    mentioned: bool = Field(description="Whether the brand was mentioned in the response")
    position: Optional[int] = Field(
        default=None,
        ge=1,
        description="Ordinal position of first mention (1-indexed); null if not mentioned",
    )
    sentiment_score: Decimal = Field(
        ge=Decimal("-1"),
        le=Decimal("1"),
        decimal_places=4,
        description="Sentiment of the mention from -1 (negative) to +1 (positive)",
    )
    citation_url: Optional[str] = Field(
        default=None,
        description="URL cited in the LLM response for this brand, if any",
    )
