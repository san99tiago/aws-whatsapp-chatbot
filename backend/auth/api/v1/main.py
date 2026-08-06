###############################################################################
# Entrypoint for the Auth API (Cognito-backed Web Portal Authentication)
###############################################################################

# Built-in imports
import os

# External imports
from mangum import Mangum
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Own imports
from auth.api.v1.routers import auth

# Environment used to dynamically load the FastAPI docs with stages
ENVIRONMENT = os.environ.get("ENVIRONMENT")
API_PREFIX = "/api/v1"


app = FastAPI(
    title="Auth API",
    description="Cognito-backed Auth API for the WhatsApp Chatbot Web Portal",
    version="v1",
    root_path=f"/{ENVIRONMENT}" if ENVIRONMENT else None,
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/docs/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=API_PREFIX)

# This is the Lambda Function's entrypoint (handler)
handler = Mangum(app)
