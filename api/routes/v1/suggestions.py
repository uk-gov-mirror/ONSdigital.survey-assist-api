"""Suggestions endpoint for the Survey Assist API."""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from survey_assist_utils.logging import get_logger

from api.models.suggestions import (
    Suggestion,
    SuggestionsRequest,
    SuggestionsResponse,
)
from api.services.sayt_client import SAYTClient
from utils.survey import truncate_identifier

router = APIRouter(tags=["Suggestions"])
logger = get_logger(__name__)


def get_sayt_client(request: Request) -> SAYTClient:
    """Get the SAYT client from app state."""
    return request.app.state.sayt_client


@router.post(
    "/suggestions",
    response_model=SuggestionsResponse,
    response_model_exclude_none=True,
)
async def get_suggestions(
    suggestions_request: SuggestionsRequest,
    sayt_client: Annotated[SAYTClient, Depends(get_sayt_client)],
) -> SuggestionsResponse:
    """Return typeahead suggestions from the SAYT service.

    Args:
        suggestions_request: Public suggestions request.
        sayt_client: SAYT client from application startup.

    Returns:
        Ranked suggestions. Scores are included only when requested.
    """
    start_time = time.perf_counter()
    request_timestamp = int(time.time())
    correlation_id = (
        f"{truncate_identifier(suggestions_request.query)}_{request_timestamp}"
    )
    logger.info(
        "Request received for suggestions",
        type=suggestions_request.type.value,
        query=truncate_identifier(suggestions_request.query),
        limit=(
            str(suggestions_request.limit)
            if suggestions_request.limit is not None
            else ""
        ),
        include_scores=str(suggestions_request.include_scores),
        correlation_id=correlation_id,
    )

    raw_suggestions = await sayt_client.suggest(
        query=suggestions_request.query,
        limit=suggestions_request.limit,
        correlation_id=correlation_id,
    )

    suggestions = [
        _map_suggestion(item, include_scores=suggestions_request.include_scores)
        for item in raw_suggestions
        if isinstance(item, dict) and item.get("display_text")
    ]

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    logger.info(
        "Response sent for suggestions",
        results_count=str(len(suggestions)),
        include_scores=str(suggestions_request.include_scores),
        duration_ms=str(duration_ms),
        correlation_id=correlation_id,
    )
    return SuggestionsResponse(suggestions=suggestions)


def _map_suggestion(item: dict, *, include_scores: bool) -> Suggestion:
    """Map a SAYT service suggestion to the public response model."""
    suggestion = Suggestion(display_text=str(item["display_text"]))
    if include_scores and "score" in item:
        suggestion.score = item["score"]
    return suggestion
