# Built-in imports
import os

# External imports
from aws_cdk import (
    Duration,
    aws_bedrock,
    aws_dynamodb,
    aws_iam,
    aws_lambda,
    aws_lambda_event_sources,
    aws_logs,
    aws_ssm,
    aws_secretsmanager,
    aws_stepfunctions as aws_sfn,
    aws_stepfunctions_tasks as aws_sfn_tasks,
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
        self.import_secrets()
        self.create_dynamodb_table()
        self.create_lambda_layers()
        self.create_lambda_functions()
        self.create_dynamodb_streams()
        self.create_rest_api()
        self.configure_rest_api()
        self.create_state_machine_tasks()
        self.create_state_machine_definition()
        self.create_state_machine()
        self.create_bedrock_components()

        # Generate CloudFormation outputs
        self.generate_cloudformation_outputs()

    def import_secrets(self) -> None:
        """
        Method to import the AWS Secrets for the Lambda Functions.
        """
        self.secret_chatbot = aws_secretsmanager.Secret.from_secret_name_v2(
            self,
            "Secret-Chatbot",
            secret_name=self.app_config["secret_name"],
        )

    def create_dynamodb_table(self):
        """
        Create DynamoDB table for storing the conversations.
        """
        self.dynamodb_table = aws_dynamodb.Table(
            self,
            "DynamoDB-Table-Chatbot",
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
        self.lambda_whatsapp_webhook = aws_lambda.Function(
            self,
            "Lambda-WhatsApp-Webhook",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            handler="whatsapp_webhook/api/v1/main.handler",
            function_name=f"{self.main_resources_name}-input",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(20),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
                "DYNAMODB_TABLE": self.dynamodb_table.table_name,
                "SECRET_NAME": self.app_config["secret_name"],
            },
            layers=[
                self.lambda_layer_powertools,
                self.lambda_layer_common,
            ],
        )
        self.dynamodb_table.grant_read_write_data(self.lambda_whatsapp_webhook)
        self.secret_chatbot.grant_read(self.lambda_whatsapp_webhook)

        # Lambda Function for receiving the messages from DynamoDB Streams
        # ... and triggering the State Machine for processing the messages
        self.lambda_trigger_state_machine = aws_lambda.Function(
            self,
            "Lambda-Trigger-Message-Processing",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            handler="trigger/trigger_handler.lambda_handler",
            function_name=f"{self.main_resources_name}-trigger-state-machine",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(20),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
            },
            layers=[
                self.lambda_layer_powertools,
                self.lambda_layer_common,
            ],
        )

        # Lambda Function that will run the State Machine steps for processing the messages
        # TODO: In the future, can be migrated to MULTIPLE Lambda Functions for each step...
        self.lambda_state_machine_process_message = aws_lambda.Function(
            self,
            "Lambda-SM-Process-Message",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            handler="state_machine/state_machine_handler.lambda_handler",
            function_name=f"{self.main_resources_name}-state-machine-lambda",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
                "SECRET_NAME": self.app_config["secret_name"],
                "META_ENDPOINT": self.app_config["meta_endpoint"],
            },
            layers=[
                self.lambda_layer_powertools,
                self.lambda_layer_common,
            ],
        )
        self.secret_chatbot.grant_read(self.lambda_state_machine_process_message)

        # Lambda Function for the Bedrock Agent Group (fetch recipes)
        bedrock_agent_lambda_role = aws_iam.Role(
            self,
            "BedrockAgentLambdaRole",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for Bedrock Agent Lambda",
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole",
                ),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess",
                ),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonDynamoDBFullAccess",
                ),
            ],
        )

        # Lambda for the Action Group (used for Bedrock Agents)
        self.lambda_fetch_calendar_events = aws_lambda.Function(
            self,
            "Lambda-AG-FetchCalendarEvents",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            handler="bedrock_agent/lambda_function.lambda_handler",
            function_name=f"{self.main_resources_name}-bedrock-action-group-calendar-events",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
                "TABLE_NAME": self.app_config["calendar_events_table_name"],
            },
            role=bedrock_agent_lambda_role,
        )

    def create_dynamodb_streams(self) -> None:
        """
        Method to create the DynamoDB Streams for the Lambda Function that will
        process the incoming messages and trigger the State Machine.
        """

        # Stream the DynamoDB Events to the Lambda Function for processing
        self.lambda_trigger_state_machine.add_event_source(
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

        # Method to remove the "CloudFormation Output" to avoid exposing the endpoint
        self.api.node.try_remove_child("Endpoint")

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

    def create_state_machine_tasks(self) -> None:
        """ "
        Method to create the tasks for the Step Function State Machine.
        """

        # TODO: create abstraction to reuse the definition of tasks

        self.task_validate_message = aws_sfn_tasks.LambdaInvoke(
            self,
            "Task-ValidateMessage",
            state_name="Validate Message",
            lambda_function=self.lambda_state_machine_process_message,
            payload=aws_sfn.TaskInput.from_object(
                {
                    "event.$": "$",
                    "params": {
                        "class_name": "ValidateMessage",
                        "method_name": "validate_input",
                    },
                }
            ),
            output_path="$.Payload",
        )

        # Pass States to simplify State Machine UI understanding
        self.task_pass_text = aws_sfn.Pass(
            self,
            "Task-Text",
            comment="Indicates that the message type is Text",
            state_name="Text",
        )

        self.task_pass_voice = aws_sfn.Pass(
            self,
            "Task-Voice",
            comment="Indicates that the message type is Voice",
            state_name="Voice",
        )

        self.task_pass_image = aws_sfn.Pass(
            self,
            "Task-Image",
            comment="Indicates that the message type is Image",
            state_name="Image",
        )

        self.task_pass_video = aws_sfn.Pass(
            self,
            "Task-Video",
            comment="Indicates that the message type is Video",
            state_name="Video",
        )

        self.task_process_text = aws_sfn_tasks.LambdaInvoke(
            self,
            "Task-ProcessText",
            state_name="Process Text",
            lambda_function=self.lambda_state_machine_process_message,
            payload=aws_sfn.TaskInput.from_object(
                {
                    "event.$": "$",
                    "params": {
                        "class_name": "ProcessText",
                        "method_name": "process_text",
                    },
                }
            ),
            output_path="$.Payload",
        )

        self.task_send_message = aws_sfn_tasks.LambdaInvoke(
            self,
            "Task-SendMessage",
            state_name="Send Message",
            lambda_function=self.lambda_state_machine_process_message,
            payload=aws_sfn.TaskInput.from_object(
                {
                    "event.$": "$",
                    "params": {
                        "class_name": "SendMessage",
                        "method_name": "send_message",
                    },
                }
            ),
            output_path="$.Payload",
        )

        self.task_not_implemented = aws_sfn.Pass(
            self,
            "Task-NotImplemented",
            comment="Not implemented yet",
        )

        self.task_process_success = aws_sfn_tasks.LambdaInvoke(
            self,
            "Task-Success",
            state_name="Process Success",
            lambda_function=self.lambda_state_machine_process_message,
            payload=aws_sfn.TaskInput.from_object(
                {
                    "event.$": "$",
                    "params": {
                        "class_name": "Success",
                        "method_name": "process_success",
                    },
                }
            ),
            output_path="$.Payload",
        )

        self.task_process_failure = aws_sfn_tasks.LambdaInvoke(
            self,
            "Task-Failure",
            state_name="Process Failure",
            lambda_function=self.lambda_state_machine_process_message,
            payload=aws_sfn.TaskInput.from_object(
                {
                    "event.$": "$",
                    "params": {
                        "class_name": "Failure",
                        "method_name": "process_failure",
                    },
                }
            ),
            output_path="$.Payload",
        )

        self.task_success = aws_sfn.Succeed(
            self,
            id="Succeed",
            comment="Successful execution of State Machine",
        )

        self.task_failure = aws_sfn.Fail(
            self,
            id="Exception Handling Finished",
            comment="State Machine Exception or Failure",
        )

    def create_state_machine_definition(self) -> None:
        """
        Method to create the Step Function State Machine definition.
        """

        # Conditions to simplify Choices in the State Machine
        # TODO: Add enums here for MessageType
        self.choice_text = aws_sfn.Condition.string_equals("$.message_type", "text")
        self.choice_image = aws_sfn.Condition.string_equals("$.message_type", "image")
        self.choice_video = aws_sfn.Condition.string_equals("$.message_type", "video")
        self.choice_voice = aws_sfn.Condition.string_equals("$.message_type", "voice")

        # State Machine event type initial configuration entrypoints
        self.state_machine_definition = self.task_validate_message.next(
            aws_sfn.Choice(self, "Message Type?")
            .when(self.choice_text, self.task_pass_text)
            .when(self.choice_voice, self.task_pass_voice)
            .when(self.choice_image, self.task_pass_image)
            .when(self.choice_video, self.task_pass_video)
        )

        # Pass States entrypoints
        self.task_pass_text.next(
            self.task_process_text.next(self.task_send_message),
        )
        self.task_pass_voice.next(self.task_not_implemented)
        self.task_pass_image.next(self.task_not_implemented)
        self.task_pass_video.next(self.task_not_implemented)

        self.task_not_implemented.next(self.task_send_message)

        self.task_send_message.next(self.task_process_success)

        self.task_process_success.next(self.task_success)

        # TODO: Add failure handling for the State Machine with "process_failure"
        # self.task_process_failure.next(self.task_failure)

    def create_state_machine(self) -> None:
        """
        Method to create the Step Function State Machine for processing the messages.
        """

        log_group_name = f"/aws/vendedlogs/states/{self.main_resources_name}"
        self.state_machine_log_group = aws_logs.LogGroup(
            self,
            "StateMachine-LogGroup",
            log_group_name=log_group_name,
            removal_policy=RemovalPolicy.DESTROY,
        )
        Tags.of(self.state_machine_log_group).add("Name", log_group_name)

        self.state_machine = aws_sfn.StateMachine(
            self,
            "StateMachine-ProcessMessage",
            state_machine_name=f"{self.main_resources_name}-process-message",
            state_machine_type=aws_sfn.StateMachineType.EXPRESS,
            definition_body=aws_sfn.DefinitionBody.from_chainable(
                self.state_machine_definition,
            ),
            logs=aws_sfn.LogOptions(
                destination=self.state_machine_log_group,
                include_execution_data=True,
                level=aws_sfn.LogLevel.ALL,
            ),
        )

        self.state_machine.grant_start_execution(self.lambda_trigger_state_machine)

        # Add additional environment variables to the Lambda Functions
        self.lambda_trigger_state_machine.add_environment(
            "STATE_MACHINE_ARN",
            self.state_machine.state_machine_arn,
        )

    def create_bedrock_components(self) -> None:
        """
        Method to create the Bedrock Agent for the chatbot.
        """

        # Generic "PK" and "SK", to leverage Single-Table-Design
        self.calendar_events_dynamodb_table = aws_dynamodb.Table(
            self,
            "DynamoDB-Table-CalendarEvents",
            table_name=self.app_config["calendar_events_table_name"],
            partition_key=aws_dynamodb.Attribute(
                name="PK", type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="SK", type=aws_dynamodb.AttributeType.STRING
            ),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
        Tags.of(self.calendar_events_dynamodb_table).add(
            "Name", self.app_config["table_name"]
        )

        # Add permissions to the Lambda function resource policy. You use a resource-based policy to allow an AWS service to invoke your function.
        self.lambda_fetch_calendar_events.add_permission(
            "AllowBedrock",
            principal=aws_iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:bedrock:{self.region}:{self.account}:agent/*",
        )

        bedrock_agent_role = aws_iam.Role(
            self,
            "BedrockAgentRole",
            assumed_by=aws_iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role for Bedrock Agent",
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess",
                ),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSLambda_FullAccess",
                ),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess",
                ),
            ],
        )
        # Add additional IAM actions for the bedrock agent
        bedrock_agent_role.add_to_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelEndpoint",
                    "bedrock:InvokeModelEndpointAsync",
                ],
                resources=["*"],
            )
        )

        self.bedrock_agent = aws_bedrock.CfnAgent(
            self,
            "BedrockAgent",
            agent_name=f"{self.main_resources_name}-agent",
            agent_resource_role_arn=bedrock_agent_role.role_arn,
            description="Agent for chatbot",
            foundation_model="anthropic.claude-3-haiku-20240307-v1:0",
            instruction="You are a specialized agent in giving back calendar events based on the user's input <date>. User must provide the date, and you will make sure it has the format 'YYYY-MM-DD' for the parameter <date>. You will use it to get the list of events for that day and return them in a structured format.",
            auto_prepare=True,
            action_groups=[
                aws_bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="FetchCalendarEvents",
                    description="A function that is able to fetch the calendar events from the database from an input date.",
                    action_group_executor=aws_bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.lambda_fetch_calendar_events.function_arn,
                    ),
                    function_schema=aws_bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            aws_bedrock.CfnAgent.FunctionProperty(
                                name="FetchCalendarEvents",
                                # the properties below are optional
                                description="Function to fetch the calendar events based on the input input date",
                                parameters={
                                    "date": aws_bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Date to fetch the calendar events",
                                        required=True,
                                    ),
                                },
                            )
                        ]
                    ),
                ),
            ],
        )

        # Create an alias for the bedrock agent
        cfn_agent_alias = aws_bedrock.CfnAgentAlias(
            self,
            "MyCfnAgentAlias",
            agent_alias_name="bedrock-agent-alias",
            agent_id=self.bedrock_agent.ref,
            description="bedrock agent alias to simplify agent invocation",
        )
        cfn_agent_alias.add_dependency(self.bedrock_agent)

        # This string will be as <AGENT_ID>|<AGENT_ALIAS_ID>
        agent_alias_string = cfn_agent_alias.ref

        # Create SSM Parameters for the agent alias to use in the Lambda functions
        # Note: can not be added as Env-Vars due to circular dependency. Thus, SSM Params (decouple)
        aws_ssm.StringParameter(
            self,
            "SSMAgentAlias",
            parameter_name=f"/{self.deployment_environment}/aws-wpp/bedrock-agent-alias-id-full-string",
            string_value=agent_alias_string,
        )
        aws_ssm.StringParameter(
            self,
            "SSMAgentId",
            parameter_name=f"/{self.deployment_environment}/aws-wpp/bedrock-agent-id",
            string_value=self.bedrock_agent.ref,
        )

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

        if self.deployment_environment != "prod":
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
