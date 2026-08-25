"""Request and response models for the suggestions endpoint."""

from enum import Enum

from pydantic import BaseModel, Field


class SuggestionType(str, Enum):
    """Supported suggestion sources."""

    SIC = "sic"


class SuggestionsRequest(BaseModel):
    """Payload for the public suggestions route."""

    type: SuggestionType = Field(..., description="Suggestion source")
    query: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Text the user typed (maximum 100 characters)",
    )
    limit: int | None = Field(
        default=None,
        gt=0,
        description="Optional maximum number of suggestions",
    )
    include_scores: bool = Field(
        default=False,
        description="When true, include a score on each suggestion",
    )


class Suggestion(BaseModel):
    """A single suggestion returned to the caller."""

    display_text: str = Field(..., description="Suggestion text to display")
    score: float | None = Field(
        default=None,
        description="Optional ranking score from the SAYT service",
    )


class SuggestionsResponse(BaseModel):
    """Response payload for the suggestions route."""

    suggestions: list[Suggestion] = Field(
        ...,
        description="Ranked suggestions for the query",
    )
