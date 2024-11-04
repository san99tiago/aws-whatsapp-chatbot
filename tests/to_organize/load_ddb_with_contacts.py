# DEMO SCRIPT TO LOAD SAMPLE DATA TO DYNAMODB
import os, boto3

# TODO: Replace the items with your own data... Parametrize this script... Improve it...

items = [
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "CONTACT#1111111111",
        "contact_details": "1111111111: Rick Sanchez (Llamar para crear inventos locos)",
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "CONTACT#222222222",
        "contact_details": "222222222: Jeff Bezos (Llamar para planear el futuro de AWS)",
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "CONTACT#333333333",
        "contact_details": "333333333: Warren Buffet (Llamar para discutir ideas de Finanzas)",
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "CONTACT#444444444",
        "contact_details": "444444444: Elon Musk (Llamar para lanzar un cohete)",
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "CONTACT#555555555",
        "contact_details": "555555555: Jensen Huang (Llamar en caso de idea genial de Gen-AI)",
    },
]

# Load data to DynamoDB
deployment_environment = os.environ["DEPLOYMENT_ENVIRONMENT"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(f"aws-whatsapp-agents-data-{deployment_environment}")

for item in items:
    table.put_item(Item=item)
