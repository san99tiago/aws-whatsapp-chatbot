# Built-in imports
import os
from typing import Optional

# External imports
from aws_lambda_powertools import Logger
import requests


# Own imports
from common.helpers.secrets_helper import SecretsHelper
from common.logger import custom_logger
from state_machine.integrations.meta.api_utils import (
    get_api_endpoint,
    get_api_headers,
)
from state_machine.integrations.meta.schemas import MetaPostMessageModel


SECRET_NAME = os.environ["SECRET_NAME"]
secrets_helper = SecretsHelper(SECRET_NAME)


class MetaAPI:
    """
    Class that contains the base helpers for interacting with the Meta API.
    """

    def __init__(self, logger: Optional[Logger] = None) -> None:
        self.logger = logger or custom_logger()
        self.load_meta_configurations()

    def load_meta_configurations(self) -> None:
        """
        Method to load Meta configurations from Secrets Manager and initialize
        the endpoint and headers (secret fetched lazily at runtime, NOT at import).
        """
        self.logger.debug("Loading Meta configurations from Secrets Manager...")
        self.meta_secret_json = secrets_helper.get_secret_value()
        _meta_token = self.meta_secret_json.get("META_TOKEN")
        _meta_from_phone_number_id = self.meta_secret_json.get(
            "META_FROM_PHONE_NUMBER_ID"
        )
        self.api_headers = get_api_headers(bearer_token=_meta_token)
        self.api_endpoint = get_api_endpoint(f"{_meta_from_phone_number_id}/messages")

    def post_message(
        self,
        text_message: str,
        to_phone_number: str,
        original_message_id: Optional[str] = None,
    ) -> dict:
        """
        Method to send a POST message request to the Meta API.

        :param text_message (str): text_message to send in the POST request.
        :param to_phone_number (str): Phone number to send the message to.
        :param original_message_id (str): Original message ID to reply to.
        """

        self.logger.info(f"Starting POST request to Meta API: {self.api_endpoint}")
        self.logger.debug(f"text_message to send: {text_message}")

        # Create response model for the POST request (JSON data)
        message_data_model = MetaPostMessageModel(
            to=to_phone_number,
            text={"body": text_message},
            context=(
                {"message_id": original_message_id} if original_message_id else None
            ),
        )

        try:
            response = requests.post(
                self.api_endpoint,
                headers=self.api_headers,
                json=message_data_model.model_dump(exclude_none=True),
                timeout=30,
            )
        except Exception as e:
            self.logger.exception(
                "Unexpected error occurred while executing Meta API request."
            )
            raise e

        self.logger.info(f"Response has status_code: {response.status_code}")
        self.logger.info(f"Response data: {response.text}")
        return response.json()

    def get_media_url(self, media_id: str) -> dict:
        """
        Method to FETCH the media metadata (download URL) for a given META
        media ID (e.g. the <audio_id> received in the WhatsApp webhook).

        :param media_id (str): META media ID to fetch.
        :return (dict): Media metadata with <url> and <mime_type> keys.
        """
        media_endpoint = get_api_endpoint(media_id)
        self.logger.info(f"Fetching media URL from Meta API: {media_endpoint}")
        response = requests.get(media_endpoint, headers=self.api_headers, timeout=30)
        self.logger.info(f"Media URL response status_code: {response.status_code}")
        response.raise_for_status()
        media_info = response.json()
        self.logger.debug(media_info, message_details="Meta media metadata")
        return media_info

    def download_media(self, media_url: str) -> bytes:
        """
        Method to DOWNLOAD the media binary content from the (short-lived)
        META media URL (requires the Bearer token authorization).

        :param media_url (str): Short-lived media URL returned by get_media_url.
        :return (bytes): Raw media content (e.g. OGG/MP3 audio bytes).
        """
        self.logger.info("Downloading media binary content from Meta API")
        response = requests.get(media_url, headers=self.api_headers, timeout=60)
        self.logger.info(
            f"Media download status_code: {response.status_code} "
            f"(size: {len(response.content)} bytes)"
        )
        response.raise_for_status()
        return response.content
