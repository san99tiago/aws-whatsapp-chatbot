# DEMO SCRIPT TO LOAD SAMPLE DATA TO DYNAMODB
import os, boto3

# TODO: Replace the items with your own data... Parametrize this script... Improve it...

items = [
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "TODO#1",
        "todo_details": "Armar el arbolito de navidad comiendo natilla y buñuelo",
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "TODO#2",
        "todo_details": "Programar la próxima certificación de AWS",
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "TODO#3",
        "todo_details": "Actualizar mi sitio web (san99tiago.com)",
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "TODO#4",
        "todo_details": "Ir a la piedra del Peñol con mi familia",
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "TODO#5",
        "todo_details": "Poner música de diciembre (Rodolfo Aicardi, Pastol López, Los Hispanos, Lisandro Meza)",
    },
]

# Load data to DynamoDB
deployment_environment = os.environ["DEPLOYMENT_ENVIRONMENT"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(f"aws-whatsapp-agents-data-{deployment_environment}")

for item in items:
    table.put_item(Item=item)
