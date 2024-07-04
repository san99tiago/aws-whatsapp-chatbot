from enum import Enum


class WhatsAppMessageTypes(Enum):
    """Class that represents the different types of WhatsApp messages."""

    TEXT: str = "text"
    IMAGE: str = "image"
    VIDEO: str = "video"
    VOICE: str = "voice"


# TODO: Actually use these prefixes for my DynamoDB Table Single Table Design
class DDBPrefixes(Enum):
    """
    Enumerations for DynamoDB Partition Keys and Sort Keys for whatsapp
    conversations and chats.
    """

    PK_NUMBER = "NUMBER#"
    SK_NUMBER_DATA = "NUMBER#"
    SK_CHAT_INPUT = "CHAT#INPUT#"
    SK_CHAT_OUTPUT = "CHAT#OUTPUT#"
