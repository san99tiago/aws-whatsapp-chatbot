from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TextModel(BaseModel):
    body: str


class ContextModel(BaseModel):
    message_id: Optional[str] = None


class MetaPostMessageModel(BaseModel):
    """
    Class that represents the Model for sending messages via POST request to META API.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messaging_product": "whatsapp",
                "to": "to_phone_number",
                "type": "text",
                "text": {"body": "text_message"},
                "context": {"message_id": "original_message_id"},
            }
        }
    )

    messaging_product: str = Field(default="whatsapp")
    to: str
    type: str = Field(default="text")
    text: TextModel
    context: Optional[ContextModel] = None
