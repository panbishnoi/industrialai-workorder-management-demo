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
)
from constructs import Construct


import core_constructs as core

from cdk_nag import NagSuppressions, NagPackSuppression

class WorkOrderApiStack(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_gateway: core.CoreApiGateway,
        dynamo_db_workorder_table: str,
        dynamo_db_location_table: str,
    ) -> None:
        super().__init__(scope, construct_id)

        # a lambda function process the customer's question
        work_order_fn = lambda_python.PythonFunction(
            self,
            "Get WorkOrders",
            entry=f"{os.path.dirname(os.path.realpath(__file__))}/workorders",
            index="workorders.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.seconds(90),
            memory_size=512,
            environment={
                "LOG_LEVEL": "DEBUG",
                "POWERTOOLS_SERVICE_NAME": "WorkOrdersService",
                "WorkOrderTableName": dynamo_db_workorder_table,
                "LocationTableName": dynamo_db_location_table,
            },
        )

        work_order_fn_policy = iam.Policy(self, "WorkOrdersFnPolicy")

        work_order_fn_policy.add_statements(
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
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            ),
        )

        # Attach the IAM policy to the Lambda function's role
        work_order_fn.role.attach_inline_policy(work_order_fn_policy)

        NagSuppressions.add_resource_suppressions(
            work_order_fn_policy,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This Lambda has wildcard permissions to allow choice of Dynamo and manage CloudWatch Logs log groups.",
                )
            ],
            True,
        )

        # create optimization job API method
        api_gateway.add_method(
            resource_path="/workorders/",
            http_method="POST",
            lambda_function=work_order_fn,
            request_validator=api_gateway.request_body_validator,
        )

        NagSuppressions.add_resource_suppressions(
            work_order_fn,
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