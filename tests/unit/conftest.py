################################################################################
# Global pytest fixtures and environment setup for the unit tests.
# IMPORTANT: env-vars are set BEFORE any module import (several modules read
# their configuration at import time).
################################################################################

# Built-in imports
import os

# External imports
import pytest

# Environment variables required at import time by the backend modules
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("SECRET_NAME", "test-secret")
os.environ.setdefault("DYNAMODB_TABLE", "test-messages-table")
os.environ.setdefault("TABLE_NAME_AUTH_SESSIONS", "test-auth-sessions-table")
os.environ.setdefault("AUTH_SESSION_TTL_SECONDS", "600")
os.environ.setdefault("META_ENDPOINT", "https://graph.facebook.com/")
os.environ.setdefault("META_API_VERSION", "v26.0")
os.environ.setdefault("BOT_NAME", "SantiBank Assistant")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials so that boto3 never hits real AWS."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
