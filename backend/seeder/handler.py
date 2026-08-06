################################################################################
# CloudFormation CustomResource Lambda: AUTOMATICALLY populates the DynamoDB
# bank-clients table and/or the Cognito demo users on CREATE/UPDATE events.
################################################################################

# Built-in imports
import json
import logging
import os
import urllib.request

# External imports
import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "DEBUG"))

TABLE_NAME = os.environ.get("TABLE_NAME", "")
TABLE_NAME_AUTH_SESSIONS = os.environ.get("TABLE_NAME_AUTH_SESSIONS", "")
USER_POOL_ID = os.environ.get("USER_POOL_ID", "")

dynamodb_client = boto3.client("dynamodb")
cognito_client = boto3.client("cognito-idp")


def send_cfn_response(event, context, response_status, reason=None):
    """Send the response back to CloudFormation (custom resource protocol)."""
    response_body = json.dumps(
        {
            "Status": response_status,
            "Reason": reason or f"See CloudWatch Logs: {context.log_stream_name}",
            "PhysicalResourceId": f"{TABLE_NAME or USER_POOL_ID}-seeder",
            "StackId": event["StackId"],
            "RequestId": event["RequestId"],
            "LogicalResourceId": event["LogicalResourceId"],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        event["ResponseURL"],
        data=response_body,
        method="PUT",
        headers={"Content-Type": "", "Content-Length": str(len(response_body))},
    )
    with urllib.request.urlopen(request) as response:
        logger.info(f"CFN response status: {response.status}")


def seed_dynamodb_items(seed_items: list) -> None:
    """Seed the bank-clients DynamoDB table (and remove stale items)."""
    logger.info(f"Seeding {len(seed_items)} items into table {TABLE_NAME}")
    seeded_emails = set()
    for client in seed_items:
        item = {
            "user_email": {"S": client["user_email"]},
            "full_name": {"S": client["full_name"]},
            "username": {"S": client.get("username", "")},
            "nickname": {"S": client.get("nickname", "")},
            "saldo": {"N": str(client["saldo"])},
            "moneda": {"S": client.get("moneda", "COP")},
            "hyperpersonalization": {
                "M": {
                    key: {"S": str(value)}
                    for key, value in client.get("hyperpersonalization", {}).items()
                }
            },
            "credit_cards": {
                "L": [
                    {
                        "M": {
                            "franquicia": {"S": card["franquicia"]},
                            "categoria": {"S": card["categoria"]},
                            "numero": {"S": card["numero"]},
                            "estado": {"S": card["estado"]},
                        }
                    }
                    for card in client.get("credit_cards", [])
                ]
            },
        }
        dynamodb_client.put_item(TableName=TABLE_NAME, Item=item)
        seeded_emails.add(client["user_email"])

    # Remove stale items not present in the seed list anymore
    scan_result = dynamodb_client.scan(
        TableName=TABLE_NAME, ProjectionExpression="user_email"
    )
    for existing_item in scan_result.get("Items", []):
        existing_email = existing_item["user_email"]["S"]
        if existing_email not in seeded_emails:
            logger.info(f"Deleting stale item: {existing_email}")
            dynamodb_client.delete_item(
                TableName=TABLE_NAME,
                Key={"user_email": {"S": existing_email}},
            )
    logger.info("DynamoDB seeding finished successfully")


def create_cognito_users(seed_users: list, password: str) -> None:
    """Create the Cognito demo users (email + phone_number attributes)."""
    logger.info(f"Creating {len(seed_users)} Cognito demo users in {USER_POOL_ID}")
    for user in seed_users:
        try:
            cognito_client.admin_create_user(
                UserPoolId=USER_POOL_ID,
                Username=user["user_email"],
                UserAttributes=[
                    {"Name": "email", "Value": user["user_email"]},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "phone_number", "Value": user["phone_number"]},
                    {"Name": "phone_number_verified", "Value": "true"},
                    {"Name": "name", "Value": user["full_name"]},
                ],
                MessageAction="SUPPRESS",
            )
        except cognito_client.exceptions.UsernameExistsException:
            logger.info(f"User {user['user_email']} already exists (updating attrs)")
            cognito_client.admin_update_user_attributes(
                UserPoolId=USER_POOL_ID,
                Username=user["user_email"],
                UserAttributes=[
                    {"Name": "phone_number", "Value": user["phone_number"]},
                    {"Name": "phone_number_verified", "Value": "true"},
                ],
            )
        cognito_client.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=user["user_email"],
            Password=password,
            Permanent=True,
        )
    logger.info("Cognito users seeding finished successfully")


def seed_username_mappings(seed_users: list) -> None:
    """
    Seed the PERMANENT (no TTL) USERNAME<->WHATSAPP mappings in the
    auth-sessions table, in BOTH directions for easy lookups:
      - PK=USERNAME#<username> / SK=MAPPING  -> phone_number, user_email
      - PK=USER#<phone_number> / SK=MAPPING  -> username, user_email
    """
    logger.info(f"Seeding {len(seed_users)} username mappings")
    for user in seed_users:
        username = user.get("username", user["user_email"].split("@")[0])
        phone_number = user["phone_number"].replace("+", "")
        dynamodb_client.put_item(
            TableName=TABLE_NAME_AUTH_SESSIONS,
            Item={
                "PK": {"S": f"USERNAME#{username}"},
                "SK": {"S": "MAPPING"},
                "phone_number": {"S": phone_number},
                "user_email": {"S": user["user_email"]},
            },
        )
        dynamodb_client.put_item(
            TableName=TABLE_NAME_AUTH_SESSIONS,
            Item={
                "PK": {"S": f"USER#{phone_number}"},
                "SK": {"S": "MAPPING"},
                "username": {"S": username},
                "user_email": {"S": user["user_email"]},
            },
        )
    logger.info("Username mappings seeding finished successfully")


def lambda_handler(event, context):
    logger.info(f"Received CustomResource event: {json.dumps(event)}")
    try:
        request_type = event["RequestType"]
        properties = event.get("ResourceProperties", {})

        if request_type in ["Create", "Update"]:
            if properties.get("SeedItems") and TABLE_NAME:
                seed_dynamodb_items(json.loads(properties["SeedItems"]))
            if properties.get("SeedUsers") and USER_POOL_ID:
                create_cognito_users(
                    json.loads(properties["SeedUsers"]),
                    password=properties["DemoUsersPassword"],
                )
            if properties.get("SeedUsers") and TABLE_NAME_AUTH_SESSIONS:
                seed_username_mappings(json.loads(properties["SeedUsers"]))
        else:
            logger.info(f"RequestType {request_type} is a no-op (skipping)")

        send_cfn_response(event, context, "SUCCESS")
    except Exception as error:
        logger.exception(f"Error in seeder CustomResource: {error}")
        send_cfn_response(event, context, "FAILED", reason=str(error))
