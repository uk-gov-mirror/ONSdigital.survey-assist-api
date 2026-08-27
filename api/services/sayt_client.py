"""Client for the SAYT suggestions service."""

import time
from http import HTTPStatus
from typing import Any

import httpx
from fastapi import HTTPException
from survey_assist_utils.logging import get_logger

from api.services.token_provider import TokenProvider, TokenProviderError
from utils.survey import truncate_identifier

logger = get_logger(__name__)


class SAYTClient:
    """Client for the SAYT suggestions service.

    The client is initialised at application startup and shares the API HTTP
    client. Authentication tokens are reused until they need refreshing.
    """

    def __init__(
        self,
        base_url: str,
        *,
        http_client: httpx.AsyncClient,
        token_provider: TokenProvider,
    ) -> None:
        """Initialise the SAYT client.

        Args:
            base_url: Base URL of the SAYT service.
            http_client: Shared async HTTP client for outbound requests.
            token_provider: Provider for authentication tokens.
        """
        self.base_url = base_url
        self._http_client = http_client
        self._token_provider = token_provider

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Return the shared async HTTP client."""
        return self._http_client

    def get_suggestions_url(self) -> str:
        """Return the SAYT suggestions endpoint URL."""
        return f"{self.base_url}/v1/suggestions"

    async def suggest(
        self,
        query: str,
        limit: int | None = None,
        correlation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the SAYT service for suggestions.

        Args:
            query: Text the user typed.
            limit: Optional maximum number of suggestions.
            correlation_id: Optional correlation ID for request tracing.

        Returns:
            A list of suggestion dicts with ``display_text`` and ``score``.

        Raises:
            HTTPException: If authentication or the downstream request fails.
        """
        url = self.get_suggestions_url()
        payload: dict[str, Any] = {"query": query}
        if limit is not None:
            payload["limit"] = limit

        try:
            headers = await self._token_provider.get_headers()
            if headers:
                logger.debug("Using authentication headers for SAYT service")

            start_time = time.perf_counter()
            logger.info(
                "SAYT request sent - suggestions",
                url=url,
                query=truncate_identifier(query),
                limit=str(limit) if limit is not None else "",
                correlation_id=correlation_id,
            )
            response = await self._http_client.post(
                url,
                json=payload,
                headers=headers,
            )
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(
                "SAYT response received - suggestions",
                status_code=str(response.status_code),
                duration_ms=str(duration_ms),
                query=truncate_identifier(query),
                correlation_id=correlation_id,
            )
            response.raise_for_status()
            result = response.json()
            suggestions = (
                result.get("suggestions") if isinstance(result, dict) else None
            )
            if not isinstance(suggestions, list):
                logger.warning(
                    "SAYT suggestions response type",
                    type=str(type(result).__name__),
                    correlation_id=correlation_id,
                )
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="SAYT service returned an invalid suggestions response",
                )

            logger.info(
                "SAYT suggestions summary",
                results_count=str(len(suggestions)),
                query=truncate_identifier(query),
                correlation_id=correlation_id,
            )
            return suggestions

        except TokenProviderError as e:
            logger.error("Failed to authenticate to SAYT service", error=str(e))
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Unable to authenticate to SAYT service",
            ) from e

        except HTTPException:
            raise

        except httpx.HTTPError as e:
            logger.error(
                "Failed to search SAYT service",
                error=str(e),
                query=truncate_identifier(query),
                correlation_id=correlation_id,
            )
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail="Service is unavailable",
            ) from e

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(
                "Unexpected error searching SAYT service",
                error=str(e),
                query=truncate_identifier(query),
                correlation_id=correlation_id,
            )
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Unexpected internal error",
            ) from e
