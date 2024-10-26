# DEMO SCRIPT TO LOAD SAMPLE DATA TO DYNAMODB
import boto3

items = [
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "DATE#2024-12-01",
        "events": [
            "7:00am - 8:00am: December payment fees",
            "8:00am - 5:00pm: Work hard in Santi's job (AWS cool stuff)",
            "5:00pm - 6:00pm: Study Gen-AI latest topics",
            "6:00pm - 10:00pm: Family time",
        ],
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "DATE#2024-12-02",
        "events": [
            "6:00am - 7:00am: Spinning Smartfit",
            "7:00am - 8:00am: Breakfast Banana with Milk",
            "8:00am - 5:00pm: Work hard in Santi's job (AWS cool stuff)",
            "5:00pm - 6:00pm: Study Architecture patterns",
            "6:00pm - 10:00pm: Family time",
        ],
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "DATE#2024-12-03",
        "events": [
            "6:00am - 7:00am: Stair Stepper Smartfit",
            "7:00am - 8:00am: Breakfast with Colombian Coffee",
            "8:00am - 5:00pm: Work hard in Santi's job (AWS cool stuff)",
            "5:00pm - 6:00pm: Study AWS latest Blogs",
            "6:00pm - 10:00pm: Family time",
        ],
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "DATE#2024-12-04",
        "events": [
            "6:00am - 7:00am: Running",
            "7:00am - 8:00am: Breakfast with Fruits",
            "8:00am - 5:00pm: Work hard in Santi's job (AWS cool stuff)",
            "5:00pm - 6:00pm: Study Design Patterns",
            "6:00pm - 10:00pm: Family time",
        ],
    },
    {
        "PK": "USER#san99tiago@gmail.com",
        "SK": "DATE#2024-12-05",
        "events": [
            "6:00am - 7:00am: Stair Stepper Smartfit",
            "7:00am - 8:00am: Breakfast with Colombian Coffee",
            "8:00am - 5:00pm: Work hard in Santi's job (AWS cool stuff)",
            "5:00pm - 6:00pm: Study Infrastructure as Code",
            "6:00pm - 10:00pm: Family time",
        ],
    },
]

# Load data to DynamoDB
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("aws-whatsapp-calendar-prod")

for item in items:
    table.put_item(Item=item)
