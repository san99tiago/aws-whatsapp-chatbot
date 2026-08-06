################################################################################
# Unit tests for the WhatsApp Webhook FastAPI router (GET verification + POST).
################################################################################

# Built-in imports
import json

# External imports
import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws


@pytest.fixture
def mock_aws_resources(aws_credentials):
    """Create the mocked AWS Secret and DynamoDB table used by the router."""
    with mock_aws():
        secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
        secrets_client.create_secret(
            Name="test-secret",
            SecretString=json.dumps(
                {
                    "AWS_API_KEY_TOKEN": "test-meta-verify-token",
                    "META_TOKEN": "test-meta-token",
                    "META_FROM_PHONE_NUMBER_ID": "1234567890",
                }
            ),
        )
        dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb_client.create_table(
            TableName="test-messages-table",
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
        yield


@pytest.fixture
def api_client(mock_aws_resources):
    """FastAPI TestClient with the mocked AWS resources in place."""
    from whatsapp_webhook.api.v1.main import app

    return TestClient(app)


def _build_meta_text_message_event(text: str = "Hola SantiBank") -> dict:
    """Helper to build a realistic META webhook POST event (text message)."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1111111111",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "573001112233",
                                "phone_number_id": "1234567890",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Santi"},
                                    "wa_id": "573001112233",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "573001112233",
                                    "id": "wamid.TEST_MESSAGE_ID",
                                    "timestamp": "1722800000",
                                    "text": {"body": text},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


class TestWebhookVerificationGET:
    def test_get_webhook_valid_token_returns_challenge(self, api_client):
        response = api_client.get(
            "/api/v1/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "challenge-123",
                "hub.verify_token": "test-meta-verify-token",
            },
        )
        assert response.status_code == 200
        assert response.text == "challenge-123"

    def test_get_webhook_invalid_token_returns_403(self, api_client):
        response = api_client.get(
            "/api/v1/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "challenge-123",
                "hub.verify_token": "WRONG-TOKEN",
            },
        )
        assert response.status_code == 403
        assert "error" in response.json()

    def test_get_webhook_missing_params_returns_422(self, api_client):
        response = api_client.get("/api/v1/webhook")
        assert response.status_code == 422


class TestWebhookCallbackPOST:
    def test_post_webhook_text_message_saved(self, api_client):
        response = api_client.post(
            "/api/v1/webhook", json=_build_meta_text_message_event()
        )
        assert response.status_code == 200
        assert response.json()["message"] == "ok"

        # Validate the message was stored in DynamoDB (kept forever, no TTL)
        dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
        result = dynamodb_client.scan(TableName="test-messages-table")
        assert result["Count"] == 1
        item = result["Items"][0]
        assert item["PK"]["S"] == "NUMBER#573001112233"
        assert item["text"]["S"] == "Hola SantiBank"
        assert "ttl" not in item

    def test_post_webhook_audio_message_saved_with_audio_id(self, api_client):
        audio_event = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "1111111111",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "messages": [
                                    {
                                        "from": "573001112233",
                                        "id": "wamid.AUDIO_TEST",
                                        "timestamp": "1722800000",
                                        "type": "audio",
                                        "audio": {
                                            "id": "MEDIA-ID-AUDIO-999",
                                            "mime_type": "audio/ogg; codecs=opus",
                                            "voice": True,
                                        },
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }
        response = api_client.post("/api/v1/webhook", json=audio_event)
        assert response.status_code == 200
        assert response.json()["message"] == "ok"

        # Validate the audio message was stored with its META media ID
        dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
        result = dynamodb_client.scan(TableName="test-messages-table")
        audio_items = [
            i for i in result["Items"] if i.get("type", {}).get("S") == "audio"
        ]
        assert len(audio_items) == 1
        assert audio_items[0]["audio_id"]["S"] == "MEDIA-ID-AUDIO-999"

    def test_post_webhook_status_event_is_skipped(self, api_client):
        status_event = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "1111111111",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "statuses": [{"id": "wamid.X", "status": "delivered"}],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }
        response = api_client.post("/api/v1/webhook", json=status_event)
        assert response.status_code == 200
        assert "skipped" in response.json()["details"]
