################################################################################
# Unit tests for the "Check Auth" State Machine step (auth session validation
# with TTL of 10 mins, and full bypass when AUTH_ENABLED=false).
################################################################################

# Built-in imports
import time

# External imports
import boto3
import pytest
from moto import mock_aws


def _build_stream_event(phone_number: str = "573001112233") -> dict:
    """Helper to build a State Machine event with the DynamoDB Stream shape."""
    return {
        "input": {
            "dynamodb": {
                "NewImage": {
                    "PK": {"S": f"NUMBER#{phone_number}"},
                    "SK": {"S": "MESSAGE#2026-08-04T00:00:00"},
                    "from_number": {"S": phone_number},
                    "type": {"S": "text"},
                    "text": {"S": "Hola"},
                    "correlation_id": {"S": "test-correlation-id"},
                }
            }
        },
        "message_type": "text",
        "correlation_id": "test-correlation-id",
    }


@pytest.fixture
def mock_auth_sessions_table(aws_credentials):
    """Create the mocked auth-sessions DynamoDB table."""
    with mock_aws():
        dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb_client.create_table(
            TableName="test-auth-sessions-table",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield dynamodb_client


class TestCheckAuthBypass:
    def test_auth_disabled_bypasses_to_incognito(self, monkeypatch):
        from state_machine.utils import check_auth as check_auth_module

        monkeypatch.setattr(check_auth_module, "AUTH_ENABLED", "false")
        step = check_auth_module.CheckAuth(_build_stream_event())
        step.dynamodb_helper_auth_sessions = None
        result = step.check_auth()

        assert result["authenticated"] == "false"
        assert result["username"] == "incognito"
        assert result["message_type"] == "text"  # NOT overridden (no auth prompt)


class TestCheckAuthEnabled:
    def test_authenticated_user_detected(self, mock_auth_sessions_table, monkeypatch):
        from common.helpers.dynamodb_helper import DynamoDBHelper
        from state_machine.utils import check_auth as check_auth_module

        # Active AUTH session in DynamoDB
        mock_auth_sessions_table.put_item(
            TableName="test-auth-sessions-table",
            Item={
                "PK": {"S": "USER#573001112233"},
                "SK": {"S": "AUTH"},
                "username": {"S": "santigrc@amazon.com"},
                "ttl": {"N": str(int(time.time()) + 600)},
            },
        )

        monkeypatch.setattr(check_auth_module, "AUTH_ENABLED", "true")
        step = check_auth_module.CheckAuth(_build_stream_event())
        step.dynamodb_helper_auth_sessions = DynamoDBHelper(
            table_name="test-auth-sessions-table"
        )
        result = step.check_auth()

        assert result["authenticated"] == "true"
        assert result["username"] == "santigrc@amazon.com"
        assert result["message_type"] == "text"

    def test_unauthenticated_user_gets_auth_prompt_once(
        self, mock_auth_sessions_table, monkeypatch
    ):
        from common.helpers.dynamodb_helper import DynamoDBHelper
        from state_machine.utils import check_auth as check_auth_module

        monkeypatch.setattr(check_auth_module, "AUTH_ENABLED", "true")
        monkeypatch.setattr(
            check_auth_module, "AUTH_PORTAL_URL", "https://portal.example.com"
        )

        # FIRST message: auth prompt is sent (message_type overridden)
        step = check_auth_module.CheckAuth(_build_stream_event())
        step.dynamodb_helper_auth_sessions = DynamoDBHelper(
            table_name="test-auth-sessions-table"
        )
        result = step.check_auth()
        assert result["authenticated"] == "false"
        assert result["message_type"] == "auth_prompt"
        assert "https://portal.example.com" in result["response_message"]

        # SECOND message: continues as incognito (marker already exists)
        step2 = check_auth_module.CheckAuth(_build_stream_event())
        step2.dynamodb_helper_auth_sessions = DynamoDBHelper(
            table_name="test-auth-sessions-table"
        )
        result2 = step2.check_auth()
        assert result2["authenticated"] == "false"
        assert result2["username"] == "incognito"
        assert result2["message_type"] == "text"  # NOT overridden anymore
