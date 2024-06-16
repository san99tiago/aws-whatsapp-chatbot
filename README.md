# AWS-WHATSAPP-POC

These are my initial experiments/playground on creating advanced WhatsApp Chatbots on AWS.

## Manual Steps 1 (Configure WhatsApp "Free Tier" Business/API)

1. Create "Meta for Developers" account:

   - https://business.facebook.com
   - https://youtu.be/CEt_KMMv3V8?list=PLX_K_BlBdZKi4GOFmJ9_67og7pMzm2vXH

2. Create an App:

   - Select "Type" == "Business"
   - App Name == "ADD_NAME" (eg "san99tiago")
   - Contact == "ADD_EMAIL" (eg "san99tiago+meta@gmail.com")

3. Enable the "WhatsApp Integration":

   - Click on "Integrate with WhatsApp"

4. Create a "Business portfolio in Business Manager"

   - Business Name == "ADD_NAME" (eg "SANTI")
   - Person's Name == "ADD_NAME" (eg "Santiago Garcia Arango")
   - Business Email == "ADD_EMAIL" (eg "san99tiago+meta@gmail.com")

5. Configure the "WhatsApp Business API"

   - On the "WhatsApp Business Platform API", select the business portfolio created on "step 4"
   - Accept terms and conditions and we should be ready to send messages to up to 5 numbers in the free tier!
   - We will use the given "test number" for now (as we don't want to add a custom number for this PoC)
   - We can register up to 5 free "recipients" phone numbers in the free tier (eg "our real phone number")

6. As soon as the CDK deployment on AWS finishes, we should be able to provide the "WebHook Endpoint" to the WhatsApp Webhook's "Callback URL":

   - Important: there will be a "Verify Token" that needs to be provided from the service
   - Then, we can configure the desired incoming events via the "Webhook fields" option on the configuration (eg "messages")

## Author 🎹

### Santiago Garcia Arango

<table border="1">
    <tr>
        <td>
            <p align="center">Curious DevOps Engineer passionate about advanced cloud-based solutions and deployments in AWS. I am convinced that today's greatest challenges must be solved by people that love what they do.</p>
        </td>
        <td>
            <p align="center"><img src="assets/SantiagoGarciaArango_AWS.png" width=80%></p>
        </td>
    </tr>
</table>

## LICENSE

Copyright 2024 Santiago Garcia Arango.
