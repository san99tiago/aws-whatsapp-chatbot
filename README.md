# :scroll: AWS-WHATSAPP-CHATBOT :scroll:

![Latest CI/CD Action workflow](https://github.com/san99tiago/aws-whatsapp-chatbot/actions/workflows/deploy.yml/badge.svg?branch=main)

My Serverless WhatsApp chatbot on AWS, serving as a personal assistant with access to my private data.

## Architecture :memo:

<img src="assets/aws-whatsapp-chatbot.png" width=90%> <br>

How is the Generative-AI approach implemented on top of AWS?

- RAG on top of Bedrock Knowledge Bases leveraging an OpenSearch Serverless Vector DB from PDF files.
- Bedrock Agents to enable APIs and Database requests to fetch live data as part of the chain-of-thought process.
- State Machine for different workflow's processing based on the user's input (text, voice-message, etc).

## State Machine Process :fallen_leaf:

The processing of messages is powered by an AWS Step Function that has multiple tasks based on the user's input:

<img src="assets/WhatsApp_Chatbot_StateMachine.PNG" width=50%> <br>

## Results (WhatsApp Assistant Demo) 🔮

<img src="assets/WhatsApp_Chatbot_Results_01.PNG" width=35%> <img src="assets/WhatsApp_Chatbot_Results_02.PNG" width=35%>

<img src="assets/WhatsApp_Chatbot_Results_03.PNG" width=35%> <img src="assets/WhatsApp_Chatbot_Results_04.PNG" width=35%>

## Manual Steps (Only Once) :raised_hand:

### WhatsApp Configurations

These steps show the creation of the "Meta Projects" and settings that will allow us to use WhatsApp Business APIs:

- [WHATSAPP_CONFIGURATION README](./docs/WHATSAPP_CONFIGURATION.md)

### AWS Configurations

These steps show the creation of a Secret on AWS that will contain the required tokens/credentials for connecting AWS and Meta APIs.

- [AWS_CONFIGURATION README](./docs/AWS_CONFIGURATION.md)

## Shoutouts 🙌

Thanks for all the inspiration and guidance on the Generative AI journey:

- [elizabethfuentes12](https://github.com/elizabethfuentes12) -> Gracias, Eli por inspirarme a ser un Developer Advocate!
- [micheldirk](https://medium.com/@micheldirk) -> Thanks Michel for the inspiration for the low-level CDK constructs!

## Author 🎹

### Santiago Garcia Arango

<table border="1">
    <tr>
        <td>
            <p align="center">Curious Solutions Architect experienced in DevOps and passionate about advanced cloud-based solutions and deployments in AWS. I am convinced that today's greatest challenges must be solved by people that love what they do.</p>
        </td>
        <td>
            <p align="center"><img src="assets/SantiagoGarciaArango_AWS.png" width=80%></p>
        </td>
    </tr>
</table>

## LICENSE

Copyright 2024 Santiago Garcia Arango.
