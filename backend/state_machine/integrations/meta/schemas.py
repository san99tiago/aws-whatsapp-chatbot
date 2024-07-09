from typing import Optional
from pydantic import BaseModel, Field


class TextModel(BaseModel):
    body: str


class ContextModel(BaseModel):
    message_id: Optional[str] = None


class MetaPostMessageModel(BaseModel):
    """
    Class that represents the Model for sending messages via POST request to META API.
    """

    messaging_product: str = Field(default="whatsapp")
    to: str = Field(..., example="+12345678987")
    type: str = Field(default="text")
    text: TextModel
    context: Optional[ContextModel] = None

    class Config:
        json_schema_extra = {
            "example": {
                "messaging_product": "whatsapp",
                "to": "to_phone_number",
                "type": "text",
                "text": {"body": "text_message"},
                "context": {"message_id": "original_message_id"},
            }
        }
