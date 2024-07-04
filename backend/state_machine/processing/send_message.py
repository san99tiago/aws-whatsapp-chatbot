# Built-in imports
from datetime import datetime

# Own imports
from state_machine.base_step_function import BaseStepFunction
from common.enums import WhatsAppMessageTypes
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

        # TODO: Add more robust "send message" logic here (actual response)

        self.logger.debug(
            {"dummy_response": "dummy"},
            message_details="Meta API Response for WhatsApp",
        )

        self.event["send_message_response_status_code"] = 200

        return self.event
