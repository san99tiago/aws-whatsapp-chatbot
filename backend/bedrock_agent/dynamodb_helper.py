# Built-in imports
import os
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# TODO: Enhance code to be production grade. This is just a POC
# (Add logger, add error handling, add optimizations, etc...)

TABLE_NAME = os.environ.get("TABLE_NAME")
dynamodb_resource = boto3.resource("dynamodb")
table = dynamodb_resource.Table(TABLE_NAME)


def query_dynamodb_pk_sk(partition_key: str, sort_key_portion: str) -> list[dict]:
    """
    Function to run a query against DynamoDB with partition key and the sort
    key with <begins-with> functionality on it.
    :param partition_key (str): partition key value.
    :param sort_key_portion (str): sort key portion to use in query.
    """
    print(
        f"Starting query_dynamodb_pk_sk with "
        f"pk: ({partition_key}) and sk: ({sort_key_portion})"
    )

    all_items = []
    try:
        # The structure key for a single-table-design "PK" and "SK" naming
        key_condition = Key("PK").eq(partition_key) & Key("SK").begins_with(
            sort_key_portion
        )
        limit = 50

        # Initial query before pagination
        response = table.query(
            KeyConditionExpression=key_condition,
            Limit=limit,
        )
        if "Items" in response:
            all_items.extend(response["Items"])

        # Pagination loop for possible following queries
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=key_condition,
                Limit=limit,
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            if "Items" in response:
                all_items.extend(response["Items"])

        return all_items
    except ClientError as error:
        print(
            f"query operation failed for: "
            f"table_name: {TABLE_NAME}."
            f"pk: {partition_key}."
            f"sort_key_portion: {sort_key_portion}."
            f"error: {error}."
        )
        raise error
