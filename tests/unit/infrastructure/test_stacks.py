################################################################################
# Unit tests for the CDK stacks (synthesize + fine-grained assertions).
# NOTE: requires <make install> to have been executed (lambda-layers and agent
# deployment package assets must exist locally).
################################################################################

# External imports
import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

# Own imports
from stacks.cdk_agentcore_stack import AgentCoreStack
from stacks.cdk_chatbot_api_stack import ChatbotAPIStack
from stacks.cdk_auth_portal_stack import AuthPortalStack


TEST_ENV = {"account": "111111111111", "region": "us-east-1"}

TEST_APP_CONFIG = {
    "main_resources_name": "aws-wpp",
    "deployment_environment": "test",
    "log_level": "DEBUG",
    "bot_name": "SantiBank Assistant",
    "language": "SPANISH",
    "secret_name": "/test/aws-whatsapp-chatbot",
    "meta_endpoint": "https://graph.facebook.com/",
    "meta_api_version": "v26.0",
    "hosted_zone_name": "example.com",
    "hosted_zone_id": "Z00000000000000000000",
    "api_webhook_subdomain": "wpp-api-webhook-test",
    "api_gw_name_webhook": "webhook-api",
    "table_name_messages": "messages",
    "auth_enabled": True,
    "auth_portal_subdomain": "web-portal-auth-test",
    "api_gw_name_auth": "auth-api",
    "table_name_auth_sessions": "auth-sessions",
    "auth_session_ttl_seconds": 600,
    "bedrock_model_id": "us.anthropic.claude-sonnet-5",
    "agentcore_runtime_name": "demo_agent",
    "table_name_bank_clients": "bank-clients",
    "ssm_param_agentcore_runtime_arn": "agentcore-runtime-arn",
}


@pytest.fixture(scope="module")
def agentcore_template():
    app = cdk.App()
    stack = AgentCoreStack(
        app, "agentcore-test-stack", "aws-wpp", TEST_APP_CONFIG, env=TEST_ENV
    )
    return Template.from_stack(stack)


@pytest.fixture(scope="module")
def chatbot_api_template():
    app = cdk.App()
    stack = ChatbotAPIStack(
        app, "chatbot-api-test-stack", "aws-wpp", TEST_APP_CONFIG, env=TEST_ENV
    )
    return Template.from_stack(stack)


@pytest.fixture(scope="module")
def auth_portal_template():
    app = cdk.App()
    stack = AuthPortalStack(
        app, "auth-portal-test-stack", "aws-wpp", TEST_APP_CONFIG, env=TEST_ENV
    )
    return Template.from_stack(stack)


class TestAgentCoreStack:
    def test_agentcore_runtime_created_with_zip_deploy(self, agentcore_template):
        agentcore_template.resource_count_is("AWS::BedrockAgentCore::Runtime", 1)
        agentcore_template.has_resource_properties(
            "AWS::BedrockAgentCore::Runtime",
            {
                "AgentRuntimeName": "demo_agent_test",
                "AgentRuntimeArtifact": {
                    "CodeConfiguration": {
                        "EntryPoint": ["main.py"],
                        "Runtime": "PYTHON_3_13",
                    }
                },
                "EnvironmentVariables": Match.object_like(
                    {"BEDROCK_MODEL_ID": "us.anthropic.claude-sonnet-5"}
                ),
            },
        )

    def test_bank_clients_table_created(self, agentcore_template):
        agentcore_template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {"TableName": "aws-wpp-bank-clients-test"},
        )

    def test_seeder_custom_resource_created(self, agentcore_template):
        agentcore_template.resource_count_is("AWS::CloudFormation::CustomResource", 1)

    def test_ssm_parameter_with_runtime_arn(self, agentcore_template):
        agentcore_template.has_resource_properties(
            "AWS::SSM::Parameter",
            {"Name": "/test/aws-wpp/agentcore-runtime-arn"},
        )


class TestChatbotAPIStack:
    def test_messages_table_without_ttl(self, chatbot_api_template):
        chatbot_api_template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {"TableName": "aws-wpp-messages-test"},
        )
        # Messages are kept FOREVER: no TTL specification allowed
        tables = chatbot_api_template.find_resources("AWS::DynamoDB::Table")
        for table in tables.values():
            assert "TimeToLiveSpecification" not in table["Properties"]

    def test_lambda_functions_created(self, chatbot_api_template):
        functions = chatbot_api_template.find_resources("AWS::Lambda::Function")
        function_names = [
            f["Properties"].get("FunctionName", "") for f in functions.values()
        ]
        assert "aws-wpp-webhook-test" in function_names
        assert "aws-wpp-trigger-state-machine-test" in function_names
        assert "aws-wpp-state-machine-test" in function_names

    def test_api_gateway_with_custom_domain(self, chatbot_api_template):
        chatbot_api_template.resource_count_is("AWS::ApiGateway::RestApi", 1)
        chatbot_api_template.has_resource_properties(
            "AWS::ApiGateway::DomainName",
            {"DomainName": "wpp-api-webhook-test.example.com"},
        )

    def test_state_machine_express_with_logging(self, chatbot_api_template):
        chatbot_api_template.has_resource_properties(
            "AWS::StepFunctions::StateMachine",
            {
                "StateMachineName": "aws-wpp-process-message-test",
                "StateMachineType": "EXPRESS",
                "LoggingConfiguration": Match.object_like({"Level": "ALL"}),
            },
        )

    def test_state_machine_has_renamed_states(self, chatbot_api_template):
        state_machines = chatbot_api_template.find_resources(
            "AWS::StepFunctions::StateMachine"
        )
        definition = str(state_machines)
        assert "Process Message" in definition
        assert "Send Response" in definition
        assert "Check Auth" in definition


class TestAuthPortalStack:
    def test_cognito_user_pool_created(self, auth_portal_template):
        auth_portal_template.resource_count_is("AWS::Cognito::UserPool", 1)

    def test_auth_sessions_table_with_ttl(self, auth_portal_template):
        auth_portal_template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "TableName": "aws-wpp-auth-sessions-test",
                "TimeToLiveSpecification": {
                    "AttributeName": "ttl",
                    "Enabled": True,
                },
            },
        )

    def test_cloudfront_distribution_created(self, auth_portal_template):
        auth_portal_template.resource_count_is("AWS::CloudFront::Distribution", 1)

    def test_s3_bucket_is_private(self, auth_portal_template):
        auth_portal_template.has_resource_properties(
            "AWS::S3::Bucket",
            {
                "PublicAccessBlockConfiguration": Match.object_like(
                    {"BlockPublicAcls": True, "BlockPublicPolicy": True}
                )
            },
        )
