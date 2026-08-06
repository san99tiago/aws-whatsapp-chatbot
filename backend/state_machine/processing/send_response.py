################################################################################
# "Send Response" step: sends the generated response message back to the user
# via the META (WhatsApp) Graph API.
################################################################################

# Own imports
from state_machine.base_step_function import BaseStepFunction
from state_machine.integrations.meta.api_requests import MetaAPI
from common.logger import custom_logger


logger = custom_logger()


def build_identity_footer(authenticated: str, profile: dict) -> str:
    """
    Build the one-line identity footer appended to ALL outgoing messages,
    showing the auth status and the user identity. IMPORTANT: until the auth
    process completes, the identity is ALWAYS shown as Incognito (no name).
    """
    is_authenticated = str(authenticated).lower() == "true"
    if not is_authenticated:
        return "\n\n🔐 Autenticado: No | 👤 Incógnito 🕵️"

    profile = profile or {}
    full_name = profile.get("full_name", "")
    nickname = profile.get("nickname", "")
    if full_name and nickname:
        display_name = f"{full_name} ({nickname})"
    elif full_name:
        display_name = full_name
    else:
        display_name = "Autenticado"
    return f"\n\n🔐 Autenticado: Sí ✅ | 👤 {display_name}"


class SendResponse(BaseStepFunction):
    """
    This class contains methods that will "send the response message" for the
    State Machine (final step of the processing workflow).
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def send_response(self):
        """
        Method to send the response message to the user via WhatsApp.
        """

        self.logger.info("Starting send_response for the chatbot")

        # Load response details from the event
        text_message = self.event.get("response_message", "DEFAULT_RESPONSE_MESSAGE")

        # Append the one-line identity footer to ALL outgoing messages
        text_message += build_identity_footer(
            authenticated=self.event.get("authenticated", "false"),
            profile=self.event.get("profile", {}),
        )
        new_image = self.event.get("input", {}).get("dynamodb", {}).get("NewImage", {})
        phone_number = new_image.get("from_number", {}).get("S")
        original_message_id = new_image.get("whatsapp_id", {}).get("S")

        # Initialize the Meta API and send the message (threaded reply)
        meta_api = MetaAPI(logger=self.logger)
        response = meta_api.post_message(
            text_message=text_message,
            to_phone_number=phone_number,
            original_message_id=original_message_id,
        )

        self.logger.debug(
            response,
            message_details="POST WhatsApp Message Meta API Response",
        )

        if "error" in response:
            self.logger.error(
                response,
                message_details="Error in POST WhatsApp Message Meta API Response",
            )
            raise Exception("Error in POST WhatsApp Message Meta API Response")

        self.event["send_message_response_status_code"] = 200
        return self.event
