from typing import Optional
from pydantic import BaseModel, Field


class MessageBaseModel(BaseModel):
    """
    Class that represents a Chat Message item (Base Model).

    Attributes:
        PK: str: Primary Key for the DynamoDB item (NUMBER#<phone_number>)
        SK: str: Sort Key for the DynamoDB item (MESSAGE#<datetime>)
        from_number: str: Phone number of the sender.
        created_at: str: Creation datetime of the message.
        type: str: Type of message (text, image, video, etc).
        whatsapp_id: str: WhatsApp ID of the message.
        whatsapp_timestamp: str: WhatsApp timestamp of the message.
        correlation_id: Optional(str): Correlation ID for the message.
    """

    PK: str = Field(pattern=r"^NUMBER#\d{10,13}$")
    SK: str = Field(pattern=r"^MESSAGE#")
    created_at: str
    from_number: str
    type: str
    whatsapp_id: str
    whatsapp_timestamp: str
    correlation_id: Optional[str] = None

    @classmethod
    def from_dynamodb_item(cls, dynamodb_item: dict) -> "MessageBaseModel":
        return cls(
            PK=dynamodb_item["PK"]["S"],
            SK=dynamodb_item["SK"]["S"],
            from_number=dynamodb_item["from_number"]["S"],
            whatsapp_id=dynamodb_item["whatsapp_id"]["S"],
            created_at=dynamodb_item["created_at"]["S"],
            whatsapp_timestamp=dynamodb_item["whatsapp_timestamp"]["S"],
            type=dynamodb_item["type"]["S"],
            correlation_id=dynamodb_item.get("correlation_id", {}).get("S"),
        )
