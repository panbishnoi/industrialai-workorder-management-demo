import os

from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    CfnOutput,
    Names,
    Duration,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_cognito as cognito,
)
from constructs import Construct


import core_constructs as core

from cdk_nag import NagSuppressions, NagPackSuppression

class WebSocketApiStack(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        agent_id:  str,
        agent_alias_id: str,        
        region: str,
        user_pool= str,
        client_id= str,
    ) -> None:
        super().__init__(scope, construct_id)

        # DynamoDB table to store the chat's memory
        web_socket_table = core.CoreTable(
            self,
            "WebSocketConnectionTable",
            partition_key=dynamodb.Attribute(
                name="connectionId", type=dynamodb.AttributeType.STRING
            ),
        )


        # a lambda function process the customer's question
        web_socket_fn = lambda_python.PythonFunction(
            self,
            "Websocket API",
            entry=f"{os.path.dirname(os.path.realpath(__file__))}/lambda",
            index="websocket.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.seconds(180),
            memory_size=512,
            environment={
                "WS_CONNECTION_TABLE_NAME": "WebSocketConnectionTable",
                "CLIENT_ID": client_id,
                "USER_POOL_ID": user_pool,
                "REGION": region,
                "AGENT_ID": agent_id,
                "AGENT_ALIAS_ID": agent_alias_id,
            },
        )

        web_socket_fn_policy = iam.Policy(self, "WebSocketFnPolicy")

        web_socket_fn_policy.add_statements(
            iam.PolicyStatement(
                sid="DynamoDBAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:BatchGetItem",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                sid="CWAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                sid="CognitoAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "cognito-idp:DescribeUserPool",
                    "cognito-idp:DescribeUserPoolClient",
                    "cognito-idp:GetJWKS",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                sid="BedrockFullAccess",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:*"],
                resources=["*"],
            ),
        )

        # Attach the IAM policy to the Lambda function's role
        web_socket_fn.role.attach_inline_policy(web_socket_fn_policy)

        NagSuppressions.add_resource_suppressions(
            web_socket_fn_policy,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This Lambda has wildcard permissions to allow choice of Bedrock, Dynamo and manage CloudWatch Logs log groups.",
                )
            ],
            True,
        )

        # create optimization job API method
        websocket_api = core.CoreWebSocketApiGateway(
            self, 
            "WebSocketApi",
            region="us-east-1",
            websocket_handler=web_socket_fn
        )

        NagSuppressions.add_resource_suppressions(
            web_socket_fn,
            [
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": """Certain policies will implement wildcard permissions to expedite development. 
            TODO: Replace on Production environment (Path to Production)""",
                },
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": """Prototype will use managed policies to expedite development. 
                        TODO: Replace on Production environment (Path to Production)""",
                    "appliesTo": [
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                    ],
                },
                {
                    "id": "AwsSolutions-L1",
                    "reason": """Policy managed by AWS can not specify a different runtime version""",
                },
            ],
            True,
        )