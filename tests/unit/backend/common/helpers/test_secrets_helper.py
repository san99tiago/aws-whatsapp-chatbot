# Built-in imports
import os
import json

# External imports
import boto3
import pytest
from moto import mock_aws
from botocore.exceptions import ClientError

# Own imports
from backend.common.helpers.secrets_helper import SecretsHelper


@pytest.fixture
def aws_credentials():
    """Mocked AWS configuration for moto"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def mock_secret(aws_credentials):
    """Provide mocked client and configurations for secrets tests"""
    with mock_aws():
        secrets_manager_client = boto3.client(
            "secretsmanager", os.environ.get("AWS_DEFAULT_REGION")
        )
        secret_name = "test-secret"
        secret_value = {
            "username": "test-user",
            "password": "test-password",
            "token": "test-token",
        }
        secrets_manager_client.create_secret(
            Name=secret_name, SecretString=json.dumps(secret_value)
        )
        yield secrets_manager_client


@pytest.fixture
def secrets_helper(mock_secret) -> SecretsHelper:
    return SecretsHelper("test-secret")


@pytest.fixture
def secrets_helper_not_existent(mock_secret) -> SecretsHelper:
    return SecretsHelper("test-non-existent-secret")


def test_secret_helper_non_existent_secret(secrets_helper_not_existent):
    with pytest.raises(ClientError):
        secrets_helper_not_existent.get_secret_value("dummy")


def test_get_secret_value_with_key_success(secrets_helper):
    assert secrets_helper.get_secret_value("username") == "test-user"
    assert secrets_helper.get_secret_value("password") == "test-password"
    assert secrets_helper.get_secret_value("token") == "test-token"


def test_get_secret_value_without_key(secrets_helper):
    assert secrets_helper.get_secret_value() == {
        "username": "test-user",
        "password": "test-password",
        "token": "test-token",
    }


def test_get_secret_value_with_key_invalid(secrets_helper):
    with pytest.raises(KeyError):
        secrets_helper.get_secret_value("test-invalid-key")
