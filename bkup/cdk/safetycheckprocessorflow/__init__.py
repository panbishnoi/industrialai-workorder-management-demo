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
    aws_dynamodb as dynamodb
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression

import core_constructs as core


class SafetyCheckProcessorStack(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        work_order_requests_table: dynamodb.Table,
        agent_id: str,
        agent_alias_id: str,
        dynamo_db_workorder_table: str,
    ) -> None:
        super().__init__(scope, construct_id)

        # a lambda function process the customer's question
        safety_check_processor_fn = lambda_python.PythonFunction(
            self,
            "ProcessQuery",
            entry=f"{os.path.dirname(os.path.realpath(__file__))}/safety_check_fn",
            index="index.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.seconds(180),
            memory_size=512,
            environment={
                "LOG_LEVEL": "DEBUG",
                "POWERTOOLS_SERVICE_NAME": "SafetyCheckFlow",
                "AGENT_ID": agent_id,
                "AGENT_ALIAS_ID": agent_alias_id,
                "WORK_ORDER_TABLE_NAME": dynamo_db_workorder_table,
                "WORK_ORDER_REQUEST_TABLE_NAME": work_order_requests_table.table_name
            },
        )

        safety_check_fn_policy = iam.Policy(self, "SafetyCheckProcessorFnPolicy")

        work_order_requests_table.grant_read_write_data(safety_check_fn_policy)
        work_order_requests_table.grant_stream_read(safety_check_processor_fn)
        # Create event source mapping for DynamoDB Streams
        lambda_.EventSourceMapping(
            self,
            "StreamProcessorMapping",
            target=safety_check_processor_fn,
            event_source_arn=work_order_requests_table.table_stream_arn,
            starting_position=lambda_.StartingPosition.TRIM_HORIZON,
            batch_size=1,
            retry_attempts=3
        )

        safety_check_fn_policy.add_statements(
            iam.PolicyStatement(
                sid="BedrockFullAccess",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:*"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem",
                        "dynamodb:Scan",
                        "dynamodb:Query"
                    ],
                resources=["*"]
            ),            
        )

        # Attach the IAM policy to the Lambda function's role
        safety_check_processor_fn.role.attach_inline_policy(safety_check_fn_policy)

        NagSuppressions.add_resource_suppressions(
            safety_check_fn_policy,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This Lambda has wildcard permissions to allow choice of Bedrock model and manage CloudWatch Logs log groups.",
                )
            ],
            True,
        )

        NagSuppressions.add_resource_suppressions(
            safety_check_processor_fn,
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
