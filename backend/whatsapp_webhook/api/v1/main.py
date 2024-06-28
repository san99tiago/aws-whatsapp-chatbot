###############################################################################
# Entrypoint for the WhatsApp Chatbot Webhook Core Functionalities
###############################################################################

# Built-in imports
import os

# External imports
from mangum import Mangum
from fastapi import FastAPI

# Own imports
from whatsapp_webhook.api.v1.routers import webhook

# Environment used to dynamically load the FastAPI docs with stages
ENVIRONMENT = os.environ.get("ENVIRONMENT")
API_PREFIX = "/api/v1"


app = FastAPI(
    title="WhatsApp Chatbot API",
    description="Custom built API by Santi to interact with the WhatsApp Chatbot",
    version="v1",
    root_path=f"/{ENVIRONMENT}" if ENVIRONMENT else None,
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/docs/openapi.json",
)


app.include_router(webhook.router, prefix=API_PREFIX)

# This is the Lambda Function's entrypoint (handler)
handler = Mangum(app)
