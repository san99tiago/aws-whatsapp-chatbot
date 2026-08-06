################################################################################
# Auth Router: validates the Cognito login (AccessToken) and creates the
# auth-session item in DynamoDB (TTL of 10 mins). The DynamoDB Stream of the
# auth-sessions table then sends the "authenticated successfully" WhatsApp
# message to the user asynchronously.
################################################################################

# Built-in imports
import os
import time
from uuid import uuid4

# External imports
import boto3
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Own imports
from common.enums import DDBPrefixes
from common.logger import custom_logger
from common.helpers.dynamodb_helper import DynamoDBHelper

# Initialize DynamoDB Helper for the auth-sessions table
TABLE_NAME_AUTH_SESSIONS = os.environ["TABLE_NAME_AUTH_SESSIONS"]
AUTH_SESSION_TTL_SECONDS = int(os.environ.get("AUTH_SESSION_TTL_SECONDS", "600"))
dynamodb_helper_auth_sessions = DynamoDBHelper(table_name=TABLE_NAME_AUTH_SESSIONS)

cognito_client = boto3.client("cognito-idp")

router = APIRouter()
logger = custom_logger()


class AuthRequestModel(BaseModel):
    """Structured request contract for the Auth API."""

    access_token: str


@router.post("/auth", tags=["Auth"])
async def post_auth(input_body: AuthRequestModel):
    """
    Validates the Cognito AccessToken (obtained by the Web Portal after login)
    and creates the WhatsApp auth-session in DynamoDB with a TTL of 10 minutes.
    """
    try:
        correlation_id = str(uuid4())
        logger.append_keys(correlation_id=correlation_id)
        logger.info("Started post_auth() handler")

        # Validate the token against Cognito (raises if invalid/expired)
        cognito_user = cognito_client.get_user(AccessToken=input_body.access_token)
        user_attributes = {
            attribute["Name"]: attribute["Value"]
            for attribute in cognito_user.get("UserAttributes", [])
        }
        user_email = user_attributes.get("email", cognito_user.get("Username"))
        username = user_attributes.get("preferred_username", user_email.split("@")[0])
        phone_number = user_attributes.get("phone_number", "")
        logger.info(f"Cognito user validated: {user_email} (username: {username})")

        # Normalize the phone number to the WhatsApp format (no plus sign)
        formatted_number = phone_number.replace("+", "")

        # FALLBACK: resolve the phone from the USERNAME<->WHATSAPP mapping
        # (seeded by the CustomResource) when the Cognito attribute is missing
        if not formatted_number:
            logger.warning(
                f"User {user_email} has no phone_number attribute. "
                "Falling back to the USERNAME#<username>/MAPPING item"
            )
            mapping_item = dynamodb_helper_auth_sessions.get_item_by_pk_and_sk(
                partition_key=f"USERNAME#{username}",
                sort_key="MAPPING",
            )
            formatted_number = mapping_item.get("phone_number", {}).get("S", "")

        if not formatted_number:
            logger.error(f"No WhatsApp mapping found for user {user_email}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "error",
                    "details": "User has no WhatsApp phone number mapping configured",
                },
            )

        # Save auth session with TTL of 10 minutes (drives re-login after expiry)
        auth_item = {
            "PK": f"{DDBPrefixes.PK_USER.value}{formatted_number}",
            "SK": DDBPrefixes.SK_AUTH.value,
            "username": user_email,
            "phone_number": formatted_number,
            "correlation_id": correlation_id,
            "ttl": int(time.time()) + AUTH_SESSION_TTL_SECONDS,
        }
        result = dynamodb_helper_auth_sessions.put_item(auth_item)
        logger.debug(result, message_details="DynamoDB put_item() result")

        # SELF-HEALING: upsert the permanent USERNAME<->WHATSAPP mappings
        # (both directions, no TTL) to keep the 1:1 relation fresh and auditable
        dynamodb_helper_auth_sessions.put_item(
            {
                "PK": f"USERNAME#{username}",
                "SK": "MAPPING",
                "phone_number": formatted_number,
                "user_email": user_email,
            }
        )
        dynamodb_helper_auth_sessions.put_item(
            {
                "PK": f"{DDBPrefixes.PK_USER.value}{formatted_number}",
                "SK": "MAPPING",
                "username": username,
                "user_email": user_email,
            }
        )

        logger.info("Finished post_auth() successfully")
        return {"message": "ok", "details": f"User {user_email} authenticated"}

    except cognito_client.exceptions.NotAuthorizedException:
        logger.warning("Invalid or expired Cognito AccessToken")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "error", "details": "Invalid or expired token"},
        )
    except Exception as e:
        logger.error(f"Error in post_auth(): {e}")
        raise e
