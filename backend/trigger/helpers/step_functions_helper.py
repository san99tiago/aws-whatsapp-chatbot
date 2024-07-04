# Built-in imports
import time
import os
import json
import boto3

# External imports
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import (
    DynamoDBRecord,
)

# Own imports
from common.logger import custom_logger

LOGGER = custom_logger()

step_function_client = boto3.client("stepfunctions")


def trigger_sm(record: DynamoDBRecord, logger: Logger = None) -> str:
    """
    Handler for triggering the Step Function's execution.

    Args:
        record (DynamoDBRecord): Event from from DynamoDB Stream Record.
        logger (Logger, optional): Logger object. Defaults to None.

    Returns:
        None
    """
    try:
        logger = logger or LOGGER
        log_message = {
            "METHOD": "trigger_sm",
        }
        state_machine_arn = os.environ.get("STATE_MACHINE_ARN", "")

        log_message["MESSAGE"] = f"triggering state machine {state_machine_arn}"
        log_message["RECORD"] = record.raw_event

        # Extract the necessary information from the DynamoDB Stream Record for Execution Name
        from_message = record.dynamodb.new_image.get("from_number", "NOT_FOUND")
        correlation_id = record.dynamodb.new_image.get("correlation_id", "NOT_FOUND")
        exec_name = f"{time.strftime('%Y%m%dT%H%M%S')}_{from_message}_{correlation_id}"

        logger.append_keys(correlation_id=correlation_id)
        logger.debug(log_message)

        # Generate state machine input event with the same DynamoDBRecord dict
        state_machine_input = {"input": record.raw_event}

        logger.debug(state_machine_input, message_details="State Machine Input")

        response = step_function_client.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps(state_machine_input),
            name=exec_name,
        )
        return response.get("executionArn")
    except Exception as err:
        log_message["EXCEPTION"] = str(err)
        logger.error(str(log_message))
        raise
