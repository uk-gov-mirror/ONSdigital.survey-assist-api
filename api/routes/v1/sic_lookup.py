"""Module that provides the SIC lookup endpoint for the Survey Assist API.

This module contains the SIC lookup endpoint for the Survey Assist API.
It defines the endpoint for looking up SIC codes based on descriptions.
"""

# pylint: disable=duplicate-code  # SIC/SOC routes share structure by design

from fastapi import APIRouter, Depends, Request
from survey_assist_utils.logging import get_logger

from api.routes.v1.lookup_handlers import execute_lookup_request
from api.services.sayt_client import SAYTClient
from api.services.sic_lookup_client import SICLookupClient

logger = get_logger(__name__)
router = APIRouter(tags=["SIC Lookup"])


def get_lookup_client(request: Request) -> SICLookupClient:
    """Get a SIC lookup client instance.

    Args:
        request: The FastAPI request object containing the app state.

    Returns:
        SICLookupClient: A SIC lookup client instance.
    """
    return request.app.state.sic_lookup_client


lookup_client_dependency = Depends(get_lookup_client)


# Temp - to overload sic-lookup endpoint with SAYT client for testing
def get_sayt_client(request: Request) -> SAYTClient:
    """Get the application-scoped SAYT client."""
    return request.app.state.sayt_client


sayt_client_dependency = Depends(get_sayt_client)


@router.get("/sic-lookup")
async def sic_lookup(
    description: str,
    similarity: bool = False,
    lookup_client: SICLookupClient = lookup_client_dependency,
    sayt_client: SAYTClient = sayt_client_dependency,
):
    """Lookup the SIC code for a given description.

    Args:
        description (str): The description to look up.
        similarity (bool, optional): Whether to use similarity search. Defaults to False.
        lookup_client (SICLookupClient): The SIC lookup client instance.
        sayt_client (SAYTClient): The SAYT client instance.

    Returns:
        dict: The SIC lookup result.

    Example:
        ```json
        {
            "code": "43210",
            "description": "Electrical installation",
            "potential_matches": {
                "descriptions": [
                    "Electrical installation",
                    "Electrical contractor",
                    "Electrician"
                ]
            }
        }
    ```
    """
    if not similarity:
        logger.info("STD SIC Lookup using vector store")
        return execute_lookup_request(
            description=description,
            similarity=similarity,
            lookup_client=lookup_client,
            endpoint_name="sic-lookup",
            code_label="SIC",
        )

    logger.info("SAYT Override of SIC Lookup using SAYT Service")

    response = await sayt_client.suggestions(description)

    return {
        "results": [
            {"en": suggestion["display_text"]} for suggestion in response["suggestions"]
        ]
    }
