# External imports
import aws_cdk as core
import aws_cdk.assertions as assertions

# Own imports
from cdk.stacks.cdk_chatbot_api_stack import ChatbotAPIStack


app: core.App = core.App()
stack: ChatbotAPIStack = ChatbotAPIStack(
    scope=app,
    construct_id="santi-chatbot-api-test",
    main_resources_name="santi-chatbot",
    app_config={
        "deployment_environment": "test",
        "log_level": "DEBUG",
        "table_name": "aws-whatsapp-poc-test",
        "api_gw_name": "wpp-test",
    },
)
template: assertions.Template = assertions.Template.from_stack(stack)


def test_app_synthesize_ok():
    app.synth()


def test_dynamodb_table_created():
    match = template.find_resources(
        type="AWS::DynamoDB::Table",
    )
    assert len(match) == 1


def test_lambda_function_created():
    match = template.find_resources(
        type="AWS::Lambda::Function",
    )
    assert len(match) == 2


def test_api_gateway_created():
    match = template.find_resources(
        type="AWS::ApiGateway::RestApi",
    )
    assert len(match) == 1
