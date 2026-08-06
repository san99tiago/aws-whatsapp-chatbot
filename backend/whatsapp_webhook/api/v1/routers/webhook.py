# Built-in imports
import os
from datetime import datetime, timezone
from uuid import uuid4

# External imports
from fastapi import APIRouter, Query, Request, Response, status

# Own imports
from common.models.audio_message_model import AudioMessageModel
from common.models.text_message_model import TextMessageModel
from common.logger import custom_logger
from common.helpers.dynamodb_helper import DynamoDBHelper
from common.helpers.secrets_helper import SecretsHelper

# Initialize Secrets Manager Helper
SECRET_NAME = os.environ["SECRET_NAME"]
secrets_helper = SecretsHelper(SECRET_NAME)

# Initialize DynamoDB Helper
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
ENDPOINT_URL = os.environ.get("ENDPOINT_URL")  # Used for local testing
dynamodb_helper = DynamoDBHelper(table_name=DYNAMODB_TABLE, endpoint_url=ENDPOINT_URL)


router = APIRouter()
logger = custom_logger()


@router.get("/webhook", tags=["Chatbot"])
async def get_chatbot_webhook(
    hub_mode_query_param: str = Query("subscribe", alias="hub.mode"),
    hub_challenge_query_param: str = Query(..., alias="hub.challenge"),
    hub_verify_token_query_param: str = Query(..., alias="hub.verify_token"),
):
    """
    META Webhook verification endpoint (GET). META sends <hub.challenge> and
    <hub.verify_token>, and expects the challenge echoed back when the token
    matches the one configured in the AWS Secret (key: AWS_API_KEY_TOKEN).
    """
    try:
        correlation_id = str(uuid4())
        logger.append_keys(correlation_id=correlation_id)
        logger.info("Started chatbot handler for get_chatbot_webhook()")
        logger.debug(f"hub_mode_query_param: {hub_mode_query_param}")

        # TODO: MIGRATE TOKEN VALIDATION TO DEDICATED AUTHORIZER!!!
        AWS_API_KEY_TOKEN = secrets_helper.get_secret_value("AWS_API_KEY_TOKEN")
        if hub_verify_token_query_param == AWS_API_KEY_TOKEN:
            logger.info("Webhook verification successful (token matched)")
            return Response(
                content=hub_challenge_query_param,
                status_code=status.HTTP_200_OK,
                headers={"Content-Type": "text/html;charset=UTF-8"},
            )

        logger.warning("Webhook verification failed (invalid verify token)")
        return Response(
            content='{"error": "Invalid authorization or authentication"}',
            status_code=status.HTTP_403_FORBIDDEN,
            headers={"Content-Type": "application/json"},
        )

    except Exception as e:
        logger.error(f"Error in get_chatbot_webhook(): {e}")
        raise e


@router.post("/webhook", tags=["Chatbot"])
async def post_chatbot_webhook(
    request: Request,  # Only for initial debugging purposes
    input_body: dict,
):
    """
    META Webhook callback endpoint (POST). Receives WhatsApp events (messages,
    statuses, etc.) and stores supported user messages in DynamoDB. The DynamoDB
    Stream then asynchronously triggers the processing State Machine.
    """
    try:
        correlation_id = str(uuid4())
        logger.append_keys(correlation_id=correlation_id)
        logger.info("Started chatbot handler for post_chatbot_webhook()")
        logger.debug(input_body, message_details="Received body")
        logger.debug(f"HEADERS: {request.headers}")

        # Gracefully acknowledge non-message events (e.g. delivery/read statuses)
        webhook_value = (
            input_body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
        )
        messages = webhook_value.get("messages")
        if not messages:
            logger.info("No user messages in event (likely a status update). Skipping")
            return {"message": "ok", "details": "Event without messages (skipped)"}

        message = messages[0]
        wpp_from_phone_number = message["from"]
        wpp_id = message["id"]
        wpp_timestamp = message["timestamp"]
        wpp_type = message["type"]
        created_at = datetime.now(timezone.utc).isoformat()

        # Initialize the Message Model based on the type of message
        message_item = None
        if wpp_type == "text":
            message_item = TextMessageModel(
                PK=f"NUMBER#{wpp_from_phone_number}",
                SK=f"MESSAGE#{created_at}",
                from_number=wpp_from_phone_number,
                created_at=created_at,
                type=wpp_type,
                whatsapp_id=wpp_id,
                whatsapp_timestamp=wpp_timestamp,
                text=message["text"]["body"],
                correlation_id=correlation_id,
            )
            logger.info(
                message_item.model_dump(),
                message_details="Successfully created TextMessageModel instance",
            )
        elif wpp_type in ("audio", "voice"):
            # Audio/voice-note messages arrive with a META media ID that MUST
            # be fetched later (done in the State Machine "Fetch Audio" step)
            audio_info = message.get("audio", {}) or message.get("voice", {})
            message_item = AudioMessageModel(
                PK=f"NUMBER#{wpp_from_phone_number}",
                SK=f"MESSAGE#{created_at}",
                from_number=wpp_from_phone_number,
                created_at=created_at,
                type=wpp_type,
                whatsapp_id=wpp_id,
                whatsapp_timestamp=wpp_timestamp,
                audio_id=audio_info["id"],
                mime_type=audio_info.get("mime_type"),
                voice=audio_info.get("voice"),
                correlation_id=correlation_id,
            )
            logger.info(
                message_item.model_dump(),
                message_details="Successfully created AudioMessageModel instance",
            )
        # TODO: Add other types of messages (image, video, etc)

        # Save the message to DynamoDB (messages are kept FOREVER, no TTL)
        if message_item:
            result = dynamodb_helper.put_item(message_item.model_dump())
            logger.debug(result, message_details="DynamoDB put_item() result")
        else:
            logger.warning(f"Unsupported message type <{wpp_type}> (not stored yet)")

        logger.info("Finished post_chatbot_webhook() successfully")
        return {"message": "ok", "details": "Received message"}

    except Exception as e:
        logger.error(f"Error in post_chatbot_webhook(): {e}")
        raise e
