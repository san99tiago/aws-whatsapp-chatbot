# Built-in imports
import os
import boto3

# Own imports
from common.logger import custom_logger


ENVIRONMENT = os.environ.get("ENVIRONMENT")

logger = custom_logger()

# Create a bedrock runtime client
bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime")
ssm_client = boto3.client("ssm")


def get_ssm_parameter(parameter_name):
    """
    Fetches the parameter value from SSM Parameter Store.
    """
    response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
    return response["Parameter"]["Value"]


def call_bedrock_agent(input_text: str) -> str:
    # TODO: Update to use PowerTools SSM Params for optimization
    AGENT_ALIAS_ID = get_ssm_parameter(
        f"/{ENVIRONMENT}/aws-wpp/bedrock-agent-alias-id-full-string"
    )
    AGENT_ALIAS_ID = AGENT_ALIAS_ID.split("|")[-1]
    AGENT_ID = get_ssm_parameter(f"/{ENVIRONMENT}/aws-wpp/bedrock-agent-id")

    response = bedrock_agent_runtime_client.invoke_agent(
        agentAliasId=AGENT_ALIAS_ID,
        agentId=AGENT_ID,
        enableTrace=False,
        inputText=input_text,
        sessionId="TempSessionBedrock",
    )
    logger.info(response)

    stream = response.get("completion")
    text_response = ""
    if stream:
        for event in stream:
            chunk = event.get("chunk")
            logger.info("-----")
            text_response += chunk.get("bytes").decode()
    logger.info(text_response)

    # TODO: Add better error handling and validations/checks

    return text_response
