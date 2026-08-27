"""Tests for the SAYT client."""

from http import HTTPStatus
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi import HTTPException

from api.services.sayt_client import SAYTClient
from api.services.token_provider import TokenProviderError


@pytest.mark.api
@pytest.mark.asyncio
async def test_suggest_posts_query_and_limit_with_auth_headers() -> None:
    """Pass authentication headers and the SAYT body to the suggestions request."""
    token_provider = AsyncMock()
    token_provider.get_headers.return_value = {"Authorization": "Bearer test-token"}

    expected_suggestions = [
        {"display_text": "Soft drinks manufacturing", "score": 0.95}
    ]
    response = Mock()
    response.status_code = HTTPStatus.OK
    response.json.return_value = {"suggestions": expected_suggestions}
    response.raise_for_status.return_value = None

    http_client = AsyncMock()
    http_client.post.return_value = response

    client = SAYTClient(
        base_url="http://localhost:8090",
        http_client=http_client,
        token_provider=token_provider,
    )

    result = await client.suggest(
        query="soft",
        limit=5,
        correlation_id="test-correlation-id",
    )

    assert result == expected_suggestions
    token_provider.get_headers.assert_awaited_once_with()
    http_client.post.assert_awaited_once_with(
        "http://localhost:8090/v1/suggestions",
        json={"query": "soft", "limit": 5},
        headers={"Authorization": "Bearer test-token"},
    )


@pytest.mark.api
@pytest.mark.asyncio
async def test_suggest_omits_limit_when_not_provided() -> None:
    """Do not send limit when the caller omitted it."""
    token_provider = AsyncMock()
    token_provider.get_headers.return_value = {}

    response = Mock()
    response.status_code = HTTPStatus.OK
    response.json.return_value = {"suggestions": []}
    response.raise_for_status.return_value = None

    http_client = AsyncMock()
    http_client.post.return_value = response

    client = SAYTClient(
        base_url="http://localhost:8090",
        http_client=http_client,
        token_provider=token_provider,
    )

    await client.suggest(query="soft")

    http_client.post.assert_awaited_once_with(
        "http://localhost:8090/v1/suggestions",
        json={"query": "soft"},
        headers={},
    )


@pytest.mark.api
@pytest.mark.asyncio
async def test_suggest_maps_token_provider_error_to_503() -> None:
    """Return a sanitised 503 when SAYT authentication fails."""
    token_provider = AsyncMock()
    token_provider.get_headers.side_effect = TokenProviderError(
        "Permission iam.serviceAccounts.getOpenIdToken denied"
    )
    http_client = AsyncMock()

    client = SAYTClient(
        base_url="http://localhost:8090",
        http_client=http_client,
        token_provider=token_provider,
    )

    with pytest.raises(HTTPException) as exc_info:
        await client.suggest(query="soft")

    assert exc_info.value.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert exc_info.value.detail == "Unable to authenticate to SAYT service"
    assert "getOpenIdToken" not in str(exc_info.value.detail)
    http_client.post.assert_not_awaited()


@pytest.mark.api
@pytest.mark.asyncio
async def test_suggest_maps_http_error_to_503() -> None:
    """Return a sanitised 503 when the SAYT service request fails."""
    token_provider = AsyncMock()
    token_provider.get_headers.return_value = {}
    http_client = AsyncMock()
    http_client.post.side_effect = httpx.HTTPError("Connection error")

    client = SAYTClient(
        base_url="http://localhost:8090",
        http_client=http_client,
        token_provider=token_provider,
    )

    with pytest.raises(HTTPException) as exc_info:
        await client.suggest(query="soft")

    assert exc_info.value.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert exc_info.value.detail == "Service is unavailable"
    assert "Connection error" not in str(exc_info.value.detail)


@pytest.mark.api
@pytest.mark.asyncio
async def test_suggest_maps_unexpected_error_to_500() -> None:
    """Return a sanitised 500 when an unexpected error occurs."""
    token_provider = AsyncMock()
    token_provider.get_headers.return_value = {}
    http_client = AsyncMock()
    http_client.post.side_effect = RuntimeError("boom: secret internals")

    client = SAYTClient(
        base_url="http://localhost:8090",
        http_client=http_client,
        token_provider=token_provider,
    )

    with pytest.raises(HTTPException) as exc_info:
        await client.suggest(query="soft")

    assert exc_info.value.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert exc_info.value.detail == "Unexpected internal error"
    assert "secret internals" not in str(exc_info.value.detail)
