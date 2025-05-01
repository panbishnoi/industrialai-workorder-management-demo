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
    aws_logs as logs
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression
import core_constructs as core


class SafetyCheckRequestStack(Construct):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_gateway: core.CoreApiGateway,
        work_order_requests_table: dynamodb.Table
    ) -> None:
        super().__init__(scope, construct_id)

        # Define function name first
        function_name = f"{construct_id.lower()}-workorder-request"
        
        # Create explicit log group for safety check request function
        safet_check_request_log_group = logs.LogGroup(
            self,
            "SafetyCheckRequestLogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # a lambda function process the customer's question
        safet_check_request_fn = lambda_python.PythonFunction(
            self,
            "WorkOrderRequest",
            function_name=function_name,
            entry=f"{os.path.dirname(os.path.realpath(__file__))}/safetycheckrequest",
            index="index.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.seconds(90),
            memory_size=512,
            environment={
                "LOG_LEVEL": "DEBUG",
                "POWERTOOLS_SERVICE_NAME": "SafetyCheckRequestFlow",
                "work_order_requests_table": work_order_requests_table.table_name,
            },
        )


        work_order_requests_table.grant_read_write_data(safet_check_request_fn)

        safet_check_request_fn_plicy = iam.Policy(self, "SafetyCheckReqiestFnPolicy")

        safet_check_request_fn_plicy.add_statements(
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
        safet_check_request_fn.role.attach_inline_policy(safet_check_request_fn_plicy)

        NagSuppressions.add_resource_suppressions(
            safet_check_request_fn_plicy,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This Lambda has wildcard permissions to allow CloudWatch Logs log groups.",
                )
            ],
            True,
        )

        # Define function name first
        polling_function_name = f"{construct_id.lower()}-safety_check_polling"
        
        # Create explicit log group for safety check request function
        safet_check_polling_log_group = logs.LogGroup(
            self,
            "SafetyCheckPollingLogGroup",
            log_group_name=f"/aws/lambda/{polling_function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        # a lambda function to support polling request and provide final response
        safet_check_polling_fn = lambda_python.PythonFunction(
            self,
            "WorkOrderPolling",
            function_name=polling_function_name,
            entry=f"{os.path.dirname(os.path.realpath(__file__))}/safetycheckpolling",
            index="index.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_13,
            timeout=Duration.seconds(90),
            memory_size=512,
            environment={
                "LOG_LEVEL": "DEBUG",
                "POWERTOOLS_SERVICE_NAME": "SafetyCheckPollingFlow",
                "work_order_requests_table": work_order_requests_table.table_name,
            },
        )


        work_order_requests_table.grant_read_write_data(safet_check_polling_fn)

        safet_check_polling_fn_plicy = iam.Policy(self, "SafetyCheckPollingFnPolicy")

        safet_check_polling_fn_plicy.add_statements(
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
        safet_check_polling_fn.role.attach_inline_policy(safet_check_polling_fn_plicy)

        NagSuppressions.add_resource_suppressions(
            safet_check_polling_fn_plicy,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This Lambda has wildcard permissions to allow CloudWatch Logs log groups.",
                )
            ],
            True,
        )




        # create optimization job API method
        api_gateway.add_method(
            resource_path="/safetycheck/request",
            http_method="POST",
            lambda_function=safet_check_request_fn,
            request_validator=api_gateway.request_body_validator,
        )

        # create optimization job API method
        api_gateway.add_method(
            resource_path="/safetycheck/status",
            http_method="POST",
            lambda_function=safet_check_polling_fn,
            request_validator=api_gateway.request_body_validator,
        )


        NagSuppressions.add_resource_suppressions(
            safet_check_request_fn,
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
            safet_check_polling_fn,
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