# AWS PREREQUISITES FOR THE GITHUB ACTIONS CI/CD PIPELINE

Inspired on:

- https://github.com/aws-actions/configure-aws-credentials/tree/main/examples

## Part 1 (CDK Bootstrap)

Make sure that the target account (on the needed regions) have CDK Bootstrapped already. If not, please follow these steps to have CDK init stack already in place:

- [AWS CDK Bootstrapping Guide](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)

## Part 2 (GitHub OIDC Federation and Role)

The CI/CD uses aws-action `configure-aws-credentials` with OIDC federation. Prior to using this project, we need to deploy the [github-actions-oidc-federation-and-role](github-actions-oidc-federation-and-role.yml) CloudFormation template in the AWS account(s) that we need to deploy the solution. Specify the GitHub Organization Name, Repository Name, and the specific branch you want to deploy on.

> Note: In this case, "GitHub Organization Name" is "san99tiago" (my GitHub account).

To use the example you will need to set the following GitHub Action Secrets:

| Secret Key           | Used With                 | Description                     |
| -------------------- | ------------------------- | ------------------------------- |
| DEV_AWS_ACCOUNT_ID   | configure-aws-credentials | The AWS account ID (DEV)        |
| PROD_AWS_ACCOUNT_ID  | configure-aws-credentials | The AWS account ID (PROD)       |
| DEV_AWS_DEPLOY_ROLE  | configure-aws-credentials | The name of the IAM role (DEV)  |
| PROD_AWS_DEPLOY_ROLE | configure-aws-credentials | The name of the IAM role (PROD) |
