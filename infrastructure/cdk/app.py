#!/usr/bin/env python3

# Built-in imports
import os

# External imports
import aws_cdk as cdk

# Own imports
from helpers.add_tags import add_tags_to_app
from stacks.cdk_agentcore_stack import AgentCoreStack
from stacks.cdk_chatbot_api_stack import ChatbotAPIStack
from stacks.cdk_auth_portal_stack import AuthPortalStack


print("--> Deployment AWS configuration (safety first):")
print("CDK_DEFAULT_ACCOUNT", os.environ.get("CDK_DEFAULT_ACCOUNT"))
print("CDK_DEFAULT_REGION", os.environ.get("CDK_DEFAULT_REGION"))


app: cdk.App = cdk.App()

# Configurations for the deployment (obtained from env vars and CDK context)
DEPLOYMENT_ENVIRONMENT = os.environ.get("DEPLOYMENT_ENVIRONMENT", "prod")
APP_CONFIG = app.node.try_get_context("app_config")[DEPLOYMENT_ENVIRONMENT]
MAIN_RESOURCES_NAME = APP_CONFIG["main_resources_name"]
DEPLOYMENT_ACCOUNT_REGION = {
    "account": os.environ.get("CDK_DEFAULT_ACCOUNT"),
    "region": os.environ.get("CDK_DEFAULT_REGION"),
}

# STACK 1: AgentCore Runtime with Strands Agent (Bank Demo Agent)
agentcore_stack = AgentCoreStack(
    app,
    f"agentcore-{MAIN_RESOURCES_NAME}-{DEPLOYMENT_ENVIRONMENT}-stack",
    MAIN_RESOURCES_NAME,
    APP_CONFIG,
    env=DEPLOYMENT_ACCOUNT_REGION,
    description=f"Stack for {MAIN_RESOURCES_NAME} AgentCore Runtime (Strands Agent) in {DEPLOYMENT_ENVIRONMENT} environment",
)

# STACK 2: Chatbot API (WhatsApp Webhook, DynamoDB, Step Functions)
chatbot_api_stack = ChatbotAPIStack(
    app,
    f"{MAIN_RESOURCES_NAME}-chatbot-api-{DEPLOYMENT_ENVIRONMENT}",
    MAIN_RESOURCES_NAME,
    APP_CONFIG,
    env=DEPLOYMENT_ACCOUNT_REGION,
    description=f"Stack for {MAIN_RESOURCES_NAME} chatbot-api infrastructure in {DEPLOYMENT_ENVIRONMENT} environment",
)

# STACK 3 (OPTIONAL): Auth Portal (Cognito, CloudFront+S3, Auth API, Auth Sessions)
# --> Only deployed when <auth_enabled> is true in the cdk.json app_config
if str(APP_CONFIG.get("auth_enabled", False)).lower() == "true":
    auth_portal_stack = AuthPortalStack(
        app,
        f"{MAIN_RESOURCES_NAME}-auth-portal-{DEPLOYMENT_ENVIRONMENT}",
        MAIN_RESOURCES_NAME,
        APP_CONFIG,
        env=DEPLOYMENT_ACCOUNT_REGION,
        description=f"Stack for {MAIN_RESOURCES_NAME} auth-portal (Cognito+CloudFront+S3) in {DEPLOYMENT_ENVIRONMENT} environment",
    )

add_tags_to_app(
    app,
    MAIN_RESOURCES_NAME,
    DEPLOYMENT_ENVIRONMENT,
)

app.synth()
