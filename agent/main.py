################################################################################
# ENTRYPOINT for the "DemoAgent" (Financial Bank Agent) on AgentCore Runtime.
# --> Deployed via DIRECT CODE DEPLOY (ZIP), no Docker image required.
# --> To convert this into ANY other type of agent, see README.md section
#     "Customize the Agent" (update SYSTEM_PROMPT, tools and model as needed).
################################################################################

# Built-in imports
import json
import logging
import os

# External imports
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel

# Own imports
from tools.bank_tools import (
    consultar_saldo,
    consultar_estado_tarjeta_credito,
    consulta_canales_bancarios,
    obtener_perfil_usuario,
)

# Extra logging in DEBUG mode (AgentCore Runtime logs land in CloudWatch)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("demo-agent")
logger.setLevel(LOG_LEVEL)

# Configurations injected by CDK as AgentCore Runtime environment variables
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-5")
BOT_NAME = os.environ.get("BOT_NAME", "SantiBank Assistant")
LANGUAGE = os.environ.get("LANGUAGE", "SPANISH")

SYSTEM_PROMPT = f"""
Eres '{BOT_NAME}', el Agente Financiero de un banco (demo generica de banco).
Debes responder siempre de forma amable, profesional y concisa, en {LANGUAGE}.
Puedes utilizar diferentes herramientas (tools) para dar respuesta autonoma al usuario:
consultar su saldo, consultar el estado de sus tarjetas de credito y consultar el
estado de los canales del banco.
Usa las herramientas solo cuando sean necesarias para responder la pregunta del usuario.
Cuando entregues valores de dinero, formatealos en pesos colombianos (COP) de forma
legible (ej: $1.500.000 COP).
IMPORTANTE: responde SIEMPRE en texto plano compatible con WhatsApp (sin markdown:
nada de asteriscos dobles, tablas con barras, ni numerales). Para listas usa guiones
o emojis y saltos de linea.
Si el usuario pregunta algo fuera del contexto bancario, responde amablemente y
orientalo de vuelta a los servicios del banco.
"""

INCOGNITO_NOTE = """
El usuario actual NO esta autenticado (usuario incognito/invitado). Solo tienes
acceso a herramientas publicas (estado de canales del banco). Si el usuario pide
informacion personal (saldo, tarjetas), indicale amablemente que debe autenticarse
primero en el portal web de autenticacion para habilitar esas funciones.
"""

app = BedrockAgentCoreApp()


def _build_profile_note(profile: dict) -> str:
    """Helper to build the hyperpersonalization note from the user's profile."""
    if not profile:
        return ""
    hyperpersonalization = profile.get("hyperpersonalization", {}) or {}
    details = "; ".join(
        f"{key}: {value}" for key, value in hyperpersonalization.items()
    )
    return (
        "\nPERFIL DEL USUARIO (hiperpersonalizacion, cargado automaticamente): "
        f"nombre: {profile.get('full_name', '')}; "
        f"nickname: {profile.get('nickname', '')}; "
        f"{details}.\n"
        "USA estos datos para personalizar el saludo (llamalo por su nickname), "
        "el tono y las recomendaciones de la conversacion."
    )


def _build_agent(authenticated: bool, username: str, profile: dict) -> Agent:
    """Helper to build the Strands Agent with tools based on the auth status."""
    model = BedrockModel(model_id=BEDROCK_MODEL_ID)
    profile_note = _build_profile_note(profile)

    if authenticated:
        # Authenticated users get the FULL set of bank tools
        tools = [
            consultar_saldo,
            consultar_estado_tarjeta_credito,
            consulta_canales_bancarios,
            obtener_perfil_usuario,
        ]
        system_prompt = (
            f"{SYSTEM_PROMPT}\n"
            f"El correo del usuario autenticado es {username}: usalo como parametro "
            f"user_email en las herramientas que lo requieran."
            f"{profile_note}"
        )
    else:
        # Incognito users only get the PUBLIC subset of tools
        tools = [consulta_canales_bancarios]
        system_prompt = f"{SYSTEM_PROMPT}\n{INCOGNITO_NOTE}{profile_note}"

    return Agent(model=model, system_prompt=system_prompt, tools=tools)


@app.entrypoint
def invoke(payload: dict, context=None) -> dict:
    """
    AgentCore Runtime entrypoint (API-Contract).

    Expected JSON request payload:
    {
        "prompt": "<user message>",
        "metadata": {
            "authenticated": "true" | "false",
            "username": "<username-or-email>",
            "phone_number": "<whatsapp-phone-number>",
            "correlation_id": "<traceability-id>",
            "channel": "whatsapp"
        }
    }

    JSON response contract:
    {
        "response": "<agent text response>",
        "metadata": { ...same metadata echoed back... }
    }
    """
    logger.debug("Received payload: %s", json.dumps(payload, default=str))

    prompt = payload.get("prompt", "")
    metadata = payload.get("metadata", {}) or {}
    authenticated = str(metadata.get("authenticated", "false")).lower() == "true"
    username = metadata.get("username", "incognito")
    profile = metadata.get("profile", {}) or {}

    logger.info(
        "Invoking DemoAgent (authenticated=%s, username=%s, profile=%s, model=%s)",
        authenticated,
        username,
        bool(profile),
        BEDROCK_MODEL_ID,
    )

    agent = _build_agent(
        authenticated=authenticated, username=username, profile=profile
    )
    result = agent(prompt)
    response_text = str(result)

    logger.debug("Agent response: %s", response_text)

    return {
        "response": response_text,
        "metadata": {
            **metadata,
            "authenticated": str(authenticated).lower(),
            "username": username,
            "model_id": BEDROCK_MODEL_ID,
        },
    }


if __name__ == "__main__":
    app.run()
