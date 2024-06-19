import pytest
from backend.whatsapp_chatbot.models.message_base_model import (
    MessageBaseModel,
)


@pytest.fixture
def chat_message_base_model() -> MessageBaseModel:
    return MessageBaseModel(
        PK="NUMBER#12345678987",
        SK="MESSAGE#2024-06-19 03:41:42.269532+00:00",
        created_at="2024-06-19 03:41:42.269532+00:00",
        from_number="12345678987",
        type="text",
        whatsapp_id="wamid.DBgMATczCjA2ODI5MTg5FQICBhgUM0FCOUMzNxUxNkT2RUM2OTU5QTIA",
        whatsapp_timestamp="1718768502",
    )


def test_chat_message_base_model(chat_message_base_model: MessageBaseModel):
    # Check the model attributes
    assert chat_message_base_model.PK == "NUMBER#12345678987"
    assert chat_message_base_model.SK == "MESSAGE#2024-06-19 03:41:42.269532+00:00"
    assert chat_message_base_model.created_at == "2024-06-19 03:41:42.269532+00:00"
    assert chat_message_base_model.from_number == "12345678987"
    assert chat_message_base_model.type == "text"
    assert (
        chat_message_base_model.whatsapp_id
        == "wamid.DBgMATczCjA2ODI5MTg5FQICBhgUM0FCOUMzNxUxNkT2RUM2OTU5QTIA"
    )
    assert chat_message_base_model.whatsapp_timestamp == "1718768502"

    # Check the model_dump() method
    chat_message_dict = chat_message_base_model.model_dump()
    assert chat_message_dict == {
        "PK": "NUMBER#12345678987",
        "SK": "MESSAGE#2024-06-19 03:41:42.269532+00:00",
        "created_at": "2024-06-19 03:41:42.269532+00:00",
        "from_number": "12345678987",
        "type": "text",
        "whatsapp_id": "wamid.DBgMATczCjA2ODI5MTg5FQICBhgUM0FCOUMzNxUxNkT2RUM2OTU5QTIA",
        "whatsapp_timestamp": "1718768502",
    }


def test_chat_message_from_dynamodb_item():
    dynamodb_item = {
        "PK": {"S": "NUMBER#12345678987"},
        "SK": {"S": "MESSAGE#2024-06-19 03:41:42.269532+00:00"},
        "created_at": {"S": "2024-06-19 03:41:42.269532+00:00"},
        "from_number": {"S": "12345678987"},
        "type": {"S": "text"},
        "whatsapp_id": {
            "S": "wamid.DBgMATczCjA2ODI5MTg5FQICBhgUM0FCOUMzNxUxNkT2RUM2OTU5QTIA"
        },
        "whatsapp_timestamp": {"S": "1718768502"},
    }

    chat_message_instance = MessageBaseModel.from_dynamodb_item(dynamodb_item)
    assert chat_message_instance.PK == "NUMBER#12345678987"
    assert chat_message_instance.SK == "MESSAGE#2024-06-19 03:41:42.269532+00:00"
