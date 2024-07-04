# Local Imports
from state_machine.base_step_function import BaseStepFunction
from common.enums import WhatsAppMessageTypes
from common.logger import custom_logger


logger = custom_logger()
ALLOWED_MESSAGE_TYPES = [member.value for member in WhatsAppMessageTypes]


class ValidateMessage(BaseStepFunction):
    """
    This class contains methods that serve as event validation for the State Machine.
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def validate_input(self):
        """
        Method to validate the input JSON body for the beginning of the State Machine.
        """

        self.logger.info("Starting validate_input JSON body validation")

        # TODO: Add a more complex validation here (Python schema, etc.)

        # Obtain message_type from the DynamoDB Stream event
        # TODO: add abstraction and validation
        self.message_type = (
            self.event.get("input", {})
            .get("dynamodb", {})
            .get("NewImage", {})
            .get("type", {})
            .get("S", "NOT_FOUND_MESSAGE_TYPE")
        )

        if self.message_type not in ALLOWED_MESSAGE_TYPES:
            logger.error(f"Message type {self.message_type} not allowed")
            raise ValueError(
                f"Message type <{self.message_type}> is not allowed. Allowed ones are: {ALLOWED_MESSAGE_TYPES}"
            )

        self.logger.info("Validation finished successfully")

        # Add relevant data fields for traceability in the next State Machine steps
        self.event["correlation_id"] = self.correlation_id
        self.event["message_type"] = self.message_type

        return self.event
