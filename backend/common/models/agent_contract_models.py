################################################################################
# API-CONTRACT models for invoking the AgentCore Runtime (Strands DemoAgent).
# --> These models define the structured JSON request/response exchanged
#     between the "Process Message" step and the AgentCore Runtime.
################################################################################

# Built-in imports
from typing import Optional

# External imports
from pydantic import BaseModel, Field


class AgentMetadataModel(BaseModel):
    """
    Metadata passed to the Agent as part of the invocation payload.
    Enables future "auth-based" tools inside the Agent.
    """

    authenticated: str = Field(default="false", description="'true' or 'false'")
    username: str = Field(default="incognito")
    phone_number: Optional[str] = None
    correlation_id: Optional[str] = None
    channel: str = Field(default="whatsapp")
    profile: Optional[dict] = Field(
        default=None,
        description="User profile for hyperpersonalization (name, nickname, etc.)",
    )


class AgentInvocationRequestModel(BaseModel):
    """
    JSON Request contract for AGENTCORE INVOKE AGENT RUNTIME.
    """

    prompt: str
    metadata: AgentMetadataModel = Field(default_factory=AgentMetadataModel)


class AgentInvocationResponseModel(BaseModel):
    """
    JSON Response contract returned by the AgentCore Runtime.
    """

    response: str
    metadata: Optional[dict] = None
