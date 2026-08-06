################################################################################
# Unit tests for the Auth API FastAPI router (Cognito-backed portal login).
################################################################################

# External imports
import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws


@pytest.fixture
def mock_aws_resources(aws_credentials):
    """Create the mocked auth-sessions DynamoDB table and Cognito user."""
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

        cognito_client = boto3.client("cognito-idp", region_name="us-east-1")
        user_pool = cognito_client.create_user_pool(PoolName="test-pool")
        user_pool_id = user_pool["UserPool"]["Id"]
        client = cognito_client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName="test-client",
            ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        )
        client_id = client["UserPoolClient"]["ClientId"]

        cognito_client.admin_create_user(
            UserPoolId=user_pool_id,
            Username="santigrc@amazon.com",
            UserAttributes=[
                {"Name": "email", "Value": "santigrc@amazon.com"},
                {"Name": "phone_number", "Value": "+573001112233"},
            ],
            MessageAction="SUPPRESS",
        )
        cognito_client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username="santigrc@amazon.com",
            Password="Password123.",
            Permanent=True,
        )
        auth_result = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": "santigrc@amazon.com",
                "PASSWORD": "Password123.",
            },
        )
        access_token = auth_result["AuthenticationResult"]["AccessToken"]
        yield {"access_token": access_token}


@pytest.fixture
def api_client(mock_aws_resources):
    """FastAPI TestClient with the mocked AWS resources in place."""
    # Re-create the module-level boto3 clients INSIDE the moto context
    import importlib
    from auth.api.v1.routers import auth as auth_router_module

    importlib.reload(auth_router_module)
    from auth.api.v1 import main as auth_main

    importlib.reload(auth_main)
    return TestClient(auth_main.app), mock_aws_resources["access_token"]


class TestAuthAPI:
    def test_post_auth_valid_token_creates_session(self, api_client):
        client, access_token = api_client
        response = client.post("/api/v1/auth", json={"access_token": access_token})
        assert response.status_code == 200
        assert response.json()["message"] == "ok"

        # Validate the auth-session item was created with TTL
        dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
        auth_item = dynamodb_client.get_item(
            TableName="test-auth-sessions-table",
            Key={"PK": {"S": "USER#573001112233"}, "SK": {"S": "AUTH"}},
        )["Item"]
        assert auth_item["username"]["S"] == "santigrc@amazon.com"
        assert "ttl" in auth_item

        # Validate the PERMANENT USERNAME<->WHATSAPP mappings (both directions)
        username_mapping = dynamodb_client.get_item(
            TableName="test-auth-sessions-table",
            Key={"PK": {"S": "USERNAME#santigrc"}, "SK": {"S": "MAPPING"}},
        )["Item"]
        assert username_mapping["phone_number"]["S"] == "573001112233"
        assert "ttl" not in username_mapping
        phone_mapping = dynamodb_client.get_item(
            TableName="test-auth-sessions-table",
            Key={"PK": {"S": "USER#573001112233"}, "SK": {"S": "MAPPING"}},
        )["Item"]
        assert phone_mapping["user_email"]["S"] == "santigrc@amazon.com"

    def test_post_auth_invalid_token_returns_401(self, api_client):
        client, _ = api_client
        response = client.post("/api/v1/auth", json={"access_token": "INVALID-TOKEN"})
        assert response.status_code == 401
        assert response.json()["message"] == "error"

    def test_post_auth_missing_body_returns_422(self, api_client):
        client, _ = api_client
        response = client.post("/api/v1/auth", json={})
        assert response.status_code == 422
