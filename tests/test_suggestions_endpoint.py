"""Tests for the /suggestions endpoint."""

from collections.abc import Iterator
from http import HTTPStatus
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.main import app
from api.routes.v1.suggestions import get_sayt_client
from api.services.sayt_client import SAYTClient


def _setup_sayt_client_override(mock_client: SAYTClient) -> None:
    """Override the SAYT client dependency with a mock."""
    app.dependency_overrides[get_sayt_client] = lambda: mock_client


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    """Clear FastAPI dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()


@pytest.mark.api
def test_suggestions_strips_scores_by_default() -> None:
    """Omit scores unless the caller asks for them."""
    mock_client = AsyncMock(spec=SAYTClient)
    mock_client.suggest.return_value = [
        {"display_text": "Soft drinks manufacturing", "score": 0.95}
    ]
    _setup_sayt_client_override(mock_client)

    response = TestClient(app).post(
        "/v1/survey-assist/suggestions",
        json={"type": "sic", "query": "soft", "limit": 5},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "suggestions": [{"display_text": "Soft drinks manufacturing"}]
    }
    mock_client.suggest.assert_awaited_once_with(
        query="soft",
        limit=5,
        correlation_id=mock_client.suggest.await_args.kwargs["correlation_id"],
    )


@pytest.mark.api
def test_suggestions_includes_scores_when_requested() -> None:
    """Include scores when include_scores is true."""
    mock_client = AsyncMock(spec=SAYTClient)
    mock_client.suggest.return_value = [
        {"display_text": "Soft drinks manufacturing", "score": 0.95}
    ]
    _setup_sayt_client_override(mock_client)

    response = TestClient(app).post(
        "/v1/survey-assist/suggestions",
        json={
            "type": "sic",
            "query": "soft",
            "include_scores": True,
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "suggestions": [{"display_text": "Soft drinks manufacturing", "score": 0.95}]
    }
    mock_client.suggest.assert_awaited_once_with(
        query="soft",
        limit=None,
        correlation_id=mock_client.suggest.await_args.kwargs["correlation_id"],
    )


@pytest.mark.api
def test_suggestions_rejects_unsupported_type() -> None:
    """Reject suggestion types other than sic."""
    mock_client = AsyncMock(spec=SAYTClient)
    _setup_sayt_client_override(mock_client)

    response = TestClient(app).post(
        "/v1/survey-assist/suggestions",
        json={"type": "soc", "query": "soft"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    mock_client.suggest.assert_not_awaited()


@pytest.mark.api
def test_suggestions_rejects_empty_query() -> None:
    """Reject an empty query string."""
    mock_client = AsyncMock(spec=SAYTClient)
    _setup_sayt_client_override(mock_client)

    response = TestClient(app).post(
        "/v1/survey-assist/suggestions",
        json={"type": "sic", "query": ""},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    mock_client.suggest.assert_not_awaited()


@pytest.mark.api
def test_suggestions_rejects_query_over_max_length() -> None:
    """Reject a query longer than 100 characters with 422."""
    mock_client = AsyncMock(spec=SAYTClient)
    _setup_sayt_client_override(mock_client)

    response = TestClient(app).post(
        "/v1/survey-assist/suggestions",
        json={"type": "sic", "query": "x" * 101},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "at most 100 characters" in response.text
    mock_client.suggest.assert_not_awaited()


@pytest.mark.api
def test_suggestions_rejects_limit_over_maximum() -> None:
    """Reject a limit greater than 50 with 422."""
    mock_client = AsyncMock(spec=SAYTClient)
    _setup_sayt_client_override(mock_client)

    response = TestClient(app).post(
        "/v1/survey-assist/suggestions",
        json={"type": "sic", "query": "soft", "limit": 51},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert "less than or equal to 50" in response.text
    mock_client.suggest.assert_not_awaited()


@pytest.mark.api
def test_suggestions_maps_client_unavailable_to_503() -> None:
    """Surface SAYT client failures as 503."""
    mock_client = AsyncMock(spec=SAYTClient)
    mock_client.suggest.side_effect = HTTPException(
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        detail="Unable to authenticate to SAYT service",
    )
    _setup_sayt_client_override(mock_client)

    response = TestClient(app).post(
        "/v1/survey-assist/suggestions",
        json={"type": "sic", "query": "soft"},
    )

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.json() == {"detail": "Unable to authenticate to SAYT service"}
