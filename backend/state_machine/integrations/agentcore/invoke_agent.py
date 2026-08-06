################################################################################
# Helper to INVOKE AGENT RUNTIME (Bedrock AgentCore) with the JSON API-Contract.
# --> The AgentCore Runtime ARN is stored in an AWS Systems Manager Parameter,
#     whose NAME is passed to the Lambda as an ENV-VAR, and the VALUE is fetched
#     dynamically (and cached) at runtime.
# Docs: https://docs.aws.amazon.com/boto3/latest/reference/services/bedrock-agentcore/client/invoke_agent_runtime.html
################################################################################

# Built-in imports
import json
import os
import uuid

# External imports
import boto3
from aws_lambda_powertools.utilities import parameters

# Own imports
from common.logger import custom_logger
from common.models.agent_contract_models import (
    AgentInvocationRequestModel,
    AgentInvocationResponseModel,
)


logger = custom_logger()

# ENV-VAR with the NAME of the SSM Parameter that stores the AgentCore Runtime ARN
AGENTCORE_RUNTIME_ARN_PARAM = os.environ.get("AGENTCORE_RUNTIME_ARN_PARAM")

# AgentCore data-plane client (bedrock-agentcore)
agentcore_client = boto3.client("bedrock-agentcore")


def get_agentcore_runtime_arn() -> str:
    """
    Dynamically fetch the AgentCore Runtime ARN from SSM Parameter Store.
    Uses PowerTools parameters provider (cached for 60 seconds by default).
    """
    if not AGENTCORE_RUNTIME_ARN_PARAM:
        raise ValueError("AGENTCORE_RUNTIME_ARN_PARAM env-var is not configured")
    runtime_arn = parameters.get_parameter(AGENTCORE_RUNTIME_ARN_PARAM, max_age=60)
    logger.debug(f"Resolved AgentCore Runtime ARN: {runtime_arn}")
    return runtime_arn


def build_runtime_session_id(phone_number: str) -> str:
    """
    Build a runtime session ID for AgentCore (33+ chars required).
    Keeps per-user session affinity based on the WhatsApp phone number.
    """
    session_id = f"whatsapp-session-{phone_number}-{uuid.uuid4().hex[:8]}"
    return session_id.ljust(33, "0")


def invoke_agentcore_runtime(
    request: AgentInvocationRequestModel,
) -> AgentInvocationResponseModel:
    """
    Invoke the AgentCore Runtime with the structured JSON API-Contract.

    :param request (AgentInvocationRequestModel): structured request contract.
    :return (AgentInvocationResponseModel): structured response contract.
    """
    runtime_arn = get_agentcore_runtime_arn()
    payload = request.model_dump()
    logger.info(f"Invoking AgentCore Runtime: {runtime_arn}")
    logger.debug(payload, message_details="AgentCore invocation payload")

    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        qualifier="DEFAULT",
        runtimeSessionId=build_runtime_session_id(
            request.metadata.phone_number or "unknown"
        ),
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(payload).encode("utf-8"),
    )

    # Read the (streaming) response body and parse the JSON contract
    raw_response = response["response"].read().decode("utf-8")
    logger.debug(f"AgentCore raw response: {raw_response}")

    response_json = json.loads(raw_response)
    agent_response = AgentInvocationResponseModel(**response_json)
    logger.info("AgentCore Runtime invocation finished successfully")
    return agent_response
