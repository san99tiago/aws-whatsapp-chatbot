################################################################################
# Unit tests for the AgentCore API-Contract models (request/response).
################################################################################

# External imports
import pytest
from pydantic import ValidationError

# Own imports
from common.models.agent_contract_models import (
    AgentInvocationRequestModel,
    AgentInvocationResponseModel,
    AgentMetadataModel,
)


class TestAgentContractModels:
    def test_request_defaults_to_incognito(self):
        request = AgentInvocationRequestModel(prompt="Hola")
        assert request.prompt == "Hola"
        assert request.metadata.authenticated == "false"
        assert request.metadata.username == "incognito"
        assert request.metadata.channel == "whatsapp"

    def test_request_with_authenticated_metadata(self):
        request = AgentInvocationRequestModel(
            prompt="Cual es mi saldo?",
            metadata=AgentMetadataModel(
                authenticated="true",
                username="santigrc@amazon.com",
                phone_number="573001112233",
                correlation_id="abc-123",
            ),
        )
        payload = request.model_dump()
        assert payload["metadata"]["authenticated"] == "true"
        assert payload["metadata"]["username"] == "santigrc@amazon.com"
        assert payload["metadata"]["phone_number"] == "573001112233"

    def test_request_requires_prompt(self):
        with pytest.raises(ValidationError):
            AgentInvocationRequestModel()

    def test_response_contract_parsing(self):
        response = AgentInvocationResponseModel(
            **{
                "response": "Tu saldo es $1.500.000 COP",
                "metadata": {"authenticated": "true", "model_id": "test-model"},
            }
        )
        assert "1.500.000" in response.response
        assert response.metadata["model_id"] == "test-model"

    def test_response_requires_response_field(self):
        with pytest.raises(ValidationError):
            AgentInvocationResponseModel(metadata={})
