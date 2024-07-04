################################################################################
# Lambda Function that triggers receives the event and triggers the State Machine
################################################################################

# External imports
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import event_source
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import (
    DynamoDBStreamEvent,
    DynamoDBRecord,
)

# Own imports
from common.logger import custom_logger
from trigger.helpers.step_functions_helper import trigger_sm  # noqa

logger = custom_logger()


def send_message_to_step_function(record: DynamoDBRecord) -> None:
    logger.append_keys(event_id=record.event_id)
    execution_id = trigger_sm(record)
    logger.info(f"State Machine execution_id: {execution_id}")


@logger.inject_lambda_context(log_event=True)
@event_source(data_class=DynamoDBStreamEvent)
def lambda_handler(event: DynamoDBStreamEvent, context: LambdaContext):
    logger.info("Starting message processing from DynamoDB Stream")
    try:
        for record in event.records:
            correlation_id = record.dynamodb.new_image.get("correlation_id")
            logger.append_keys(correlation_id=correlation_id)
            logger.debug(record.raw_event, message_details="DynamoDB Stream Record")
            send_message_to_step_function(record)

        logger.info("Finished message processing")
    except Exception as e:
        logger.exception(
            f"Wrong input event, does not match DynamoDBRecord schema: {e}"
        )
        raise e
