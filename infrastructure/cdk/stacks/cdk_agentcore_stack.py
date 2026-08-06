# Built-in imports
import json
import os

# External imports
from aws_cdk import (
    CfnOutput,
    CustomResource,
    Duration,
    RemovalPolicy,
    Stack,
    aws_bedrockagentcore,
    aws_dynamodb,
    aws_iam,
    aws_lambda,
    aws_logs,
    aws_s3_assets,
    aws_ssm,
)
from constructs import Construct

# Own imports
from stacks.seed_data import SEED_BANK_CLIENTS

# Path to the repository root (this file lives in infrastructure/cdk/stacks/)
PATH_TO_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
PATH_TO_AGENT_PACKAGE = os.path.join(PATH_TO_REPO_ROOT, "agent", "dist", "package")
PATH_TO_BACKEND_FOLDER = os.path.join(PATH_TO_REPO_ROOT, "backend")


class AgentCoreStack(Stack):
    """
    Class to create the AgentCore Runtime resources: the Strands "DemoAgent"
    (Financial Bank Agent) deployed via DIRECT CODE DEPLOY (ZIP), the DynamoDB
    bank-clients table with its seeder CustomResource, and the SSM Parameter
    that exposes the AgentCore Runtime ARN to other stacks (decoupled).
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

        # Main methods for the deployment
        self.create_dynamodb_table_bank_clients()
        self.create_seeder_custom_resource()
        self.create_agent_code_asset()
        self.create_agentcore_runtime_role()
        self.create_agentcore_runtime()
        self.create_ssm_parameters()
        self.generate_cloudformation_outputs()

    def create_dynamodb_table_bank_clients(self):
        """Method to create the DynamoDB table with the bank clients sample data."""
        self.table_name_bank_clients = (
            f"{self.main_resources_name}"
            f"-{self.app_config['table_name_bank_clients']}"
            f"-{self.deployment_environment}"
        )
        self.dynamodb_table_bank_clients = aws_dynamodb.Table(
            self,
            "DynamoDB-Table-BankClients",
            table_name=self.table_name_bank_clients,
            partition_key=aws_dynamodb.Attribute(
                name="user_email",
                type=aws_dynamodb.AttributeType.STRING,
            ),
            billing_mode=aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=aws_dynamodb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
        )

    def create_seeder_custom_resource(self):
        """
        Method to create the CustomResource that AUTOMATICALLY populates the
        DynamoDB bank-clients table on CREATE/UPDATE stack events.
        """
        self.seeder_lambda = aws_lambda.Function(
            self,
            "Lambda-Seeder",
            function_name=f"{self.main_resources_name}-agentcore-seeder-{self.deployment_environment}",
            runtime=aws_lambda.Runtime.PYTHON_3_13,
            handler="seeder/handler.lambda_handler",
            code=aws_lambda.Code.from_asset(PATH_TO_BACKEND_FOLDER),
            timeout=Duration.minutes(2),
            memory_size=128,
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
            environment={
                "TABLE_NAME": self.dynamodb_table_bank_clients.table_name,
                "LOG_LEVEL": self.app_config["log_level"],
            },
        )
        self.dynamodb_table_bank_clients.grant_read_write_data(self.seeder_lambda)

        # Any change to the SEED_BANK_CLIENTS triggers an UPDATE (re-seed)
        self.seeder_custom_resource = CustomResource(
            self,
            "CustomResource-Seeder",
            service_token=self.seeder_lambda.function_arn,
            properties={
                "SeedItems": json.dumps(SEED_BANK_CLIENTS),
            },
        )

    def create_agent_code_asset(self):
        """
        Method to create the S3 Asset with the Agent's deployment package
        (Strands Agent code + arm64 dependencies, built by <agent/Makefile>).
        """
        self.agent_code_asset = aws_s3_assets.Asset(
            self,
            "AgentCodeAsset",
            path=PATH_TO_AGENT_PACKAGE,
        )

    def create_agentcore_runtime_role(self):
        """Method to create the IAM Role for the AgentCore Runtime (least privilege)."""
        self.agentcore_runtime_role = aws_iam.Role(
            self,
            "AgentCoreRuntimeRole",
            role_name=f"{self.main_resources_name}-agentcore-runtime-role-{self.deployment_environment}",
            assumed_by=aws_iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            description="Execution role for the AgentCore Runtime (Strands DemoAgent)",
        )

        # Bedrock model invocation (cross-region inference profiles)
        self.agentcore_runtime_role.add_to_policy(
            aws_iam.PolicyStatement(
                sid="BedrockInvokeModel",
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        # Read access to the bank-clients table (used by the Agent's tools)
        self.dynamodb_table_bank_clients.grant_read_data(self.agentcore_runtime_role)

        # Read access to the deployment package in S3 (direct code deploy)
        self.agent_code_asset.grant_read(self.agentcore_runtime_role)

        # CloudWatch Logs and X-Ray (AgentCore observability)
        self.agentcore_runtime_role.add_to_policy(
            aws_iam.PolicyStatement(
                sid="CloudWatchLogsAccess",
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/bedrock-agentcore/*"
                ],
            )
        )
        self.agentcore_runtime_role.add_to_policy(
            aws_iam.PolicyStatement(
                sid="ObservabilityAccess",
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "cloudwatch:PutMetricData",
                ],
                resources=["*"],
            )
        )

    def create_agentcore_runtime(self):
        """
        Method to create the AgentCore Runtime via DIRECT CODE DEPLOY (ZIP),
        instead of a Docker container image.
        """
        # AgentCore Runtime names only allow letters, numbers and underscores
        runtime_name = (
            f"{self.app_config['agentcore_runtime_name']}"
            f"_{self.deployment_environment}"
        )

        self.agentcore_runtime = aws_bedrockagentcore.CfnRuntime(
            self,
            "AgentCoreRuntime",
            agent_runtime_name=runtime_name,
            description=(
                f"Strands DemoAgent (Financial Bank Agent) for {self.main_resources_name} "
                f"in {self.deployment_environment} environment (direct code deploy)"
            ),
            agent_runtime_artifact=aws_bedrockagentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                code_configuration=aws_bedrockagentcore.CfnRuntime.CodeConfigurationProperty(
                    code=aws_bedrockagentcore.CfnRuntime.CodeProperty(
                        s3=aws_bedrockagentcore.CfnRuntime.S3LocationProperty(
                            bucket=self.agent_code_asset.s3_bucket_name,
                            prefix=self.agent_code_asset.s3_object_key,
                        )
                    ),
                    entry_point=["main.py"],
                    runtime="PYTHON_3_13",
                )
            ),
            network_configuration=aws_bedrockagentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode="PUBLIC",
            ),
            protocol_configuration="HTTP",
            role_arn=self.agentcore_runtime_role.role_arn,
            environment_variables={
                "TABLE_NAME": self.dynamodb_table_bank_clients.table_name,
                "BEDROCK_MODEL_ID": self.app_config["bedrock_model_id"],
                "BOT_NAME": self.app_config["bot_name"],
                "LANGUAGE": self.app_config["language"],
                "LOG_LEVEL": self.app_config["log_level"],
            },
        )
        self.agentcore_runtime.node.add_dependency(self.agentcore_runtime_role)

    def create_ssm_parameters(self):
        """
        Method to create the SSM Parameter with the AgentCore Runtime ARN.
        --> This decouples the stacks: the "Process Message" Lambda receives the
            SSM Parameter NAME as ENV-VAR and fetches the VALUE dynamically.
        """
        self.ssm_param_agentcore_runtime_arn = aws_ssm.StringParameter(
            self,
            "SSMParameter-AgentCoreRuntimeArn",
            parameter_name=(
                f"/{self.deployment_environment}/{self.main_resources_name}"
                f"/{self.app_config['ssm_param_agentcore_runtime_arn']}"
            ),
            string_value=self.agentcore_runtime.attr_agent_runtime_arn,
            description="ARN of the AgentCore Runtime (Strands DemoAgent)",
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
            "AgentCoreRuntimeArn",
            value=self.agentcore_runtime.attr_agent_runtime_arn,
            description="ARN of the AgentCore Runtime (Strands DemoAgent)",
        )
        CfnOutput(
            self,
            "BankClientsTableName",
            value=self.dynamodb_table_bank_clients.table_name,
            description="DynamoDB table with the bank clients sample data",
        )
