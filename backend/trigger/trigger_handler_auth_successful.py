################################################################################
# Lambda Function triggered by the auth-sessions DynamoDB Stream. When a new
# AUTH session is created (user logged in via the Web Portal), it sends the
# "authenticated successfully" WhatsApp message to the user.
################################################################################

# External imports
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import event_source
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import (
    DynamoDBStreamEvent,
    DynamoDBRecord,
)

# Own imports
from common.enums import DDBPrefixes
from common.logger import custom_logger
from trigger.helpers.whatsapp_helper import trigger_response  # noqa

logger = custom_logger()


def send_message_to_user(record: DynamoDBRecord) -> None:
    logger.append_keys(event_id=record.event_id)
    trigger_response(record)


@logger.inject_lambda_context(log_event=True)
@event_source(data_class=DynamoDBStreamEvent)
def lambda_handler(event: DynamoDBStreamEvent, context: LambdaContext):
    logger.info("Starting auth-successful processing from DynamoDB Stream")
    try:
        for record in event.records:
            # Skip REMOVE events (TTL expirations) and non-AUTH items
            if record.event_name.name == "REMOVE":
                logger.info("Skipping REMOVE event (TTL expiration)")
                continue
            if record.dynamodb.keys.get("SK") != DDBPrefixes.SK_AUTH.value:
                logger.info("Skipping non-AUTH item (e.g. AUTH#PROMPTED marker)")
                continue

            correlation_id = record.dynamodb.new_image.get("correlation_id")
            logger.append_keys(correlation_id=correlation_id)
            logger.debug(record.raw_event, message_details="DynamoDB Stream Record")
            send_message_to_user(record)

        logger.info("Finished auth-successful processing")
    except Exception as e:
        logger.exception(
            f"Wrong input event, does not match DynamoDBRecord schema: {e}"
        )
        raise e
