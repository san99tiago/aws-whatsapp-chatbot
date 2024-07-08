import pytest
from uuid import uuid4
from backend.common.models.message_base_model import MessageBaseModel
from backend.common.models.text_message_model import TextMessageModel


@pytest.fixture(scope="package")  # used for all tests
def correlation_id():
    return str(uuid4())


@pytest.fixture
def chat_message_base_model(correlation_id) -> MessageBaseModel:
    return MessageBaseModel(
        PK="NUMBER#12345678987",
        SK="MESSAGE#2024-06-19 03:41:42.269532+00:00",
        created_at="2024-06-19 03:41:42.269532+00:00",
        from_number="12345678987",
        type="text",
        whatsapp_id="wamid.DBgMATczCjA2ODI5MTg5FQICBhgUM0FCOUMzNxUxNkT2RUM2OTU5QTIA",
        whatsapp_timestamp="1718768502",
        correlation_id=correlation_id,
    )


@pytest.fixture
def chat_message_text_model(
    chat_message_base_model: MessageBaseModel,
) -> TextMessageModel:
    return TextMessageModel(
        **chat_message_base_model.model_dump(),  # All the attributes from the base model
        text="Hello by Santi!",  # Additional attribute for the text message
    )


def test_chat_message_text_model(
    chat_message_text_model: TextMessageModel, correlation_id
):
    # Check the model attributes
    assert chat_message_text_model.PK == "NUMBER#12345678987"
    assert chat_message_text_model.SK == "MESSAGE#2024-06-19 03:41:42.269532+00:00"
    assert chat_message_text_model.created_at == "2024-06-19 03:41:42.269532+00:00"
    assert chat_message_text_model.from_number == "12345678987"
    assert chat_message_text_model.type == "text"
    assert (
        chat_message_text_model.whatsapp_id
        == "wamid.DBgMATczCjA2ODI5MTg5FQICBhgUM0FCOUMzNxUxNkT2RUM2OTU5QTIA"
    )
    assert chat_message_text_model.whatsapp_timestamp == "1718768502"
    assert chat_message_text_model.correlation_id is correlation_id
    assert chat_message_text_model.text == "Hello by Santi!"

    # Check the model_dump() method
    chat_message_dict = chat_message_text_model.model_dump()
    assert chat_message_dict == {
        "PK": "NUMBER#12345678987",
        "SK": "MESSAGE#2024-06-19 03:41:42.269532+00:00",
        "created_at": "2024-06-19 03:41:42.269532+00:00",
        "from_number": "12345678987",
        "type": "text",
        "whatsapp_id": "wamid.DBgMATczCjA2ODI5MTg5FQICBhgUM0FCOUMzNxUxNkT2RUM2OTU5QTIA",
        "whatsapp_timestamp": "1718768502",
        "correlation_id": correlation_id,
        "text": "Hello by Santi!",
    }


def test_chat_message_text_model_from_dynamodb_item():
    dynamodb_item = {
        "PK": {"S": "NUMBER#12345678987"},
        "SK": {"S": "MESSAGE#2024-06-19 03:41:42.269532+00:00"},
        "created_at": {"S": "2024-06-19 03:41:42.269532+00:00"},
        "from_number": {"S": "12345678987"},
        "type": {"S": "text"},
        "text": {"S": "Hello by Santi!"},
        "whatsapp_id": {
            "S": "wamid.DBgMATczCjA2ODI5MTg5FQICBhgUM0FCOUMzNxUxNkT2RUM2OTU5QTIA"
        },
        "whatsapp_timestamp": {"S": "1718768502"},
        "correlation_id": {"S": str(uuid4())},
    }

    chat_message_instance = TextMessageModel.from_dynamodb_item(dynamodb_item)

    # Check core attributes from base model
    assert chat_message_instance.PK == "NUMBER#12345678987"
    assert chat_message_instance.SK == "MESSAGE#2024-06-19 03:41:42.269532+00:00"

    # Check additional attributes from text message model
    assert chat_message_instance.text == "Hello by Santi!"
