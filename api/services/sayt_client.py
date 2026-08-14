"""Client service for the SAYT API."""

import httpx

from api.services.token_provider import TokenProvider


class SAYTClient:  # pylint: disable=too-few-public-methods
    """Client for the SAYT service.

    The client is initialised at application startup and provides the
    dependencies required for future SAYT API requests.
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
