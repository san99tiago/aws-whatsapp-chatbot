# Built-in imports
import os

# External imports
from urllib.parse import urljoin

# Load environment variables (configured via cdk.json app_config)
META_ENDPOINT = os.environ.get("META_ENDPOINT", "https://graph.facebook.com/")
META_API_VERSION = os.environ.get("META_API_VERSION", "v26.0")


def get_api_endpoint(path: str) -> str:
    """
    Build the full META Graph API endpoint for a given path.
    Note: the base MUST have a trailing slash so that urljoin keeps the version.
    """
    base = f"{META_ENDPOINT.rstrip('/')}/{META_API_VERSION}/"
    return urljoin(base, path)


def get_api_headers(bearer_token: str) -> dict:
    return {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
