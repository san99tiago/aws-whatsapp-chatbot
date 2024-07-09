# Built-in imports
import os

# External imports
from urllib.parse import urljoin

# Own imports
from state_machine.integrations.meta.enums import MetaAPIVersion
from common.helpers.secrets_helper import SecretsHelper

# Load environment variables
META_ENDPOINT = os.environ.get("META_ENDPOINT")


def get_api_endpoint(path: str) -> str:
    base = META_ENDPOINT + MetaAPIVersion.V_20.value
    return urljoin(base, path)


def get_api_headers(bearer_token: str) -> dict:
    return {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
