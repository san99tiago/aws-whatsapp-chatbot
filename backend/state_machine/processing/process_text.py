# Built-in imports
from datetime import datetime

# Own imports
from state_machine.base_step_function import BaseStepFunction
from common.enums import WhatsAppMessageTypes
from common.logger import custom_logger


logger = custom_logger()
ALLOWED_MESSAGE_TYPES = WhatsAppMessageTypes.__members__


class ProcessText(BaseStepFunction):
    """
    This class contains methods that serve as the "text processing" for the State Machine.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def process_text(self):
        """
        Method to validate the input message and process the expected text response.
        """

        self.logger.info("Starting process_text for the chatbot")

        # TODO: Add more robust "text processing" logic here (actual response)
        self.response_message = (
            self.event.get("input", {})
            .get("dynamodb", {})
            .get("NewImage", {})
            .get("text", {})
            .get("S", "DEFAULT_RESPONSE")
        )

        # TODO: Update "acnowledged" message to a more complex response
        self.response_message = (
            str(self.response_message) + " acknowledged at " + str(datetime.now())
        )

        self.logger.info(f"Generated response message: {self.response_message}")
        self.logger.info("Validation finished successfully")

        self.event["response_message"] = self.response_message

        return self.event
