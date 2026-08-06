################################################################################
# BANK TOOLS for the "DemoAgent" (Financial Bank Agent) as Strands @tool(s).
# --> Migrated from AWS Lambda Functions (Bedrock Function Calling demos) to
#     DIRECT Python tools running inside the AgentCore Runtime.
################################################################################

# Built-in imports
import logging
import os

# External imports
import boto3
from strands import tool

logger = logging.getLogger("demo-agent.tools")

# DynamoDB table with the bank clients sample data (seeded via CDK CustomResource)
TABLE_NAME = os.environ.get("TABLE_NAME", "aws-wpp-bank-clients-prod")

# Public (mocked) bank channels status for the generic bank demo
CHANNELS_STATUS = {
    "canales": [
        {"canal": "App-Movil", "estado": "Healthy"},
        {"canal": "Portal-Web-Personas", "estado": "Healthy"},
        {"canal": "Portal-Web-Negocios", "estado": "Healthy"},
        {"canal": "Banca-Telefonica", "estado": "Healthy"},
        {"canal": "Sucursales-Fisicas", "estado": "Intermitencias"},
    ],
    "fuente": "Strands @tool (consulta_canales_bancarios)",
}


def _get_dynamodb_client():
    """Helper to lazily create the DynamoDB client (simplifies unit testing)."""
    return boto3.client("dynamodb")


def _get_bank_client_item(user_email: str) -> dict:
    """Helper to fetch a bank client item from DynamoDB by user_email."""
    logger.debug("Fetching bank client item for user_email=%s", user_email)
    result = _get_dynamodb_client().get_item(
        TableName=TABLE_NAME,
        Key={"user_email": {"S": user_email}},
    )
    return result.get("Item", {})


# TODO SANTI - Evaluate migration to AgentCore MCP GW Approach
@tool
def consultar_saldo(user_email: str) -> dict:
    """
    Consulta el saldo disponible de la cuenta bancaria del usuario autenticado.
    Usa esta herramienta cuando el usuario pregunte por su saldo, plata disponible
    o dinero en su cuenta.

    Args:
        user_email: Correo del usuario autenticado (ej: santigrc@amazon.com)

    Returns:
        dict: Informacion del saldo del usuario (usuario, nombre, saldo, moneda).
    """
    item = _get_bank_client_item(user_email)
    if not item:
        return {"error": f"No se encontro informacion bancaria para {user_email}"}

    return {
        "usuario": item["user_email"]["S"],
        "nombre": item["full_name"]["S"],
        "saldo": int(item["saldo"]["N"]),
        "moneda": item.get("moneda", {}).get("S", "COP"),
        "fuente": "Strands @tool (consultar_saldo)",
    }


# TODO SANTI - Evaluate migration to AgentCore MCP GW Approach
@tool
def consultar_estado_tarjeta_credito(user_email: str) -> dict:
    """
    Consulta el estado de las tarjetas de credito del usuario autenticado
    (franquicia, categoria, numero enmascarado y estado). Usa esta herramienta
    cuando el usuario pregunte por sus tarjetas de credito o el estado de alguna.

    Args:
        user_email: Correo del usuario autenticado (ej: santigrc@amazon.com)

    Returns:
        dict: Tarjetas de credito del usuario (usuario, nombre, tarjetas_credito).
    """
    item = _get_bank_client_item(user_email)
    if not item:
        return {"error": f"No se encontraron tarjetas para {user_email}"}

    cards = [
        {
            "franquicia": card["M"]["franquicia"]["S"],
            "categoria": card["M"]["categoria"]["S"],
            "numero": card["M"]["numero"]["S"],
            "estado": card["M"]["estado"]["S"],
        }
        for card in item.get("credit_cards", {}).get("L", [])
    ]
    return {
        "usuario": item["user_email"]["S"],
        "nombre": item["full_name"]["S"],
        "tarjetas_credito": cards,
        "fuente": "Strands @tool (consultar_estado_tarjeta_credito)",
    }


# TODO SANTI - Evaluate migration to AgentCore MCP GW Approach
@tool
def obtener_perfil_usuario(user_email: str) -> dict:
    """
    Obtiene el perfil (metadata) del usuario para hiperpersonalizacion:
    nombre completo, nickname y datos claves (ciudad, canal preferido, metas
    financieras, intereses y tono preferido). Usa esta herramienta cuando
    necesites personalizar la conversacion o el usuario pregunte por su perfil.

    Args:
        user_email: Correo del usuario autenticado (ej: santigrc@amazon.com)

    Returns:
        dict: Perfil del usuario (nombre, nickname, hiperpersonalizacion).
    """
    item = _get_bank_client_item(user_email)
    if not item:
        return {"error": f"No se encontro el perfil para {user_email}"}

    return {
        "usuario": item["user_email"]["S"],
        "nombre": item["full_name"]["S"],
        "nickname": item.get("nickname", {}).get("S", ""),
        "username": item.get("username", {}).get("S", ""),
        "hiperpersonalizacion": {
            key: value.get("S", "")
            for key, value in item.get("hyperpersonalization", {}).get("M", {}).items()
        },
        "fuente": "Strands @tool (obtener_perfil_usuario)",
    }


# TODO SANTI - Evaluate migration to AgentCore MCP GW Approach
@tool
def consulta_canales_bancarios() -> dict:
    """
    Consulta el estado actual de los 5 canales del banco (App Movil, Portal Web
    Personas, Portal Web Negocios, Banca Telefonica y Sucursales Fisicas).
    Usa esta herramienta cuando el usuario pregunte por el estado, disponibilidad
    o caidas de los canales del banco. No requiere parametros (herramienta publica).

    Returns:
        dict: Estado actual de los canales del banco.
    """
    logger.debug("Returning bank channels status")
    return CHANNELS_STATUS
