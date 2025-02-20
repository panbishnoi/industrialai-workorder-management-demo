# Gen AI Based field Workforce safety assistant


## Architecture Overview


### Backend


## Deployment
### Prerequisites

- An AWS account
- Configure AWS credentials in your environment
- Download and install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Download and install [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) >= 2.167.2
- Download and install [Docker](https://docs.docker.com/engine/install/)
- NodeJS >= 18.0.0
- Python >= 3.10
- Access to Amazon Titan Text Embeddings V2 model and Anthropic Claude 3 Haiku model. Enable these in the Amazon Bedrock console (https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess). You may need to request access if not already granted.

### Setup

1. Create and activate a Python virtual environment:

```bash
cd cdk
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate.bat
```
You should see (.venv) at the beginning of your command prompt.

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. Log in to the AWS ECR Public registry. This is needed to download docker images for builds.
```bash
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
```

4. If this is the first time using CDK in this account and region, bootstrap CDK. This is a one-time setup that provisions resources CDK needs to deploy your stacks.
```bash
cdk bootstrap
```

### Deployment
These steps may take a long time and produce a lot of output.

Synthesize the CloudFormation template:

```bash
cdk synth
```

Deploy the stacks:
```bash    
cdk deploy --all --require-approval never


aws cloudfront create-invalidation \
    --distribution-id E1XTYQEZ2FPIOI \
    --paths "/*"

For convenience in future deployments, you may choose to persist the context values in `cdk.json`:
```json
{
  "app": "python3 app.py",
...
  "context": {
    "oss_collection_name": "my-rag-collection",
    "oss_index_name": "my-rag-index",
    "language_code": "es",
    "max_retrieved_docs": 5,
    "@aws-cdk/...
```

#### Important Outputs

After successful deployment, you'll receive important output values. These values are specific to your deployment and will be different for each account and region. Make note of these outputs as they contain the information you'll need to fill in placeholders in subsequent steps.


Key outputs to note from the MainBackendStack:

* ApiGatewayRestApiEndpoint
* CognitoIdentityPoolId
* CognitoUserPoolClientId
* CognitoUserPoolId
* RegionName

## Usage


### Demo Chatbot
There is a demo chatbwebapp `frontend/`. See the [README](frontend/README.md) for usage details. It needs the outputs from the MainBackendStack.

This is the best way to validate that the MainBackendStack was deployed correctly.

#### Create Cognito Users

1. Navigate to the Amazon Cognito console.
2. Find your User Pool using the `CognitoUserPoolId` from the MainBackendStack outputs.
3. In the "Users" section, click "Create user" and follow the instructions.

[More details](https://docs.aws.amazon.com/cognito/latest/developerguide/how-to-create-user-accounts.html#creating-a-new-user-using-the-console)


## Clean Up
To avoid further charges, follow the tear down procedure:

1. On the AWS CloudFormation console or using AWS CDK in the terminal, destroy the stacks that were deployed. Some of the S3 buckets, CloudWatch Logs log groups, and Cognito user pools will remain as they will not be empty.
```bash
cdk destroy --all
```
2. Delete any Cognito User Pools that you do not wish to keep.
2. Delete any CloudWatch Logs log groups that you do not wish to keep.
3. In any S3 buckets that remain that you do not wish to keep, empty the buckets by disabling logging and configuring a lifecycle policy that expires objects after one day. Wait a day.
4. After a day, go back and delete the buckets.

For a comprehensive list of arguments and options, consult the [CDK CLI documentation](https://docs.aws.amazon.com/cdk/v2/guide/cli.html).

## Security Guideline
Please see the [security guidelines](documentation/security.md).

## Content Security Legal Disclaimer
Sample code, software libraries, command line tools, proofs of concept, templates, or other related technology are provided as AWS Content or Third-Party Content under the AWS Customer Agreement, or the relevant written agreement between you and AWS (whichever applies). You should not use this AWS Content or Third-Party Content in your production accounts, or on production or other critical data. You are responsible for testing, securing, and optimizing the AWS Content or Third-Party Content, such as sample code, as appropriate for production grade use based on your specific quality control practices and standards. Deploying AWS Content or Third-Party Content may incur AWS charges for creating or using AWS chargeable resources, such as running Amazon EC2 instances or using Amazon S3 storage.
