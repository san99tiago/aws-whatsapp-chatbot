################################################################################
# Helper to send WhatsApp messages directly from trigger Lambdas (e.g. the
# "authenticated successfully" confirmation after a Web Portal login).
################################################################################

# Built-in imports
import os

# External imports
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import (
    DynamoDBRecord,
)

# Own imports
from common.logger import custom_logger
from state_machine.integrations.meta.api_requests import MetaAPI

LOGGER = custom_logger()

BOT_NAME = os.environ.get("BOT_NAME", "SantiBank Assistant")


def trigger_response(record: DynamoDBRecord, logger: Logger = None) -> None:
    """
    Send the "authenticated successfully" WhatsApp message based on the
    auth-sessions DynamoDB Stream record.

    :param record (DynamoDBRecord): Event from the DynamoDB Stream Record.
    :param logger (Logger, optional): Logger object. Defaults to None.
    """
    logger = logger or LOGGER
    try:
        response_message = (
            f"✅ Te autenticaste exitosamente con {BOT_NAME}. "
            f"¿Cómo puedo apoyarte hoy?"
        )

        # PK has the "USER#<phone_number>" format
        pk_string = record.dynamodb.new_image["PK"]
        phone_number = pk_string.split("#")[1].replace("+", "")

        # One-line identity footer (consistent with the State Machine messages)
        username = record.dynamodb.new_image.get("username", "")
        response_message += f"\n\n🔐 Autenticado: Sí ✅ | 👤 {username}"

        logger.info(f"Sending auth-successful message to {phone_number}")
        meta_api = MetaAPI(logger=logger)
        response = meta_api.post_message(
            text_message=response_message,
            to_phone_number=phone_number,
        )
        logger.debug(response, message_details="Meta API auth-successful response")

        if "error" in response:
            # Do NOT raise exceptions here: it could cause undesired retry loops!
            logger.error(
                response,
                message_details="Error in POST WhatsApp auth-successful message",
            )
    except Exception as err:
        # Do NOT raise exceptions here: it could cause undesired retry loops!
        logger.exception(f"Error sending auth-successful message: {err}")
