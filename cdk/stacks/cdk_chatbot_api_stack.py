# Built-in imports
import os

# External imports
from aws_cdk import (
    Duration,
    aws_dynamodb,
    aws_lambda,
    aws_lambda_event_sources,
    aws_apigateway as aws_apigw,
    CfnOutput,
    RemovalPolicy,
    Stack,
    Tags,
)
from constructs import Construct


class ChatbotAPIStack(Stack):
    """
    Class to create the ChatbotAPI resources, which includes the API Gateway,
    Lambda Functions, DynamoDB Table, Streams and Async Processes Infrastructure.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        main_resources_name: str,
        app_config: dict[str],
        **kwargs,
    ) -> None:
        """
        :param scope (Construct): Parent of this stack, usually an 'App' or a 'Stage', but could be any construct.
        :param construct_id (str): The construct ID of this stack (same as aws-cdk Stack 'construct_id').
        :param main_resources_name (str): The main unique identified of this stack.
        :param app_config (dict[str]): Dictionary with relevant configuration values for the stack.
        """
        super().__init__(scope, construct_id, **kwargs)

        # Input parameters
        self.construct_id = construct_id
        self.main_resources_name = main_resources_name
        self.app_config = app_config
        self.deployment_environment = self.app_config["deployment_environment"]

        # Main methods for the deployment
        # TODO: Add "import_secret" method to import from secrets manager the tokens
        self.create_dynamodb_table()
        self.create_lambda_layers()
        self.create_lambda_functions()
        self.create_rest_api()
        self.configure_rest_api()
        # TODO: Add DynamoDB Streams
        # TODO: Add additional "async" processes (SQS, Lambdas, etc)

        # Generate CloudFormation outputs
        self.generate_cloudformation_outputs()

    def create_dynamodb_table(self):
        """
        Create DynamoDB table for storing the conversations.
        """
        self.dynamodb_table = aws_dynamodb.Table(
            self,
            "DynamoDB-Table",
            table_name=self.app_config["table_name"],
            partition_key=aws_dynamodb.Attribute(
                name="PK", type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="SK", type=aws_dynamodb.AttributeType.STRING
            ),
            stream=aws_dynamodb.StreamViewType.NEW_IMAGE,
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        Tags.of(self.dynamodb_table).add("Name", self.app_config["table_name"])

    def create_lambda_layers(self) -> None:
        """
        Create the Lambda layers that are necessary for the additional runtime
        dependencies of the Lambda Functions.
        """

        # Layer for "LambdaPowerTools" (for logging, traces, observability, etc)
        self.lambda_layer_powertools = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            "Layer-PowerTools",
            layer_version_arn=f"arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:71",
        )

        # Layer for "common" Python requirements (fastapi, mangum, pydantic, ...)
        self.lambda_layer_common = aws_lambda.LayerVersion(
            self,
            "Layer-Common",
            code=aws_lambda.Code.from_asset("lambda-layers/common/modules"),
            compatible_runtimes=[
                aws_lambda.Runtime.PYTHON_3_11,
            ],
            description="Lambda Layer for Python with <common> library",
            removal_policy=RemovalPolicy.DESTROY,
            compatible_architectures=[aws_lambda.Architecture.X86_64],
        )

    def create_lambda_functions(self) -> None:
        """
        Create the Lambda Functions for the solution.
        """
        # Get relative path for folder that contains Lambda function source
        # ! Note--> we must obtain parent dirs to create path (that"s why there is "os.path.dirname()")
        PATH_TO_LAMBDA_FUNCTION_FOLDER = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "backend",
        )

        # Lambda Function for WhatsApp input messages (Meta WebHook)
        self.lambda_whatsapp_webhook: aws_lambda.Function = aws_lambda.Function(
            self,
            "Lambda-WA-Input",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            handler="whatsapp_chatbot/api/v1/main.handler",
            function_name=f"{self.main_resources_name}-wpp-input",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(20),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
                "DYNAMODB_TABLE": self.dynamodb_table.table_name,
            },
            layers=[
                self.lambda_layer_powertools,
                self.lambda_layer_common,
            ],
        )
        self.dynamodb_table.grant_read_write_data(self.lambda_whatsapp_webhook)

        # Lambda Function for receiving the messages from DynamoDB Streams
        # ... and triggering the State Machine for processing the messages
        self.lambda_trigger_message_processing: aws_lambda.Function = (
            aws_lambda.Function(
                self,
                "Lambda-Trigger-Message-Processing",
                runtime=aws_lambda.Runtime.PYTHON_3_11,
                handler="trigger_message_processing/trigger_handler.lambda_handler",
                function_name=f"{self.main_resources_name}-trigger-msg-processing",
                code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
                timeout=Duration.seconds(20),
                memory_size=512,
                environment={
                    "ENVIRONMENT": self.app_config["deployment_environment"],
                    "LOG_LEVEL": self.app_config["log_level"],
                    "STATE_MACHINE_ARN": "TBD",
                },
                layers=[
                    self.lambda_layer_powertools,
                    self.lambda_layer_common,
                ],
            )
        )

        # Stream the DynamoDB Events to the Lambda Function for processing
        self.lambda_trigger_message_processing.add_event_source(
            aws_lambda_event_sources.DynamoEventSource(
                self.dynamodb_table,
                starting_position=aws_lambda.StartingPosition.TRIM_HORIZON,
                batch_size=1,
            )
        )

    def create_rest_api(self):
        """
        Method to create the REST-API Gateway for exposing the chatbot
        functionalities.
        """

        # API Method Options for the REST-API Gateway
        # TODO: Currently public, as validation happens in the Lambda Function for now
        self.api_method_options_public = aws_apigw.MethodOptions(
            api_key_required=False,
            authorization_type=aws_apigw.AuthorizationType.NONE,
        )

        # TODO: Add domain_name with custom DNS
        # TODO: Enable custom models and schema validations
        rest_api_name = self.app_config["api_gw_name"]
        self.api = aws_apigw.LambdaRestApi(
            self,
            "RESTAPI",
            rest_api_name=rest_api_name,
            description=f"REST API Gateway for {self.main_resources_name} in {self.deployment_environment} environment",
            handler=self.lambda_whatsapp_webhook,
            deploy_options=aws_apigw.StageOptions(
                stage_name=self.deployment_environment,
                description=f"REST API for {self.main_resources_name}",
                metrics_enabled=True,
            ),
            default_cors_preflight_options=aws_apigw.CorsOptions(
                allow_origins=aws_apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST"],
                allow_headers=["*"],
            ),
            default_method_options=self.api_method_options_public,
            endpoint_types=[aws_apigw.EndpointType.REGIONAL],
            cloud_watch_role=False,
            proxy=False,  # Proxy disabled to have more control
        )

    def configure_rest_api(self):
        """
        Method to configure the REST-API Gateway with resources and methods.
        """

        # Define REST-API resources
        root_resource_api = self.api.root.add_resource("api")
        root_resource_v1 = root_resource_api.add_resource("v1")

        # Endpoints for automatic Swagger docs (no auth required)
        root_resource_docs = root_resource_v1.add_resource("docs")
        root_resource_docs_proxy = root_resource_docs.add_resource("{path}")

        # Endpoints for the main functionalities
        root_resource_chatbot = root_resource_v1.add_resource("webhook")

        # Define all API-Lambda integrations for the API methods
        api_lambda_integration_chatbot = aws_apigw.LambdaIntegration(
            self.lambda_whatsapp_webhook
        )

        # API-Path: "/api/v1/webhook"
        root_resource_chatbot.add_method("GET", api_lambda_integration_chatbot)
        root_resource_chatbot.add_method("POST", api_lambda_integration_chatbot)

        # API-Path: "/api/v1/docs"
        root_resource_docs.add_method("GET", api_lambda_integration_chatbot)

        # API-Path: "/api/v1/docs/openapi.json
        root_resource_docs_proxy.add_method("GET", api_lambda_integration_chatbot)

    def generate_cloudformation_outputs(self) -> None:
        """
        Method to add the relevant CloudFormation outputs.
        """

        CfnOutput(
            self,
            "DeploymentEnvironment",
            value=self.app_config["deployment_environment"],
            description="Deployment environment",
        )

        CfnOutput(
            self,
            "APIDocs",
            value=f"https://{self.api.rest_api_id}.execute-api.{self.region}.amazonaws.com/{self.deployment_environment}/api/v1/docs",
            description="API endpoint Docs",
        )

        CfnOutput(
            self,
            "APIChatbot",
            value=f"https://{self.api.rest_api_id}.execute-api.{self.region}.amazonaws.com/{self.deployment_environment}/api/v1/webhook",
            description="API endpoint Chatbot",
        )
