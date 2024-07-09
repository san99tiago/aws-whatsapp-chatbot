# Built-in imports
from datetime import datetime

# Own imports
from state_machine.base_step_function import BaseStepFunction
from state_machine.integrations.meta.api_requests import MetaAPI
from common.logger import custom_logger


logger = custom_logger()


class SendMessage(BaseStepFunction):
    """
    This class contains methods that will "send the response message" for the State Machine.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def send_message(self):
        """
        Method to send the response message to the user.
        """

        self.logger.info("Starting send_message for the chatbot")

        # Load response details from the event
        text_message = self.event.get("response_message", "DEFAULT_RESPONSE_MESSAGE")
        phone_number = (
            self.event.get("input", {})
            .get("dynamodb", {})
            .get("NewImage", {})
            .get("from_number", {})
            .get("S")
        )
        original_message_id = (
            self.event.get("input", {})
            .get("dynamodb", {})
            .get("NewImage", {})
            .get("whatsapp_id", {})
            .get("S")
        )

        # Initialize the Meta API
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
