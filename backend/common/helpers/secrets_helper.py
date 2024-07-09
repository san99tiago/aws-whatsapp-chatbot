# Built-in imports
import json
import boto3
from typing import Union, Optional

# External imports
from botocore.exceptions import ClientError

# Own imports
from common.logger import custom_logger

logger = custom_logger()


class SecretsHelper:
    """Custom Secrets Manager Helper for simplifying secret's retrieval."""

    def __init__(self, secret_name: str) -> None:
        """
        :param secret_name (str): Name of the secret to fetch.
        """
        self.secret_name = secret_name
        self.client_sm = boto3.client("secretsmanager")

    def get_secret_value(self, key_name: Optional[str] = None) -> Union[str, None]:
        """
        Obtain the AWS Secret value based on a given key.
        :param key_name Optional(str): Key name to fetch from the JSON secret.
        """
        try:
            secret_value = self.client_sm.get_secret_value(SecretId=self.secret_name)
            logger.info(f"Successfully retrieved the AWS Secret: {self.secret_name}")
            self.json_secret = json.loads(secret_value["SecretString"])
            logger.debug("Successfully obtained the SecretString value.")
            # Return value or intentional KeyError if the key is not present
            return self.json_secret[key_name] if key_name else self.json_secret
        except ClientError as e:
            logger.exception(f"Error in pulling the AWS Secret: {self.secret_name}")
            logger.exception(f"Error details: {str(e)}")
            raise e
