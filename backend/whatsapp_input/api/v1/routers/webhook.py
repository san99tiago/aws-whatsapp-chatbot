# Built-in imports
import os
from typing import Annotated
from uuid import uuid4

# External imports
from fastapi import APIRouter, Header, Query, Request, Response, status

# Own imports
from whatsapp_input.common.logger import custom_logger


# Meta API Callback Token
META_API_CALLBACK_TOKEN = "PENDING_ADD_TOKEN_FROM_SECRETS_MANAGER"  # TODO (pending)


logger = custom_logger()

router = APIRouter()


@router.get("/webhook", tags=["Chatbot"])
async def get_chatbot_webhook(
    hub_challenge_query_param: str = Query(..., alias="hub.challenge"),
    hub_verify_token_query_param: str = Query(..., alias="hub.verify_token"),
    correlation_id: Annotated[str | None, Header()] = uuid4(),
):
    try:
        logger.append_keys(correlation_id=correlation_id)
        logger.info("Started chatbot handler for get_chatbot_webhook()")
        logger.info("Finished get_chatbot_webhook() successfully")

        # TODO: Remove these logs after initial validations
        logger.debug(f"hub_challenge_query_param: {hub_challenge_query_param}")
        logger.debug(f"hub_verify_token_query_param: {hub_verify_token_query_param}")

        # TODO: MIGRATE TOKEN VALIDATION TO DEDICATED AUTHORIZER!!!
        if hub_verify_token_query_param == META_API_CALLBACK_TOKEN:
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
    correlation_id: Annotated[str | None, Header()] = uuid4(),
):
    try:
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

        # TODO: Validate body and process it accordingly
        # TODO: Save chatbot data in DynamoDB
        # TODO: Enhance return

        result = {"message": "dummy post result"}
        return result

    except Exception as e:
        logger.error(f"Error in post_chatbot_webhook(): {e}")
        raise e
