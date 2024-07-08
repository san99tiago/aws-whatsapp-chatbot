# Built-in imports
import os
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

# External imports
from fastapi import APIRouter, Header, Query, Request, Response, status

# Own imports
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
    hub_challenge_query_param: str = Query(..., alias="hub.challenge"),
    hub_verify_token_query_param: str = Query(..., alias="hub.verify_token"),
):
    try:
        correlation_id = str(uuid4())
        logger.append_keys(correlation_id=correlation_id)
        logger.info("Started chatbot handler for get_chatbot_webhook()")
        logger.info("Finished get_chatbot_webhook() successfully")

        # TODO: Remove these logs after initial validations
        logger.debug(f"hub_challenge_query_param: {hub_challenge_query_param}")
        logger.debug(f"hub_verify_token_query_param: {hub_verify_token_query_param}")

        # TODO: MIGRATE TOKEN VALIDATION TO DEDICATED AUTHORIZER!!!
        AWS_API_KEY_TOKEN = secrets_helper.get_secret_value("AWS_API_KEY_TOKEN")
        if hub_verify_token_query_param == AWS_API_KEY_TOKEN:
            return Response(
                content=hub_challenge_query_param,
                status_code=status.HTTP_200_OK,
                headers={"Content-Type": "text/html;charset=UTF-8"},
            )

        return {"error": "Invalid authorization or authentication"}

    except Exception as e:
        logger.error(f"Error in get_chatbot_webhook(): {e}")
        raise e


@router.post("/webhook", tags=["Chatbot"])
async def post_chatbot_webhook(
    request: Request,  # Only for initial debugging purposes
    input_body: dict,
):
    try:
        correlation_id = str(uuid4())
        logger.append_keys(correlation_id=correlation_id)
        logger.info(
            input_body, message_details="Received body in post_chatbot_webhook()"
        )
        logger.info("Started chatbot handler for post_chatbot_webhook()")
        logger.info("Finished post_chatbot_webhook() successfully")

        # TODO: Remove these logs after initial validations
        logger.debug(f"HEADERS: {request.headers}")
        logger.debug(f"QUERY_PARAMS: {request.query_params}")
        logger.debug(f"PATH_PARAMS: {request.path_params}")
        logger.debug(f"INPUT_BODY: {input_body}")

        # Intentionally break code if parsing fails
        message = input_body["entry"][0]["changes"][0]["value"]["messages"][0]
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
        # TODO: Add other types of messages (image, voice, video, etc)

        # Save the message to DynamoDB
        if message_item:
            result = dynamodb_helper.put_item(message_item.model_dump())
            logger.debug(result, message_details="DynamoDB put_item() result")

        result = {"message": "ok", "details": "Received message"}
        return result

    except Exception as e:
        logger.error(f"Error in post_chatbot_webhook(): {e}")
        raise e
