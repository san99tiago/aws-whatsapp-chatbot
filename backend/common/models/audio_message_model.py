from typing import Optional

from common.models.message_base_model import MessageBaseModel


class AudioMessageModel(MessageBaseModel):
    """
    Class that represents a Chat Message item with AUDIO (e.g. voice notes).
    All additional attributes are inherited from the MessageBaseModel.

    Attributes:
        audio_id: str: META media ID of the audio (fetched later in the SM).
        mime_type: Optional(str): MIME type reported by META (e.g. audio/ogg).
        voice: Optional(bool): Whether the audio is a WhatsApp voice note.
    """

    audio_id: str
    mime_type: Optional[str] = None
    voice: Optional[bool] = None

    @classmethod
    def from_dynamodb_item(cls, dynamodb_item: dict) -> "AudioMessageModel":
        return cls(
            PK=dynamodb_item["PK"]["S"],
            SK=dynamodb_item["SK"]["S"],
            from_number=dynamodb_item["from_number"]["S"],
            whatsapp_id=dynamodb_item["whatsapp_id"]["S"],
            created_at=dynamodb_item["created_at"]["S"],
            whatsapp_timestamp=dynamodb_item["whatsapp_timestamp"]["S"],
            type=dynamodb_item["type"]["S"],
            audio_id=dynamodb_item["audio_id"]["S"],
            mime_type=dynamodb_item.get("mime_type", {}).get("S"),
            voice=dynamodb_item.get("voice", {}).get("BOOL"),
            correlation_id=dynamodb_item.get("correlation_id", {}).get("S"),
        )
