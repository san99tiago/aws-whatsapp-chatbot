################################################################################
# "Check Auth" step: validates if the WhatsApp user has an active auth session
# in DynamoDB (TTL of 10 mins). Supports full BYPASS when AUTH_ENABLED=false
# (auth_enabled=false in cdk.json), routing everyone as incognito users.
################################################################################

# Built-in imports
import os
import time

# External imports
import boto3

# Own imports
from state_machine.base_step_function import BaseStepFunction
from common.enums import DDBPrefixes, StateMachineMessageTypes
from common.helpers.dynamodb_helper import DynamoDBHelper
from common.logger import custom_logger


logger = custom_logger()

# Environment variables (configured via cdk.json app_config)
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false")
TABLE_NAME_AUTH_SESSIONS = os.environ.get("TABLE_NAME_AUTH_SESSIONS", "")
TABLE_NAME_BANK_CLIENTS = os.environ.get("TABLE_NAME_BANK_CLIENTS", "")
AUTH_PORTAL_URL = os.environ.get("AUTH_PORTAL_URL", "")
BOT_NAME = os.environ.get("BOT_NAME", "SantiBank Assistant")
AUTH_SESSION_TTL_SECONDS = int(os.environ.get("AUTH_SESSION_TTL_SECONDS", "600"))

dynamodb_client = boto3.client("dynamodb")


class CheckAuth(BaseStepFunction):
    """
    This class validates the authentication status of the user for the State Machine.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)
        # Lazy init (only when auth is enabled, table exists)
        self.dynamodb_helper_auth_sessions = (
            DynamoDBHelper(table_name=TABLE_NAME_AUTH_SESSIONS)
            if AUTH_ENABLED == "true" and TABLE_NAME_AUTH_SESSIONS
            else None
        )

    def load_user_profile(self, phone_number: str) -> None:
        """
        Method to load the user's profile (metadata) for hyperpersonalization:
        full name, nickname and key data. ONLY executed for AUTHENTICATED
        users (unauthenticated users stay fully incognito). Resolution:
        phone -> USER#<phone>/MAPPING -> user_email -> bank-clients item.
        """
        self.event["profile"] = {}
        try:
            if not self.dynamodb_helper_auth_sessions or not TABLE_NAME_BANK_CLIENTS:
                return

            # Resolve the user_email from the auth session OR the mapping
            user_email = self.event.get("username", "")
            if user_email in ("", "incognito"):
                mapping_item = self.dynamodb_helper_auth_sessions.get_item_by_pk_and_sk(
                    partition_key=f"{DDBPrefixes.PK_USER.value}{phone_number}",
                    sort_key=DDBPrefixes.SK_MAPPING.value,
                )
                user_email = mapping_item.get("user_email", {}).get("S", "")
            if not user_email:
                self.logger.info(f"No profile mapping found for {phone_number}")
                return

            # Load the profile (metadata) from the bank-clients table
            result = dynamodb_client.get_item(
                TableName=TABLE_NAME_BANK_CLIENTS,
                Key={"user_email": {"S": user_email}},
            )
            item = result.get("Item", {})
            if not item:
                self.logger.info(f"No bank-clients profile found for {user_email}")
                return

            self.event["profile"] = {
                "user_email": item["user_email"]["S"],
                "full_name": item.get("full_name", {}).get("S", ""),
                "username": item.get("username", {}).get("S", ""),
                "nickname": item.get("nickname", {}).get("S", ""),
                "hyperpersonalization": {
                    key: value.get("S", "")
                    for key, value in item.get("hyperpersonalization", {})
                    .get("M", {})
                    .items()
                },
            }
            self.logger.info(
                f"Loaded profile for {user_email} "
                f"(nickname: {self.event['profile']['nickname']})"
            )
        except Exception as e:
            # Profile loading must NEVER break the message processing
            self.logger.warning(f"Could not load user profile: {e}")

    def check_auth(self):
        """
        Method to validate the user's auth session and enrich the event with
        <authenticated>, <username> and <profile> fields (Agent's API-Contract).
        """
        self.logger.info("Starting check_auth validation")

        phone_number = (
            self.event.get("input", {})
            .get("dynamodb", {})
            .get("NewImage", {})
            .get("from_number", {})
            .get("S", "UNKNOWN")
        )

        # Default: incognito user (reduced subset of Agent tools)
        self.event["authenticated"] = "false"
        self.event["username"] = "incognito"
        self.event["profile"] = {}

        # BYPASS: when auth is disabled, everyone continues as incognito user
        if AUTH_ENABLED != "true" or not self.dynamodb_helper_auth_sessions:
            self.logger.info("Auth DISABLED (bypass): continuing as incognito user")
            return self.event

        # Validate active auth session (item with TTL of 10 mins)
        auth_item = self.dynamodb_helper_auth_sessions.get_item_by_pk_and_sk(
            partition_key=f"{DDBPrefixes.PK_USER.value}{phone_number}",
            sort_key=DDBPrefixes.SK_AUTH.value,
        )
        if auth_item:
            username = auth_item.get("username", {}).get("S", "unknown")
            self.logger.info(f"User {phone_number} authenticated as {username}")
            self.event["authenticated"] = "true"
            self.event["username"] = username
            # Load the profile metadata (hyperpersonalization) ONLY when
            # the user is AUTHENTICATED (privacy: incognito stays incognito)
            self.load_user_profile(phone_number)
            return self.event

        # NOT authenticated: ask ONCE (per TTL window) to login OR continue incognito
        self.logger.warning(f"User {phone_number} NOT authenticated")
        prompted_item = self.dynamodb_helper_auth_sessions.get_item_by_pk_and_sk(
            partition_key=f"{DDBPrefixes.PK_USER.value}{phone_number}",
            sort_key=DDBPrefixes.SK_AUTH_PROMPTED.value,
        )
        if not prompted_item:
            self.logger.info("Sending auth prompt message (login OR incognito)")
            self.dynamodb_helper_auth_sessions.put_item(
                {
                    "PK": f"{DDBPrefixes.PK_USER.value}{phone_number}",
                    "SK": DDBPrefixes.SK_AUTH_PROMPTED.value,
                    "ttl": int(time.time()) + AUTH_SESSION_TTL_SECONDS,
                }
            )
            self.event["message_type"] = StateMachineMessageTypes.AUTH_PROMPT.value
            self.event["response_message"] = (
                f"👋 Gracias por comunicarte con {BOT_NAME}.\n\n"
                f"🔐 Para acceder a todas las funciones (saldo, tarjetas, etc.), "
                f"autentícate en el portal web:\n{AUTH_PORTAL_URL}\n\n"
                f"🕵️ O simplemente vuelve a enviar tu pregunta para continuar como "
                f"usuario incógnito (funciones limitadas)."
            )

        # NO profile loading for unauthenticated users: until the auth process
        # completes, the user stays FULLY incognito (no name, no personalization)
        return self.event
