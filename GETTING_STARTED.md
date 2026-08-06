# :rocket: GETTING STARTED

Step-by-step guide to deploy AWS-WHATSAPP-AGENTCORE-BACKEND (WhatsApp + AgentCore + Strands + optional Cognito Auth Portal) from ZERO.

## 1. Prerequisites (Tools)

| Tool       | Version            | Notes                                    |
| ---------- | ------------------ | ---------------------------------------- |
| Python     | 3.12+ (3.13 ideal) | Lambdas and AgentCore run Python 3.13    |
| Poetry     | 2.x                | Dependency management (`.venv` at root)  |
| Node.js    | 20+                | Required by the AWS CDK CLI              |
| AWS CDK    | 2.x (latest)       | `npm install -g aws-cdk`                 |
| AWS CLI    | 2.x                | With valid credentials for your account  |
| Draw.io    | (optional)         | To edit the architecture diagram         |

```bash
# Install project dependencies (Poetry with .venv at the repo root)
poetry config virtualenvs.in-project true
poetry install
```

## 2. Prerequisite: META (WhatsApp Business) Account

Follow the detailed guide in [docs/WHATSAPP_CONFIGURATION.md](./docs/WHATSAPP_CONFIGURATION.md). Summary:

1. Create a [Meta for Developers](https://developers.facebook.com/) account.
2. Create a **Business App** with the **WhatsApp** product enabled.
3. Get the **Phone Number ID** (sender) from the WhatsApp API Setup page.
4. Create a **System User** (Business Settings) with a **permanent token** that has the `whatsapp_business_messaging` and `whatsapp_business_management` permissions.
5. Keep at hand: `META_TOKEN` (permanent token) and `META_FROM_PHONE_NUMBER_ID`.

> The WebHook subscription (step 6 below) is configured AFTER the first deployment, because you need the API endpoint.

## 3. Prerequisite: AWS Secret (MANUAL - FIRST PROCESS PREREQUISITE)

The solution fetches its credentials at runtime from AWS Secrets Manager. The secret MUST exist **BEFORE the first deployment** and MUST be created **MANUALLY** with name **`/prod/aws-whatsapp-chatbot`**:

```bash
aws secretsmanager create-secret \
  --name "/prod/aws-whatsapp-chatbot" \
  --description "Credentials for the WhatsApp Chatbot (META + API verify token)" \
  --secret-string '{
    "AWS_API_KEY_TOKEN": "<YOUR-RANDOM-VERIFY-TOKEN-FOR-META-WEBHOOK>",
    "META_TOKEN": "<YOUR-META-PERMANENT-SYSTEM-USER-TOKEN>",
    "META_FROM_PHONE_NUMBER_ID": "<YOUR-META-PHONE-NUMBER-ID>"
  }'
```

| Key                         | Purpose                                                                |
| --------------------------- | ---------------------------------------------------------------------- |
| `AWS_API_KEY_TOKEN`         | Verify token for the META WebHook GET verification (you invent it)     |
| `META_TOKEN`                | Permanent System User token (Bearer for the Graph API)                 |
| `META_FROM_PHONE_NUMBER_ID` | Phone Number ID used as sender in the `/{id}/messages` endpoint        |

> The secret name is configured in `infrastructure/cdk.json` (`secret_name` key).

## 4. Prerequisite: Route53 Hosted Zone (Custom DNS) - MANDATORY

⚠️ **You MUST own a Route53 Hosted Zone in your AWS account.** ALL the endpoints of this solution (META WebHook API, Auth Portal, Auth API) are exposed via custom DNS with ACM certificates, so the deployment FAILS without a valid zone.

**REPLACE the DNS values in `infrastructure/cdk.json` (both `dev` and `prod` blocks) with YOUR OWN zone BEFORE deploying:**

| Key in `cdk.json` | Default (author's values - replace them!) | Your value |
| --- | --- | --- |
| `hosted_zone_name`      | `cb.events.genai.aws.dev` | Your Route53 zone name (e.g. `mydomain.com`) |
| `hosted_zone_id`        | `Z0422199173AVFEWSD3SF`   | Your zone ID (Route53 console > Hosted zones) |
| `api_webhook_subdomain` | `wpp-api-webhook-aws`     | (Optional) subdomain for the WebHook API |
| `auth_portal_subdomain` | `web-portal-auth`         | (Optional) subdomain for the Auth Portal |

The resulting endpoints will be:

- WebHook API: `https://<api_webhook_subdomain>.<hosted_zone_name>/api/v1/webhook`
- Auth Portal: `https://<auth_portal_subdomain>.<hosted_zone_name>`
- Auth API: `https://<auth_portal_subdomain>-api.<hosted_zone_name>`

> The defaults are the author's own zone and will NOT work in your account. Find your zone ID with: `aws route53 list-hosted-zones --query "HostedZones[].{Name:Name,Id:Id}"`

> Don't have a domain yet? Register one in [Route53](https://console.aws.amazon.com/route53/home#DomainRegistration) or delegate an existing domain to a new Route53 Hosted Zone.

## 5. Prerequisite: Bedrock Model Access

Enable **Anthropic Claude Sonnet 5** in the [Bedrock console](https://console.aws.amazon.com/bedrock) (Model access). The solution uses the cross-region inference profile `us.anthropic.claude-sonnet-5` (configurable via `bedrock_model_id` in `cdk.json`).

## 6. Configuration (cdk.json)

ALL configurations live in `infrastructure/cdk.json` under `app_config` (per environment `dev`/`prod`):

| Key                          | Description                                                     |
| ---------------------------- | --------------------------------------------------------------- |
| `bedrock_model_id`           | Bedrock model (inference profile) for the Strands Agent         |
| `auth_enabled`               | `true` deploys the Cognito Auth Portal; `false` bypasses auth   |
| `secret_name`                | AWS Secret with META credentials (manual prerequisite)          |
| `meta_api_version`           | META Graph API version (e.g. `v26.0`)                           |
| `hosted_zone_name/id`        | Route53 zone for the custom DNS (MANDATORY: replace with YOURS) |
| `api_webhook_subdomain`      | Subdomain for the WebHook API                                   |
| `auth_portal_subdomain`      | Subdomain for the Auth Portal (portal + `-api` for the Auth API)|
| `table_name_*`               | DynamoDB table base names                                       |
| `auth_session_ttl_seconds`   | Auth session TTL (default 600 = 10 minutes)                     |

> The Cognito demo users + bank data (100% fake/simulated) are seeded automatically by CustomResources from `infrastructure/cdk/stacks/seed_data.py`.

## 6.1. Prerequisite: Local `.env` file (PERSONAL DATA - BEFORE DEPLOYING)

The personal/sensitive demo values do NOT live in the repo. Copy the example file and set YOUR values **BEFORE the deployment** (the Data Seeder reads them at synth/deploy time):

```bash
cp .env.example .env
# Then edit <.env> with your REAL values:
# DEMO_USER_PHONE_NUMBER=+57XXXXXXXXXX   <- your REAL WhatsApp number (E.164, allowlisted in META)
# DEMO_USERS_PASSWORD=YourStrongPassword <- password for ALL Cognito demo users
```

> The `.env` file is gitignored on purpose: NEVER commit it. Without it, safe example defaults are used (`.env.example` values), which will NOT deliver WhatsApp messages to a real phone.

## 7. Deployment

```bash
# 1. Bootstrap CDK (only once per account/region)
cdk bootstrap

# 2. Build layers + agent ZIP package, synth and deploy (prod is the default env)
poetry run poe synth
poetry run poe deploy

# Or with an explicit environment:
cd infrastructure
DEPLOYMENT_ENVIRONMENT=prod cdk deploy --all --require-approval never
```

The deploy creates 3 stacks (Auth Portal only when `auth_enabled=true`):

1. `agentcore-aws-wpp-prod-stack`
2. `aws-wpp-chatbot-api-prod`
3. `aws-wpp-auth-portal-prod`

## 8. Configure the META WebHook (After First Deploy)

1. In the Meta App dashboard, go to **WhatsApp > Configuration > Webhook**.
2. Callback URL: `https://wpp-api-webhook-aws.cb.events.genai.aws.dev/api/v1/webhook`
3. Verify token: the `AWS_API_KEY_TOKEN` value from your secret.
4. Click **Verify and save** (META sends the GET verification request).
5. Subscribe to the **messages** webhook field.
6. **CRITICAL (easy to miss!)**: subscribe your App to the WhatsApp Business Account (WABA). The dashboard "Test" button and the field toggles work WITHOUT this step, but REAL messages are NOT delivered until you run:

   ```bash
   curl -X POST "https://graph.facebook.com/v26.0/<WABA_ID>/subscribed_apps" \
     -H "Authorization: Bearer <META_TOKEN>"
   # Verify your app appears in the list:
   curl "https://graph.facebook.com/v26.0/<WABA_ID>/subscribed_apps" \
     -H "Authorization: Bearer <META_TOKEN>"
   ```

   The `WABA_ID` is shown in the Meta dashboard under **Step 1. Try it out** (WhatsApp Business Account ID).

## 9. Validation

```bash
# Unit tests
poetry run poe test-unit

# Simulate the META WebHook GET verification (fetching the real secret)
TOKEN=$(aws secretsmanager get-secret-value --secret-id /prod/aws-whatsapp-chatbot \
  --query SecretString --output text | python3 -c "import json,sys; print(json.load(sys.stdin)['AWS_API_KEY_TOKEN'])")
curl -s "https://wpp-api-webhook-aws.cb.events.genai.aws.dev/api/v1/webhook?hub.mode=subscribe&hub.challenge=test-challenge-123&hub.verify_token=${TOKEN}"
# Expected: test-challenge-123

# Simulate the META WebHook POST callback (text message event)
curl -s -X POST "https://wpp-api-webhook-aws.cb.events.genai.aws.dev/api/v1/webhook" \
  -H "Content-Type: application/json" \
  -d '{"object":"whatsapp_business_account","entry":[{"id":"1","changes":[{"value":{"messaging_product":"whatsapp","messages":[{"from":"573001112233","id":"wamid.TEST","timestamp":"1722800000","text":{"body":"Hola!"},"type":"text"}]},"field":"messages"}]}]}'
# Expected: {"message":"ok","details":"Received message"}
```

Then send a real WhatsApp message to your META phone number and watch the magic (CloudWatch logs in DEBUG mode for full traceability).

## 10. Demo Flow

1. Send "Hola" to the bot -> receive the auth prompt (login link OR continue incognito).
2. Option A (Incognito): send any question -> agent answers with PUBLIC tools only (bank channels status).
3. Option B (Login): open `https://web-portal-auth.cb.events.genai.aws.dev`, login with a demo user (e.g. `santigrc@amazon.com` and the `DEMO_USERS_PASSWORD` you set in your `.env`) -> receive the WhatsApp confirmation -> now ask "¿Cuál es mi saldo?" or "¿Cómo están mis tarjetas?" (FULL toolset for 10 minutes).

## Troubleshooting

- **`Secrets Manager can't find the specified secret`**: create the secret from step 3 (manual prerequisite).
- **Certificate validation stuck**: verify the Hosted Zone is resolvable and the `hosted_zone_id` is correct.
- **Agent errors**: check the AgentCore Runtime logs in CloudWatch (`/aws/bedrock-agentcore/...`) and the State Machine execution logs (`/aws/vendedlogs/states/aws-wpp-{env}`).
- **`AccessDeniedException` invoking the model**: enable Claude Sonnet 5 model access in Bedrock (step 5).

## LICENSE

Copyright 2026 Santiago Garcia Arango.
