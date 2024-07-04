# Built-in imports
import uuid
from typing import Optional

# External imports
from aws_lambda_powertools import Logger

# Own imports
from common.logger import custom_logger


class BaseStepFunction:
    """
    Class that contains the base helpers/attributes for all steps in the state machine.
    """

    message_type: str = ""
    correlation_id: str = ""
    version_id: str = ""
    previous_step_key: str = ""

    def __init__(
        self,
        event,
        logger: Optional[Logger] = None,
    ):
        self.event = event
        self.logger = logger or custom_logger()

        self.logger.info(self.__class__.__name__ + "class event")
        self.logger.info(event, message_details="Received Event")

        self.message_type: str = self.event.get("message_type")

        # Load correlation ID from event, from DynamoDB Stream or generate a new one
        correlation_id_from_event = self.event.get("correlation_id")
        correlation_id_from_dynamo = (
            self.event.get("input", {})
            .get("dynamodb", {})
            .get("NewImage", {})
            .get("correlation_id", {})
            .get("S")
        )
        self.correlation_id: str = (
            correlation_id_from_event or correlation_id_from_dynamo or str(uuid.uuid4())
        )

        # TODO: Also include the phone number in the appended keys

        self.logger.append_keys(
            correlation_id=self.correlation_id,
            message_type=self.message_type,
        )
