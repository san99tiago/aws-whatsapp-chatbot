# AWS CONFIGURATION

In order to correctly configure the AWS account and manual steps (only once), follow these steps.

## Configure Secrets Manager Secret (MANDATORY PREREQUISITE)

Create the AWS Secret that contains the required tokens/credentials for connecting AWS and Meta APIs. This MUST be done manually BEFORE the first deployment:

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

| Key                         | Purpose                                                             |
| --------------------------- | ------------------------------------------------------------------- |
| `AWS_API_KEY_TOKEN`         | Verify token for the META WebHook GET verification (you invent it)  |
| `META_TOKEN`                | Permanent System User token (Bearer for the META Graph API)         |
| `META_FROM_PHONE_NUMBER_ID` | Phone Number ID used as sender in the `/{id}/messages` endpoint     |

To update the values later (e.g. token rotation):

```bash
aws secretsmanager put-secret-value \
  --secret-id "/prod/aws-whatsapp-chatbot" \
  --secret-string '{"AWS_API_KEY_TOKEN":"...","META_TOKEN":"...","META_FROM_PHONE_NUMBER_ID":"..."}'
```

## Route53 Hosted Zone

The custom DNS endpoints require an existing Hosted Zone (configured in `infrastructure/cdk.json` via `hosted_zone_name` and `hosted_zone_id`).

## Bedrock Model Access

Enable **Anthropic Claude Sonnet 5** in the Bedrock console (Model access) for the region where you deploy (default `us-east-1`, cross-region inference profile `us.anthropic.claude-sonnet-5`).

For the full deployment guide, see [GETTING_STARTED.md](../GETTING_STARTED.md).
