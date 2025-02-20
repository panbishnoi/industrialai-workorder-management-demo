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
    aws_events as events,
    aws_events_targets as targets,
    aws_dynamodb as dynamodb
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression

import core_constructs as core


class SafetyCheckBatchStack(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        work_order_request_table: dynamodb.Table,
        dynamo_db_workorder_table: str,
        dynamo_db_location_table: str,
    ) -> None:
        super().__init__(scope, construct_id)

        # a lambda function process the customer's question
        safety_check_batch_fn = lambda_python.PythonFunction(
            self,
            "ProcessQuery",
            entry=f"{os.path.dirname(os.path.realpath(__file__))}/batch_safety_check_fn",
            index="index.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.seconds(180),
            memory_size=512,
            environment={
                "LOG_LEVEL": "DEBUG",
                "POWERTOOLS_SERVICE_NAME": "BatchSafetyCheckFlow",
                "WORK_ORDER_REQUEST_TABLE_NAME": work_order_request_table.table_name,
                "WORK_ORDER_LOCATION_TABLE_NAME": dynamo_db_location_table,
                "WORK_ORDER_TABLE_NAME": dynamo_db_workorder_table
            },
        )

        batch_safety_check_fn_policy = iam.Policy(self, "SafetyCheckBatchFnPolicy")


        # Create EventBridge Rule
        schedule_rule = events.Rule(
            self,
            "WorkOrderSafetyCheckRule",
            schedule=events.Schedule.cron(
                minute='15',
                hour='11',
                month='*',
                week_day='*',
                year='*'
            ),
            targets=[targets.LambdaFunction(safety_check_batch_fn)]
        )

        batch_safety_check_fn_policy.add_statements(
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
        safety_check_batch_fn.role.attach_inline_policy(batch_safety_check_fn_policy)

        NagSuppressions.add_resource_suppressions(
            batch_safety_check_fn_policy,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This Lambda has wildcard permissions to allow choice of Bedrock model and manage CloudWatch Logs log groups.",
                )
            ],
            True,
        )

        NagSuppressions.add_resource_suppressions(
            safety_check_batch_fn,
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
