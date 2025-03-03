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


class VicEmergencyStack(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_gateway: core.CoreApiGateway,
        dynamo_db_workorder_table=str,
    ) -> None:
        super().__init__(scope, construct_id)

        # a lambda function process the customer's question
        emergency_check_request_fn = lambda_python.PythonFunction(
            self,
            "EmergencyCheckRequest",
            entry=f"{os.path.dirname(os.path.realpath(__file__))}/emergencyfn",
            index="index.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.seconds(90),
            memory_size=512,
            environment={
                "LOG_LEVEL": "DEBUG",
                "POWERTOOLS_SERVICE_NAME": "EmergencyCheckFlow",
                "work_order_table_name": dynamo_db_workorder_table,
            },
        )

        emergency_check_request_fn_plicy = iam.Policy(self, "EmergencyCheckReqiestFnPolicy")

        emergency_check_request_fn_plicy.add_statements(
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
        emergency_check_request_fn.role.attach_inline_policy(emergency_check_request_fn_plicy)

        NagSuppressions.add_resource_suppressions(
            emergency_check_request_fn_plicy,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This Lambda has wildcard permissions to allow CloudWatch Logs log groups.",
                )
            ],
            True,
        )

        # create emergency check API method
        api_gateway.add_method(
            resource_path="/emergencycheck/request",
            http_method="POST",
            lambda_function=emergency_check_request_fn,
            request_validator=api_gateway.request_body_validator,
        )

        

        NagSuppressions.add_resource_suppressions(
            emergency_check_request_fn,
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

        NagSuppressions.add_resource_suppressions(
            emergency_check_request_fn,
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