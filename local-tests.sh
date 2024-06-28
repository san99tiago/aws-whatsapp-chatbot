#!/bin/bash

# SCRIPT TO RUN LOCAL TESTS/VALIDATIONS OF THE API

# Run the API (FastAPI server)
cd backend
LOG_LEVEL=DEBUG uvicorn whatsapp_webhook.api.v1.main:app --host 0.0.0.0 --port 9999 --reload
