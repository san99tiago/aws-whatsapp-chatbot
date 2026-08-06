from enum import Enum


class WhatsAppMessageTypes(Enum):
    """Class that represents the different types of WhatsApp messages."""

    TEXT: str = "text"
    IMAGE: str = "image"
    VIDEO: str = "video"
    VOICE: str = "voice"
    AUDIO: str = "audio"


class DDBPrefixes(Enum):
    """
    Enumerations for DynamoDB Partition Keys and Sort Keys for WhatsApp
    conversations, chats and auth sessions.
    """

    PK_NUMBER = "NUMBER#"
    SK_MESSAGE = "MESSAGE#"
    PK_USER = "USER#"
    PK_USERNAME = "USERNAME#"
    SK_AUTH = "AUTH"
    SK_AUTH_PROMPTED = "AUTH#PROMPTED"
    SK_MAPPING = "MAPPING"


class StateMachineMessageTypes(Enum):
    """
    Extra (internal) message types used to route the State Machine Choice state
    (additional to the native WhatsApp message types).
    """

    AUTH_PROMPT = "auth_prompt"
