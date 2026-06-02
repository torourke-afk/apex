"""SEORanking — organic keyword rank tracking by product category and week.

Captures weekly SERP position, page placement, search volume, and
week-over-week rank change for a keyword/category combination.
"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from src.models.base import ApexBase


class SEORanking(ApexBase):
    """Organic keyword ranking snapshot for a product category in a given week."""

    keyword: str = Field(min_length=1, description="Target keyword being tracked")
    product_category: str = Field(min_length=1, description="Product category associated with the keyword")
    rank_position: int = Field(ge=1, description="Rank position within the SERP page (1-indexed)")
    rank_page: int = Field(ge=1, description="SERP page number (1 = first page)")
    search_volume: int = Field(ge=0, description="Average monthly search volume for the keyword")
    week_start: date = Field(description="ISO date for the Monday of the tracking week")
    rank_change: int = Field(
        description="Position change vs. prior week (positive = improved rank, negative = dropped)",
    )
