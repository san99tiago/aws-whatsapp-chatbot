################################################################################
# Unit tests for the Strands Agent bank tools (DynamoDB-backed + mocked).
################################################################################

# External imports
import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def mock_bank_clients_table(aws_credentials, monkeypatch):
    """Create the mocked bank-clients DynamoDB table with one sample client."""
    with mock_aws():
        dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
        dynamodb_client.create_table(
            TableName="test-bank-clients-table",
            KeySchema=[{"AttributeName": "user_email", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "user_email", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        dynamodb_client.put_item(
            TableName="test-bank-clients-table",
            Item={
                "user_email": {"S": "santigrc@amazon.com"},
                "full_name": {"S": "Santiago Garcia"},
                "username": {"S": "san99tiago"},
                "nickname": {"S": "Santi"},
                "hyperpersonalization": {
                    "M": {
                        "ciudad": {"S": "Medellin"},
                        "tono_preferido": {"S": "cercano, paisa, con emojis"},
                    }
                },
                "saldo": {"N": "1500000"},
                "moneda": {"S": "COP"},
                "credit_cards": {
                    "L": [
                        {
                            "M": {
                                "franquicia": {"S": "Visa"},
                                "categoria": {"S": "Visa Infinite"},
                                "numero": {"S": "**** **** **** 4512"},
                                "estado": {"S": "Activa"},
                            }
                        }
                    ]
                },
            },
        )

        from tools import bank_tools

        monkeypatch.setattr(bank_tools, "TABLE_NAME", "test-bank-clients-table")
        yield bank_tools


class TestBankTools:
    def test_consultar_saldo_returns_balance(self, mock_bank_clients_table):
        result = mock_bank_clients_table.consultar_saldo("santigrc@amazon.com")
        assert result["saldo"] == 1500000
        assert result["moneda"] == "COP"
        assert result["nombre"] == "Santiago Garcia"

    def test_consultar_saldo_unknown_user_returns_error(self, mock_bank_clients_table):
        result = mock_bank_clients_table.consultar_saldo("unknown@example.com")
        assert "error" in result

    def test_consultar_tarjetas_returns_cards(self, mock_bank_clients_table):
        result = mock_bank_clients_table.consultar_estado_tarjeta_credito(
            "santigrc@amazon.com"
        )
        assert len(result["tarjetas_credito"]) == 1
        assert result["tarjetas_credito"][0]["franquicia"] == "Visa"
        assert result["tarjetas_credito"][0]["estado"] == "Activa"

    def test_consulta_canales_returns_channels(self, mock_bank_clients_table):
        result = mock_bank_clients_table.consulta_canales_bancarios()
        assert len(result["canales"]) == 5
        assert any(c["estado"] == "Healthy" for c in result["canales"])

    def test_obtener_perfil_returns_hyperpersonalization(self, mock_bank_clients_table):
        result = mock_bank_clients_table.obtener_perfil_usuario("santigrc@amazon.com")
        assert result["nombre"] == "Santiago Garcia"
        assert result["nickname"] == "Santi"
        assert result["username"] == "san99tiago"
        assert result["hiperpersonalizacion"]["ciudad"] == "Medellin"

    def test_obtener_perfil_unknown_user_returns_error(self, mock_bank_clients_table):
        result = mock_bank_clients_table.obtener_perfil_usuario("unknown@example.com")
        assert "error" in result
