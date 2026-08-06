# Built-in imports
import os

# External imports
from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as aws_apigw,
    aws_certificatemanager,
    aws_dynamodb,
    aws_iam,
    aws_lambda,
    aws_lambda_event_sources,
    aws_logs,
    aws_route53,
    aws_route53_targets,
    aws_secretsmanager,
    aws_stepfunctions as aws_sfn,
    aws_stepfunctions_tasks as aws_sfn_tasks,
)
from constructs import Construct

# Path to the repository root (this file lives in infrastructure/cdk/stacks/)
PATH_TO_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
PATH_TO_BACKEND_FOLDER = os.path.join(PATH_TO_REPO_ROOT, "backend")
PATH_TO_COMMON_LAYER = os.path.join(
    PATH_TO_REPO_ROOT, "lambda-layers", "common", "modules"
)


class ChatbotAPIStack(Stack):
    """
    Class to create the ChatbotAPI resources: API Gateway (custom DNS) with the
    FastAPI WhatsApp Webhook Lambda, DynamoDB messages table (NO TTL, messages
    kept forever), and the processing State Machine (Check Auth -> Process
    Message via AgentCore Runtime -> Send Response via META API).
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        main_resources_name: str,
        app_config: dict[str, str],
        **kwargs,
    ) -> None:
        """
        :param scope (Construct): Parent of this stack, usually an 'App' or a 'Stage'.
        :param construct_id (str): The construct ID of this stack.
        :param main_resources_name (str): The main unique identifier of this stack.
        :param app_config (dict[str, str]): Dictionary with relevant configuration values for the stack.
        """
        super().__init__(scope, construct_id, **kwargs)

        # Input parameters
        self.construct_id = construct_id
        self.main_resources_name = main_resources_name
        self.app_config = app_config
        self.deployment_environment = self.app_config["deployment_environment"]
        self.auth_enabled = str(self.app_config.get("auth_enabled", False)).lower()

        # Shared naming (decoupled cross-stack physical names)
        self.table_name_auth_sessions = (
            f"{self.main_resources_name}"
            f"-{self.app_config['table_name_auth_sessions']}"
            f"-{self.deployment_environment}"
        )
        self.table_name_bank_clients = (
            f"{self.main_resources_name}"
            f"-{self.app_config['table_name_bank_clients']}"
            f"-{self.deployment_environment}"
        )
        self.ssm_param_name_agentcore_runtime_arn = (
            f"/{self.deployment_environment}/{self.main_resources_name}"
            f"/{self.app_config['ssm_param_agentcore_runtime_arn']}"
        )
        self.auth_portal_url = (
            f"https://{self.app_config['auth_portal_subdomain']}"
            f".{self.app_config['hosted_zone_name']}"
        )

        # Main methods for the deployment
        self.import_secrets()
        self.create_dynamodb_table_messages()
        self.create_lambda_layers()
        self.create_lambda_functions()
        self.create_dynamodb_streams()
        self.create_rest_api()
        self.configure_rest_api()
        self.configure_custom_dns()
        self.create_state_machine_tasks()
        self.create_state_machine_definition()
        self.create_state_machine()
        self.configure_extra_permissions()
        self.generate_cloudformation_outputs()

    def import_secrets(self):
        """
        Method to import the AWS Secret with the META/WhatsApp credentials.
        --> PREREQUISITE: the secret MUST be created MANUALLY before the first
            deployment with keys: AWS_API_KEY_TOKEN, META_TOKEN,
            META_FROM_PHONE_NUMBER_ID (see GETTING_STARTED.md).
        """
        self.secret_chatbot = aws_secretsmanager.Secret.from_secret_name_v2(
            self,
            "Secret-Chatbot",
            secret_name=self.app_config["secret_name"],
        )

    def create_dynamodb_table_messages(self):
        """
        Method to create the DynamoDB table for the WhatsApp messages.
        --> NO TTL configured on purpose: messages are kept FOREVER.
        """
        self.dynamodb_table_messages = aws_dynamodb.Table(
            self,
            "DynamoDB-Table-Messages",
            table_name=(
                f"{self.main_resources_name}"
                f"-{self.app_config['table_name_messages']}"
                f"-{self.deployment_environment}"
            ),
            partition_key=aws_dynamodb.Attribute(
                name="PK", type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="SK", type=aws_dynamodb.AttributeType.STRING
            ),
            stream=aws_dynamodb.StreamViewType.NEW_IMAGE,
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=aws_dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
            removal_policy=(
                RemovalPolicy.RETAIN
                if self.deployment_environment == "prod"
                else RemovalPolicy.DESTROY
            ),
        )

    def create_lambda_layers(self):
        """Method to create the Lambda Layers (shared Python dependencies)."""
        self.lambda_layer_common = aws_lambda.LayerVersion(
            self,
            "Layer-Common",
            layer_version_name=f"{self.main_resources_name}-common-layer-{self.deployment_environment}",
            code=aws_lambda.Code.from_asset(PATH_TO_COMMON_LAYER),
            compatible_runtimes=[aws_lambda.Runtime.PYTHON_3_13],
            description=(
                "Common dependencies layer: FastAPI, Mangum, Pydantic v2, "
                "Requests and AWS Lambda PowerTools v3"
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _get_powertools_environment(self, service_name: str) -> dict:
        """Helper for the shared PowerTools env-vars (EXTRA LOGGING in DEBUG)."""
        return {
            "ENVIRONMENT": self.deployment_environment,
            "LOG_LEVEL": self.app_config["log_level"],
            "POWERTOOLS_LOG_LEVEL": self.app_config["log_level"],
            "POWERTOOLS_SERVICE_NAME": service_name,
            "POWERTOOLS_LOGGER_LOG_EVENT": "true",
        }

    def create_lambda_functions(self):
        """Method to create the Lambda Functions for the chatbot solution."""

        # Lambda 1: WhatsApp Webhook (FastAPI + Mangum)
        self.lambda_whatsapp_webhook = aws_lambda.Function(
            self,
            "Lambda-WhatsApp-Webhook",
            function_name=f"{self.main_resources_name}-webhook-{self.deployment_environment}",
            runtime=aws_lambda.Runtime.PYTHON_3_13,
            handler="whatsapp_webhook/api/v1/main.handler",
            code=aws_lambda.Code.from_asset(PATH_TO_BACKEND_FOLDER),
            timeout=Duration.seconds(20),
            memory_size=512,
            layers=[self.lambda_layer_common],
            log_retention=aws_logs.RetentionDays.ONE_MONTH,
            environment={
                **self._get_powertools_environment("wpp-chatbot-webhook"),
                "DYNAMODB_TABLE": self.dynamodb_table_messages.table_name,
                "SECRET_NAME": self.app_config["secret_name"],
            },
        )
        self.dynamodb_table_messages.grant_read_write_data(self.lambda_whatsapp_webhook)
        self.secret_chatbot.grant_read(self.lambda_whatsapp_webhook)

        # Lambda 2: Trigger of the State Machine (from DynamoDB Streams)
        self.lambda_trigger_state_machine = aws_lambda.Function(
            self,
            "Lambda-Trigger-State-Machine",
            function_name=f"{self.main_resources_name}-trigger-state-machine-{self.deployment_environment}",
            runtime=aws_lambda.Runtime.PYTHON_3_13,
            handler="trigger/trigger_handler.lambda_handler",
            code=aws_lambda.Code.from_asset(PATH_TO_BACKEND_FOLDER),
            timeout=Duration.seconds(20),
            memory_size=512,
            layers=[self.lambda_layer_common],
            log_retention=aws_logs.RetentionDays.ONE_MONTH,
            environment={
                **self._get_powertools_environment("wpp-chatbot-trigger"),
            },
        )

        # Lambda 3: State Machine steps (Check Auth, Process Message, Send Response)
        self.lambda_state_machine = aws_lambda.Function(
            self,
            "Lambda-SM-Process-Message",
            function_name=f"{self.main_resources_name}-state-machine-{self.deployment_environment}",
            runtime=aws_lambda.Runtime.PYTHON_3_13,
            handler="state_machine/state_machine_handler.lambda_handler",
            code=aws_lambda.Code.from_asset(PATH_TO_BACKEND_FOLDER),
            timeout=Duration.seconds(120),
            memory_size=512,
            layers=[self.lambda_layer_common],
            log_retention=aws_logs.RetentionDays.ONE_MONTH,
            environment={
                **self._get_powertools_environment("wpp-chatbot-state-machine"),
                "SECRET_NAME": self.app_config["secret_name"],
                "META_ENDPOINT": self.app_config["meta_endpoint"],
                "META_API_VERSION": self.app_config["meta_api_version"],
                "BOT_NAME": self.app_config["bot_name"],
                "LANGUAGE": self.app_config["language"],
                # AgentCore Runtime ARN resolved dynamically from SSM Parameter
                "AGENTCORE_RUNTIME_ARN_PARAM": self.ssm_param_name_agentcore_runtime_arn,
                # Auth configurations (bypass when AUTH_ENABLED is "false")
                "AUTH_ENABLED": self.auth_enabled,
                "TABLE_NAME_AUTH_SESSIONS": self.table_name_auth_sessions,
                "AUTH_PORTAL_URL": self.auth_portal_url,
                "AUTH_SESSION_TTL_SECONDS": str(
                    self.app_config["auth_session_ttl_seconds"]
                ),
                # Bank clients table (profile metadata for hyperpersonalization)
                "TABLE_NAME_BANK_CLIENTS": self.table_name_bank_clients,
            },
        )
        self.secret_chatbot.grant_read(self.lambda_state_machine)

    def create_dynamodb_streams(self):
        """Method to create the DynamoDB Stream trigger for the State Machine."""
        self.lambda_trigger_state_machine.add_event_source(
            aws_lambda_event_sources.DynamoEventSource(
                self.dynamodb_table_messages,
                starting_position=aws_lambda.StartingPosition.TRIM_HORIZON,
                batch_size=1,
                retry_attempts=2,
            )
        )

    def create_rest_api(self):
        """
        Method to create the REST API Gateway with CloudWatch access logging
        enabled and the FastAPI Webhook Lambda integration.
        """
        rest_api_name = (
            f"{self.main_resources_name}"
            f"-{self.app_config['api_gw_name_webhook']}"
            f"-{self.deployment_environment}"
        )
        self.api_access_logs_group = aws_logs.LogGroup(
            self,
            "APIGW-AccessLogs",
            log_group_name=f"/aws/apigateway/{rest_api_name}-access-logs",
            retention=aws_logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.api = aws_apigw.LambdaRestApi(
            self,
            "RESTAPI",
            rest_api_name=rest_api_name,
            description=f"REST API Gateway for {self.main_resources_name} WhatsApp Webhook",
            handler=self.lambda_whatsapp_webhook,
            deploy_options=aws_apigw.StageOptions(
                stage_name=self.deployment_environment,
                logging_level=aws_apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                tracing_enabled=True,
                access_log_destination=aws_apigw.LogGroupLogDestination(
                    self.api_access_logs_group
                ),
                access_log_format=aws_apigw.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
            ),
            default_cors_preflight_options=aws_apigw.CorsOptions(
                allow_origins=aws_apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "POST"],
                allow_headers=["*"],
            ),
            endpoint_types=[aws_apigw.EndpointType.REGIONAL],
            cloud_watch_role=True,
            proxy=False,
            default_method_options=aws_apigw.MethodOptions(
                api_key_required=False,
                # TODO: Token validation happens in the Lambda (META verify token)
                authorization_type=aws_apigw.AuthorizationType.NONE,
            ),
        )

    def configure_rest_api(self):
        """Method to configure the REST API resources (paths and methods)."""
        root_resource_api = self.api.root.add_resource("api")
        root_resource_v1 = root_resource_api.add_resource("v1")

        root_resource_webhook = root_resource_v1.add_resource("webhook")
        root_resource_docs = root_resource_v1.add_resource("docs")
        root_resource_docs_proxy = root_resource_docs.add_resource("{path}")

        # Endpoints for the webhook (GET verification and POST callbacks)
        root_resource_webhook.add_method("GET")
        root_resource_webhook.add_method("POST")

        # Endpoints for the API docs (Swagger UI)
        root_resource_docs.add_method("GET")
        root_resource_docs_proxy.add_method("GET")

    def configure_custom_dns(self):
        """
        Method to configure the CUSTOM DNS for the API Gateway endpoint
        (e.g. wpp-api-webhook-aws.cb.events.genai.aws.dev).
        """
        hosted_zone_name = self.app_config["hosted_zone_name"]
        self.api_domain_name = (
            f"{self.app_config['api_webhook_subdomain']}.{hosted_zone_name}"
        )

        self.route53_zone = aws_route53.HostedZone.from_hosted_zone_attributes(
            self,
            "Route53HostedZone",
            hosted_zone_id=self.app_config["hosted_zone_id"],
            zone_name=hosted_zone_name,
        )
        certificate = aws_certificatemanager.Certificate(
            self,
            "CustomDomainCertificate",
            domain_name=self.api_domain_name,
            validation=aws_certificatemanager.CertificateValidation.from_dns(
                self.route53_zone
            ),
        )
        self.api.add_domain_name(
            "CustomDomain",
            domain_name=self.api_domain_name,
            certificate=certificate,
            security_policy=aws_apigw.SecurityPolicy.TLS_1_2,
        )
        self.custom_dns_record = aws_route53.ARecord(
            self,
            "CustomDNS",
            zone=self.route53_zone,
            record_name=self.api_domain_name,
            target=aws_route53.RecordTarget.from_alias(
                aws_route53_targets.ApiGatewayDomain(self.api.domain_name)
            ),
        )

    def _create_lambda_task(
        self, construct_id: str, state_name: str, class_name: str, method_name: str
    ) -> aws_sfn_tasks.LambdaInvoke:
        """Helper to create the State Machine Lambda tasks (dynamic dispatch)."""
        return aws_sfn_tasks.LambdaInvoke(
            self,
            construct_id,
            state_name=state_name,
            lambda_function=self.lambda_state_machine,
            payload=aws_sfn.TaskInput.from_object(
                {
                    "event.$": "$",
                    "params": {
                        "class_name": class_name,
                        "method_name": method_name,
                    },
                }
            ),
            output_path="$.Payload",
        )

    def create_state_machine_tasks(self):
        """Method to create the tasks (states) for the State Machine."""

        self.task_validate_message = self._create_lambda_task(
            "Task-ValidateMessage",
            "Validate Message",
            "ValidateMessage",
            "validate_input",
        )
        self.task_check_auth = self._create_lambda_task(
            "Task-CheckAuth",
            "Check Auth",
            "CheckAuth",
            "check_auth",
        )
        self.task_process_message = self._create_lambda_task(
            "Task-ProcessMessage",
            "Process Message",
            "ProcessMessage",
            "process_message",
        )
        self.task_process_voice = self._create_lambda_task(
            "Task-ProcessVoice",
            "Process Voice (TBD)",
            "ProcessVoice",
            "process_voice",
        )
        self.task_process_image = self._create_lambda_task(
            "Task-ProcessImage",
            "Process Image (TBD)",
            "ProcessImage",
            "process_image",
        )
        self.task_process_video = self._create_lambda_task(
            "Task-ProcessVideo",
            "Process Video (TBD)",
            "ProcessVideo",
            "process_video",
        )
        self.task_send_response = self._create_lambda_task(
            "Task-SendResponse",
            "Send Response",
            "SendResponse",
            "send_response",
        )
        self.task_process_success = self._create_lambda_task(
            "Task-Success",
            "Process Success",
            "Success",
            "process_success",
        )
        self.task_process_failure = self._create_lambda_task(
            "Task-Failure",
            "Process Failure",
            "Failure",
            "process_failure",
        )

        # Retries for the most critical tasks (Agent invocation and META API)
        for task in [self.task_process_message, self.task_send_response]:
            task.add_retry(
                errors=["States.ALL"],
                interval=Duration.seconds(1),
                max_attempts=3,
                backoff_rate=2.0,
            )

        self.task_not_implemented = aws_sfn.Pass(
            self,
            "Task-NotImplemented",
            state_name="Not Implemented (TBD)",
            result_path=aws_sfn.JsonPath.DISCARD,
        )

        self.succeed_state = aws_sfn.Succeed(
            self,
            "Succeed",
            comment="Successful execution of the State Machine",
        )
        self.failure_state = aws_sfn.Fail(
            self,
            "Exception Handling Finished",
            comment="State Machine failure handling finished",
        )

    def create_state_machine_definition(self):
        """Method to create the State Machine definition (chained states)."""

        # Failure path (wired via catch on the main tasks)
        self.task_process_failure.next(self.failure_state)

        # Choice: route the message based on the (validated + auth-checked) type
        self.choice_message_type = aws_sfn.Choice(
            self, "Message Type?", comment="Route the message based on its type"
        )
        self.choice_message_type.when(
            aws_sfn.Condition.string_equals("$.message_type", "auth_prompt"),
            self.task_send_response,
        )
        self.choice_message_type.when(
            aws_sfn.Condition.string_equals("$.message_type", "text"),
            self.task_process_message,
        )
        self.choice_message_type.when(
            aws_sfn.Condition.or_(
                aws_sfn.Condition.string_equals("$.message_type", "voice"),
                aws_sfn.Condition.string_equals("$.message_type", "audio"),
            ),
            self.task_process_voice,
        )
        self.choice_message_type.when(
            aws_sfn.Condition.string_equals("$.message_type", "image"),
            self.task_process_image,
        )
        self.choice_message_type.when(
            aws_sfn.Condition.string_equals("$.message_type", "video"),
            self.task_process_video,
        )
        self.choice_message_type.otherwise(self.task_not_implemented)

        # Main flow
        self.task_validate_message.next(self.task_check_auth)
        self.task_check_auth.next(self.choice_message_type)
        self.task_process_message.next(self.task_send_response)
        self.task_process_voice.next(self.task_send_response)
        self.task_process_image.next(self.task_send_response)
        self.task_process_video.next(self.task_send_response)
        self.task_not_implemented.next(self.task_send_response)
        self.task_send_response.next(self.task_process_success)
        self.task_process_success.next(self.succeed_state)

        # Catch errors on critical tasks towards the failure handling
        for task in [
            self.task_validate_message,
            self.task_check_auth,
            self.task_process_message,
            self.task_send_response,
        ]:
            task.add_catch(
                self.task_process_failure,
                errors=["States.ALL"],
                result_path="$.error_details",
            )

        self.state_machine_definition = self.task_validate_message

    def create_state_machine(self):
        """Method to create the State Machine (EXPRESS) with full logging."""
        log_group_state_machine = aws_logs.LogGroup(
            self,
            "StateMachine-LogGroup",
            log_group_name=f"/aws/vendedlogs/states/{self.main_resources_name}-{self.deployment_environment}",
            removal_policy=RemovalPolicy.DESTROY,
            retention=aws_logs.RetentionDays.ONE_MONTH,
        )

        self.state_machine = aws_sfn.StateMachine(
            self,
            "StateMachine-ProcessMessage",
            state_machine_name=f"{self.main_resources_name}-process-message-{self.deployment_environment}",
            state_machine_type=aws_sfn.StateMachineType.EXPRESS,
            definition_body=aws_sfn.DefinitionBody.from_chainable(
                self.state_machine_definition
            ),
            logs=aws_sfn.LogOptions(
                destination=log_group_state_machine,
                include_execution_data=True,
                level=aws_sfn.LogLevel.ALL,
            ),
            tracing_enabled=True,
        )

        # Allow the trigger Lambda to start executions of the State Machine
        self.state_machine.grant_start_execution(self.lambda_trigger_state_machine)
        self.lambda_trigger_state_machine.add_environment(
            "STATE_MACHINE_ARN", self.state_machine.state_machine_arn
        )

    def configure_extra_permissions(self):
        """
        Method to configure the extra IAM permissions for the State Machine
        Lambda: SSM Parameter read, AgentCore Runtime invocation, and the
        (conditional) auth-sessions DynamoDB table access.
        """
        # Read the SSM Parameter with the AgentCore Runtime ARN
        self.lambda_state_machine.add_to_role_policy(
            aws_iam.PolicyStatement(
                sid="SSMGetAgentCoreRuntimeArnParameter",
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter{self.ssm_param_name_agentcore_runtime_arn}"
                ],
            )
        )

        # Invoke the AgentCore Runtime (decoupled from the agentcore stack)
        self.lambda_state_machine.add_to_role_policy(
            aws_iam.PolicyStatement(
                sid="InvokeAgentCoreRuntime",
                actions=["bedrock-agentcore:InvokeAgentRuntime"],
                resources=[
                    f"arn:aws:bedrock-agentcore:{self.region}:{self.account}:runtime/*"
                ],
            )
        )

        # Read access to the bank-clients table (profile metadata loading)
        self.lambda_state_machine.add_to_role_policy(
            aws_iam.PolicyStatement(
                sid="BankClientsTableReadAccess",
                actions=["dynamodb:GetItem"],
                resources=[
                    f"arn:aws:dynamodb:{self.region}:{self.account}"
                    f":table/{self.table_name_bank_clients}"
                ],
            )
        )

        # Conditional: auth-sessions table access (only when auth is enabled)
        if self.auth_enabled == "true":
            table_arn_auth_sessions = (
                f"arn:aws:dynamodb:{self.region}:{self.account}"
                f":table/{self.table_name_auth_sessions}"
            )
            self.lambda_state_machine.add_to_role_policy(
                aws_iam.PolicyStatement(
                    sid="AuthSessionsTableAccess",
                    actions=[
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                    ],
                    resources=[table_arn_auth_sessions],
                )
            )

    def generate_cloudformation_outputs(self):
        """Method to add the relevant CloudFormation outputs."""
        CfnOutput(
            self,
            "DeploymentEnvironment",
            value=self.deployment_environment,
            description="Deployment environment",
        )
        CfnOutput(
            self,
            "APIChatbot",
            value=f"https://{self.api_domain_name}/api/v1/webhook",
            description="WhatsApp Webhook endpoint (custom DNS)",
        )
        CfnOutput(
            self,
            "APIDocs",
            value=f"https://{self.api_domain_name}/api/v1/docs",
            description="API Docs endpoint (custom DNS)",
        )
        CfnOutput(
            self,
            "MessagesTableName",
            value=self.dynamodb_table_messages.table_name,
            description="DynamoDB messages table (NO TTL, messages kept forever)",
        )
