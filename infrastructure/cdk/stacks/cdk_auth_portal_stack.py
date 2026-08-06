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
    aws_apigateway as aws_apigw,
    aws_certificatemanager,
    aws_cloudfront,
    aws_cloudfront_origins,
    aws_cognito,
    aws_dynamodb,
    aws_iam,
    aws_lambda,
    aws_lambda_event_sources,
    aws_logs,
    aws_route53,
    aws_route53_targets,
    aws_s3,
    aws_s3_deployment,
    aws_secretsmanager,
)
from constructs import Construct

# Own imports
from stacks.seed_data import SEED_BANK_CLIENTS, DEMO_USERS_PASSWORD

# Path to the repository root (this file lives in infrastructure/cdk/stacks/)
PATH_TO_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
PATH_TO_BACKEND_FOLDER = os.path.join(PATH_TO_REPO_ROOT, "backend")
PATH_TO_FRONTEND_FOLDER = os.path.join(PATH_TO_REPO_ROOT, "frontend")
PATH_TO_COMMON_LAYER = os.path.join(
    PATH_TO_REPO_ROOT, "lambda-layers", "common", "modules"
)


class AuthPortalStack(Stack):
    """
    Class to create the OPTIONAL Auth Portal resources: Cognito User Pool (with
    demo users), the auth-sessions DynamoDB table (TTL of 10 mins), the Auth
    API (API-GW + Lambda with custom DNS), the WhatsApp auth-successful trigger,
    and the Web Portal (CloudFront + private S3, custom DNS).
    --> Only deployed when <auth_enabled> is true in the cdk.json app_config.
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

        # Domain names (portal and auth API)
        self.hosted_zone_name = self.app_config["hosted_zone_name"]
        self.portal_domain_name = (
            f"{self.app_config['auth_portal_subdomain']}.{self.hosted_zone_name}"
        )
        self.auth_api_domain_name = (
            f"{self.app_config['auth_portal_subdomain']}-api.{self.hosted_zone_name}"
        )

        # Main methods for the deployment
        self.import_secrets()
        self.import_route53_hosted_zone()
        self.create_cognito_user_pool()
        self.create_dynamodb_table_auth_sessions()
        self.create_lambda_layers()
        self.create_auth_api_lambda()
        self.create_auth_api_gateway()
        self.configure_auth_api_custom_dns()
        self.create_auth_successful_trigger()
        self.create_seeder_custom_resource()
        self.create_web_portal()
        self.generate_cloudformation_outputs()

    def import_secrets(self):
        """Method to import the AWS Secret with the META/WhatsApp credentials."""
        self.secret_chatbot = aws_secretsmanager.Secret.from_secret_name_v2(
            self,
            "Secret-Chatbot",
            secret_name=self.app_config["secret_name"],
        )

    def import_route53_hosted_zone(self):
        """Method to import the Route53 Hosted Zone (from cdk.json config)."""
        self.route53_zone = aws_route53.HostedZone.from_hosted_zone_attributes(
            self,
            "Route53HostedZone",
            hosted_zone_id=self.app_config["hosted_zone_id"],
            zone_name=self.hosted_zone_name,
        )

    def create_cognito_user_pool(self):
        """Method to create the Cognito User Pool for the Auth Portal."""
        self.user_pool = aws_cognito.UserPool(
            self,
            "CognitoUserPool",
            user_pool_name=f"{self.main_resources_name}-auth-portal-{self.deployment_environment}",
            self_sign_up_enabled=False,
            sign_in_aliases=aws_cognito.SignInAliases(email=True),
            standard_attributes=aws_cognito.StandardAttributes(
                email=aws_cognito.StandardAttribute(required=True, mutable=True),
                phone_number=aws_cognito.StandardAttribute(
                    required=False, mutable=True
                ),
            ),
            password_policy=aws_cognito.PasswordPolicy(
                min_length=8,
                require_digits=True,
                require_lowercase=True,
                require_uppercase=True,
                require_symbols=True,
            ),
            account_recovery=aws_cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.user_pool_client = self.user_pool.add_client(
            "CognitoUserPoolClient",
            user_pool_client_name=f"{self.main_resources_name}-auth-portal-client-{self.deployment_environment}",
            auth_flows=aws_cognito.AuthFlow(user_password=True, user_srp=True),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            prevent_user_existence_errors=True,
        )

    def create_dynamodb_table_auth_sessions(self):
        """
        Method to create the DynamoDB auth-sessions table with TTL of 10 mins
        (attribute <ttl>) and a Stream that triggers the WhatsApp confirmation.
        """
        self.dynamodb_table_auth_sessions = aws_dynamodb.Table(
            self,
            "DynamoDB-Table-AuthSessions",
            table_name=(
                f"{self.main_resources_name}"
                f"-{self.app_config['table_name_auth_sessions']}"
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
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
        )

    def create_lambda_layers(self):
        """Method to create the Lambda Layers (shared Python dependencies)."""
        self.lambda_layer_common = aws_lambda.LayerVersion(
            self,
            "Layer-Common",
            layer_version_name=f"{self.main_resources_name}-auth-common-layer-{self.deployment_environment}",
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

    def create_auth_api_lambda(self):
        """Method to create the Auth API Lambda (FastAPI + Mangum)."""
        self.lambda_auth_api = aws_lambda.Function(
            self,
            "Lambda-Auth-API",
            function_name=f"{self.main_resources_name}-auth-api-{self.deployment_environment}",
            runtime=aws_lambda.Runtime.PYTHON_3_13,
            handler="auth/api/v1/main.handler",
            code=aws_lambda.Code.from_asset(PATH_TO_BACKEND_FOLDER),
            timeout=Duration.seconds(20),
            memory_size=512,
            layers=[self.lambda_layer_common],
            log_retention=aws_logs.RetentionDays.ONE_MONTH,
            environment={
                **self._get_powertools_environment("wpp-chatbot-auth-api"),
                "TABLE_NAME_AUTH_SESSIONS": self.dynamodb_table_auth_sessions.table_name,
                "AUTH_SESSION_TTL_SECONDS": str(
                    self.app_config["auth_session_ttl_seconds"]
                ),
            },
        )
        self.dynamodb_table_auth_sessions.grant_read_write_data(self.lambda_auth_api)

        # Validate Cognito AccessTokens (get_user does not need extra IAM perms,
        # but we scope it explicitly for clarity/least-privilege audits)
        self.lambda_auth_api.add_to_role_policy(
            aws_iam.PolicyStatement(
                sid="CognitoGetUser",
                actions=["cognito-idp:GetUser"],
                resources=[self.user_pool.user_pool_arn],
            )
        )

    def create_auth_api_gateway(self):
        """Method to create the Auth REST API Gateway with CloudWatch logging."""
        rest_api_name = (
            f"{self.main_resources_name}"
            f"-{self.app_config['api_gw_name_auth']}"
            f"-{self.deployment_environment}"
        )
        self.auth_api_access_logs_group = aws_logs.LogGroup(
            self,
            "AuthAPIGW-AccessLogs",
            log_group_name=f"/aws/apigateway/{rest_api_name}-access-logs",
            retention=aws_logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )
        self.auth_api = aws_apigw.LambdaRestApi(
            self,
            "AuthRESTAPI",
            rest_api_name=rest_api_name,
            description=f"Auth REST API Gateway for {self.main_resources_name} Web Portal",
            handler=self.lambda_auth_api,
            deploy_options=aws_apigw.StageOptions(
                stage_name=self.deployment_environment,
                logging_level=aws_apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                tracing_enabled=True,
                access_log_destination=aws_apigw.LogGroupLogDestination(
                    self.auth_api_access_logs_group
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
                allow_methods=aws_apigw.Cors.ALL_METHODS,
                allow_headers=["*"],
            ),
            endpoint_types=[aws_apigw.EndpointType.REGIONAL],
            cloud_watch_role=True,
            proxy=False,
            default_method_options=aws_apigw.MethodOptions(
                api_key_required=False,
                # Token validation (Cognito AccessToken) happens in the Lambda
                authorization_type=aws_apigw.AuthorizationType.NONE,
            ),
        )

        root_resource_api = self.auth_api.root.add_resource("api")
        root_resource_v1 = root_resource_api.add_resource("v1")
        root_resource_auth = root_resource_v1.add_resource("auth")
        root_resource_docs = root_resource_v1.add_resource("docs")
        root_resource_docs_proxy = root_resource_docs.add_resource("{path}")

        root_resource_auth.add_method("POST")
        root_resource_docs.add_method("GET")
        root_resource_docs_proxy.add_method("GET")

    def configure_auth_api_custom_dns(self):
        """Method to configure the CUSTOM DNS for the Auth API Gateway."""
        certificate = aws_certificatemanager.Certificate(
            self,
            "AuthAPICustomDomainCertificate",
            domain_name=self.auth_api_domain_name,
            validation=aws_certificatemanager.CertificateValidation.from_dns(
                self.route53_zone
            ),
        )
        self.auth_api.add_domain_name(
            "AuthAPICustomDomain",
            domain_name=self.auth_api_domain_name,
            certificate=certificate,
            security_policy=aws_apigw.SecurityPolicy.TLS_1_2,
        )
        aws_route53.ARecord(
            self,
            "AuthAPICustomDNS",
            zone=self.route53_zone,
            record_name=self.auth_api_domain_name,
            target=aws_route53.RecordTarget.from_alias(
                aws_route53_targets.ApiGatewayDomain(self.auth_api.domain_name)
            ),
        )

    def create_auth_successful_trigger(self):
        """
        Method to create the Lambda triggered by the auth-sessions DynamoDB
        Stream, sending the "authenticated successfully" WhatsApp message.
        """
        self.lambda_trigger_auth_successful = aws_lambda.Function(
            self,
            "Lambda-Trigger-Auth-Successful",
            function_name=f"{self.main_resources_name}-trigger-auth-successful-{self.deployment_environment}",
            runtime=aws_lambda.Runtime.PYTHON_3_13,
            handler="trigger/trigger_handler_auth_successful.lambda_handler",
            code=aws_lambda.Code.from_asset(PATH_TO_BACKEND_FOLDER),
            timeout=Duration.seconds(30),
            memory_size=512,
            layers=[self.lambda_layer_common],
            log_retention=aws_logs.RetentionDays.ONE_MONTH,
            environment={
                **self._get_powertools_environment("wpp-chatbot-trigger-auth"),
                "SECRET_NAME": self.app_config["secret_name"],
                "META_ENDPOINT": self.app_config["meta_endpoint"],
                "META_API_VERSION": self.app_config["meta_api_version"],
                "BOT_NAME": self.app_config["bot_name"],
            },
        )
        self.secret_chatbot.grant_read(self.lambda_trigger_auth_successful)
        self.lambda_trigger_auth_successful.add_event_source(
            aws_lambda_event_sources.DynamoEventSource(
                self.dynamodb_table_auth_sessions,
                starting_position=aws_lambda.StartingPosition.TRIM_HORIZON,
                batch_size=1,
                retry_attempts=2,
            )
        )

    def create_seeder_custom_resource(self):
        """
        Method to create the CustomResource that AUTOMATICALLY creates the
        Cognito demo users (email + phone_number) on CREATE/UPDATE stack events.
        """
        self.seeder_lambda = aws_lambda.Function(
            self,
            "Lambda-Seeder",
            function_name=f"{self.main_resources_name}-auth-seeder-{self.deployment_environment}",
            runtime=aws_lambda.Runtime.PYTHON_3_13,
            handler="seeder/handler.lambda_handler",
            code=aws_lambda.Code.from_asset(PATH_TO_BACKEND_FOLDER),
            timeout=Duration.minutes(2),
            memory_size=128,
            log_retention=aws_logs.RetentionDays.ONE_WEEK,
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "TABLE_NAME_AUTH_SESSIONS": self.dynamodb_table_auth_sessions.table_name,
                "LOG_LEVEL": self.app_config["log_level"],
            },
        )
        # Write access to seed the permanent USERNAME<->WHATSAPP mappings
        self.dynamodb_table_auth_sessions.grant_read_write_data(self.seeder_lambda)
        self.seeder_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                sid="CognitoAdminCreateDemoUsers",
                actions=[
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminSetUserPassword",
                    "cognito-idp:AdminUpdateUserAttributes",
                ],
                resources=[self.user_pool.user_pool_arn],
            )
        )

        # Any change to the SEED_BANK_CLIENTS triggers an UPDATE (re-seed)
        seed_users = [
            {
                "user_email": client["user_email"],
                "username": client.get("username", client["user_email"].split("@")[0]),
                "full_name": client["full_name"],
                "phone_number": client["phone_number"],
            }
            for client in SEED_BANK_CLIENTS
        ]
        # NOTE: the demo users password comes from the local <.env> file
        # (DEMO_USERS_PASSWORD), NOT from cdk.json (avoid committing secrets)
        self.seeder_custom_resource = CustomResource(
            self,
            "CustomResource-Seeder",
            service_token=self.seeder_lambda.function_arn,
            properties={
                "SeedUsers": json.dumps(seed_users),
                "DemoUsersPassword": DEMO_USERS_PASSWORD,
            },
        )

    def create_web_portal(self):
        """
        Method to create the Web Portal: private S3 bucket + CloudFront (OAC)
        + ACM certificate + Route53 records + S3 deployment (with config.json).
        --> NO S3 Website functionality and NO public bucket (secure pattern).
        """
        self.portal_bucket = aws_s3.Bucket(
            self,
            "PortalBucket",
            bucket_name=f"{self.main_resources_name}-auth-portal-{self.account}-{self.deployment_environment}",
            public_read_access=False,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        portal_certificate = aws_certificatemanager.Certificate(
            self,
            "PortalCertificate",
            domain_name=self.portal_domain_name,
            validation=aws_certificatemanager.CertificateValidation.from_dns(
                self.route53_zone
            ),
        )

        self.portal_distribution = aws_cloudfront.Distribution(
            self,
            "PortalDistribution",
            comment=f"Distribution for {self.main_resources_name} Auth Portal ({self.deployment_environment})",
            default_behavior=aws_cloudfront.BehaviorOptions(
                origin=aws_cloudfront_origins.S3BucketOrigin.with_origin_access_control(
                    self.portal_bucket
                ),
                viewer_protocol_policy=aws_cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            domain_names=[self.portal_domain_name],
            certificate=portal_certificate,
            default_root_object="index.html",
            error_responses=[
                aws_cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
                aws_cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                ),
            ],
        )

        aws_route53.ARecord(
            self,
            "PortalAliasRecord",
            zone=self.route53_zone,
            record_name=self.portal_domain_name,
            target=aws_route53.RecordTarget.from_alias(
                aws_route53_targets.CloudFrontTarget(self.portal_distribution)
            ),
        )

        # Deploy the portal static files + runtime config.json (dynamic values)
        aws_s3_deployment.BucketDeployment(
            self,
            "PortalS3Deployment",
            sources=[
                aws_s3_deployment.Source.asset(PATH_TO_FRONTEND_FOLDER),
                aws_s3_deployment.Source.json_data(
                    "config.json",
                    {
                        "region": self.region,
                        "userPoolId": self.user_pool.user_pool_id,
                        "userPoolClientId": self.user_pool_client.user_pool_client_id,
                        "authApiUrl": f"https://{self.auth_api_domain_name}",
                    },
                ),
            ],
            destination_bucket=self.portal_bucket,
            distribution=self.portal_distribution,
            distribution_paths=["/*"],
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
            "AuthPortalURL",
            value=f"https://{self.portal_domain_name}",
            description="Auth Portal URL (CloudFront custom DNS)",
        )
        CfnOutput(
            self,
            "AuthAPIURL",
            value=f"https://{self.auth_api_domain_name}/api/v1/auth",
            description="Auth API endpoint (custom DNS)",
        )
        CfnOutput(
            self,
            "CognitoUserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID for the Auth Portal",
        )
