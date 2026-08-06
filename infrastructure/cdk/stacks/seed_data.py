################################################################################
# SAMPLE (SEED) DATA for the Bank Demo (100% FAKE/SIMULATED data). Used by the
# CustomResources that automatically populate the DynamoDB tables and the
# Cognito demo users on stack CREATE/UPDATE events.
#
# PREREQUISITE: copy <.env.example> to <.env> at the repo root and set:
#   - DEMO_USER_PHONE_NUMBER: your REAL WhatsApp number (E.164) for the main
#     demo user (must be allowlisted in your META test app).
#   - DEMO_USERS_PASSWORD: the password for ALL the Cognito demo users.
# --> The <.env> file is gitignored on purpose (personal data stays local).
################################################################################

# Built-in imports
import os


def _load_dotenv_file() -> None:
    """Minimal .env loader (repo root), without external dependencies."""
    dotenv_path = os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ),
        ".env",
    )
    if not os.path.exists(dotenv_path):
        return
    with open(dotenv_path, "r", encoding="utf-8") as dotenv_file:
        for line in dotenv_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv_file()

# Values from <.env> (with safe example defaults for tests/CI without .env)
DEMO_USER_PHONE_NUMBER = os.environ.get("DEMO_USER_PHONE_NUMBER", "+573001234567")
DEMO_USERS_PASSWORD = os.environ.get("DEMO_USERS_PASSWORD", "Password123.")


SEED_BANK_CLIENTS = [
    {
        "user_email": "santigrc@amazon.com",
        "username": "san99tiago",
        "nickname": "Santi",
        "hyperpersonalization": {
            "ciudad": "Medellin",
            "profesion": "Solutions Architect en AWS",
            "canal_preferido": "App Movil",
            "meta_financiera": "Ahorro para comprar una PlayStation 5 Pro y jugar GTA6",
            "intereses": "GenAI, musica (piano), automatizacion, gaming",
            "tono_preferido": "cercano, paisa, con emojis",
        },
        "full_name": "Santiago Garcia",
        "phone_number": DEMO_USER_PHONE_NUMBER,
        "saldo": 1500000,
        "credit_cards": [
            {
                "franquicia": "Visa",
                "categoria": "Visa Infinite",
                "numero": "**** **** **** 4512",
                "estado": "Activa",
            },
            {
                "franquicia": "Mastercard",
                "categoria": "Mastercard Black",
                "numero": "**** **** **** 9034",
                "estado": "Activa",
            },
        ],
    },
    {
        "user_email": "moni@example.com",
        "username": "moni",
        "nickname": "Moni",
        "hyperpersonalization": {
            "ciudad": "Bogota",
            "profesion": "Disenadora UX",
            "canal_preferido": "Portal Web Personas",
            "meta_financiera": "Montar su propio estudio de diseno",
            "intereses": "arte, ilustracion digital, viajes",
            "tono_preferido": "creativo y amigable",
        },
        "full_name": "Monica Perez",
        "phone_number": "+573000000002",
        "saldo": 9500000,
        "credit_cards": [
            {
                "franquicia": "Mastercard",
                "categoria": "Mastercard Gold",
                "numero": "**** **** **** 2201",
                "estado": "Activa",
            },
            {
                "franquicia": "Visa",
                "categoria": "Visa Clasica",
                "numero": "**** **** **** 7718",
                "estado": "Bloqueada temporalmente",
            },
        ],
    },
    {
        "user_email": "naz@example.com",
        "username": "naz",
        "nickname": "Naz",
        "hyperpersonalization": {
            "ciudad": "Cali",
            "profesion": "Ingeniera de Datos",
            "canal_preferido": "App Movil",
            "meta_financiera": "Pagar una maestria en Inteligencia Artificial",
            "intereses": "analitica, lectura, ciclismo",
            "tono_preferido": "directo y tecnico",
        },
        "full_name": "Naz Torres",
        "phone_number": "+573000000003",
        "saldo": 27000000,
        "credit_cards": [
            {
                "franquicia": "Mastercard",
                "categoria": "Mastercard Platinum",
                "numero": "**** **** **** 5590",
                "estado": "Activa",
            },
        ],
    },
    {
        "user_email": "ana@example.com",
        "username": "ana",
        "nickname": "Ana",
        "hyperpersonalization": {
            "ciudad": "Cartagena",
            "profesion": "Chef",
            "canal_preferido": "Banca Telefonica",
            "meta_financiera": "Comprar un food truck",
            "intereses": "gastronomia, playa, emprendimiento",
            "tono_preferido": "alegre y cercano",
        },
        "full_name": "Ana Maria Rojas",
        "phone_number": "+573000000004",
        "saldo": 15400000,
        "credit_cards": [
            {
                "franquicia": "Visa",
                "categoria": "Visa Gold",
                "numero": "**** **** **** 6604",
                "estado": "Activa",
            },
        ],
    },
    {
        "user_email": "pablo@example.com",
        "username": "pablo",
        "nickname": "Pablo",
        "hyperpersonalization": {
            "ciudad": "Medellin",
            "profesion": "Experto en DevEx (Developer Experience)",
            "canal_preferido": "App Movil",
            "meta_financiera": "Compra de apartamento en Dubai",
            "intereses": "DevEx, platform engineering, automatizacion CI/CD",
            "tono_preferido": "tecnico y cercano",
        },
        "full_name": "Pablo Gomez",
        "phone_number": "+573000000005",
        "saldo": 62000000,
        "credit_cards": [
            {
                "franquicia": "Visa",
                "categoria": "Visa Signature",
                "numero": "**** **** **** 8823",
                "estado": "Activa",
            },
            {
                "franquicia": "Mastercard",
                "categoria": "Mastercard Gold",
                "numero": "**** **** **** 3147",
                "estado": "Activa",
            },
        ],
    },
]
