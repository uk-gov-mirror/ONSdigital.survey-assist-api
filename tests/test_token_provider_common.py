"""Shared helpers for token-provider auth failure client tests.

Used to avoid duplicate-code (e.g. pylint R0801) between vector-store and SAYT
client tests while keeping the sanitised 503 behaviour aligned.
"""

from http import HTTPStatus
from unittest.mock import AsyncMock

from fastapi import HTTPException

from api.services.token_provider import TokenProviderError

_DEFAULT_TOKEN_PROVIDER_ERROR = (
    "Permission iam.serviceAccounts.getOpenIdToken denied"
)


def mocks_for_token_provider_auth_failure() -> tuple[AsyncMock, AsyncMock]:
    """Return token provider and HTTP client mocks that fail authentication."""
    token_provider = AsyncMock()
    token_provider.get_headers.side_effect = TokenProviderError(
        _DEFAULT_TOKEN_PROVIDER_ERROR
    )
    return token_provider, AsyncMock()


def assert_sanitised_auth_failure_503(
    exc: HTTPException,
    expected_detail: str,
) -> None:
    """Assert a sanitised 503 that does not leak token-provider internals."""
    assert exc.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert exc.detail == expected_detail
    assert "getOpenIdToken" not in str(exc.detail)
