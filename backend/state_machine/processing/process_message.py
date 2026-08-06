################################################################################
# "Process Message" step: invokes the AgentCore Runtime (Strands DemoAgent)
# with the structured JSON API-Contract (prompt + auth metadata).
################################################################################

# Built-in imports
import os

# Own imports
from state_machine.base_step_function import BaseStepFunction
from state_machine.integrations.agentcore.invoke_agent import (
    invoke_agentcore_runtime,
)
from common.logger import custom_logger
from common.models.agent_contract_models import (
    AgentInvocationRequestModel,
    AgentMetadataModel,
)


logger = custom_logger()

BOT_NAME = os.environ.get("BOT_NAME", "SantiBank Assistant")


class ProcessMessage(BaseStepFunction):
    """
    This class contains methods that serve as the "message processing" for the
    State Machine (Agent invocation via AgentCore Runtime).
    """

    def __init__(self, event):
        super().__init__(event, logger=logger)

    def process_message(self):
        """
        Method to process the input message with the AgentCore Runtime Agent
        and generate the expected response message.
        """

        self.logger.info("Starting process_message for the chatbot")

        new_image = self.event.get("input", {}).get("dynamodb", {}).get("NewImage", {})
        phone_number = new_image.get("from_number", {}).get("S", "UNKNOWN")

        # The prompt comes from the TEXT message, OR from the TRANSCRIBED audio
        # (re-utilizing the output of the Fetch Audio -> Transcribe Audio steps)
        transcribed_text = self.event.get("transcribed_text", "")
        text = transcribed_text or new_image.get("text", {}).get("S", "")
        if transcribed_text:
            self.logger.info(
                f"Re-utilizing the TRANSCRIBED audio text as prompt: {text}"
            )

        # Build the structured JSON API-Contract for the Agent invocation
        # (profile metadata is ALWAYS loaded by CheckAuth for hyperpersonalization)
        agent_request = AgentInvocationRequestModel(
            prompt=text,
            metadata=AgentMetadataModel(
                authenticated=self.event.get("authenticated", "false"),
                username=self.event.get("username", "incognito"),
                phone_number=phone_number,
                correlation_id=self.correlation_id,
                channel="whatsapp",
                profile=self.event.get("profile") or None,
            ),
        )

        try:
            agent_response = invoke_agentcore_runtime(agent_request)
            self.response_message = agent_response.response
        except Exception as e:
            self.logger.exception(f"AgentCore Runtime invocation failed: {e}")
            raise e

        if not self.response_message:
            self.response_message = (
                f"{BOT_NAME} tuvo un pequeño problema. "
                "Por favor repite el mensaje nuevamente."
            )

        self.logger.info(f"Generated response message: {self.response_message}")

        self.event["response_message"] = self.response_message
        return self.event
