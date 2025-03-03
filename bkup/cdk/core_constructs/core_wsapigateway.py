import typing
from aws_cdk import (
    Stack,
    aws_apigatewayv2 as apigateway,
    aws_cognito as cognito,
    aws_lambda,
    aws_iam as iam,
    aws_logs as logs,
)
from aws_cdk.aws_apigatewayv2_integrations import WebSocketLambdaIntegration
from constructs import Construct
from cdk_nag import NagSuppressions

class CoreWebSocketApiGateway(Construct):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            region: str,
            websocket_handler: aws_lambda.Function,
            **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Create log group for WebSocket API
        self.log_group = logs.LogGroup(self, "WebSocketLogGroup")






        # Create WebSocket API
        self.websocket_api = apigateway.WebSocketApi(
            self,
            "WebSocketApi"
        )

        self.connectRoute = self.websocket_api.add_route(
            '$connect',
            integration=WebSocketLambdaIntegration("ConnectIntegration", websocket_handler)
        )

        # Add these suppressions after creating your WebSocket API
        NagSuppressions.add_resource_suppressions(self.connectRoute
            ,
            [
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "Authorization handled in Lambda function",
                }
            ]
        )

        self.disConnectRoute = self.websocket_api.add_route(
            '$disconnect',
            integration=WebSocketLambdaIntegration("DisConnectIntegration", websocket_handler)
        )

        # Add these suppressions after creating your WebSocket API
        NagSuppressions.add_resource_suppressions(self.disConnectRoute
            ,
            [
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "Authorization handled in Lambda function",
                }
            ]
        )



        self.defaultRoute = self.websocket_api.add_route(
            '$default',
            integration=WebSocketLambdaIntegration("DefaultIntegration", websocket_handler)
        )

        # Add these suppressions after creating your WebSocket API
        NagSuppressions.add_resource_suppressions(self.defaultRoute
            ,
            [
                {
                    "id": "AwsSolutions-APIG4",
                    "reason": "Authorization handled in Lambda function",
                }
            ]
        )



        # Deploy to stage with logging
        self.stage = apigateway.WebSocketStage(
            self,
            "WebSocketStage",
            web_socket_api=self.websocket_api,
            stage_name="dev",
        )
        
        # Get the underlying CfnStage
        cfn_stage = self.stage.node.default_child


        # Configure logging using the escape hatch
        cfn_stage.access_log_settings = apigateway.CfnStage.AccessLogSettingsProperty(
            destination_arn=self.log_group.log_group_arn,
            format='$context.identity.sourceIp - - [$context.requestTime] "$context.httpMethod $context.routeKey $context.protocol" $context.status $context.responseLength $context.requestId'
        )

        # Grant WebSocket management permissions
        websocket_handler.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['execute-api:ManageConnections'],
                resources=[
                    f'arn:aws:execute-api:{region}:{Stack.of(self).account}:{self.websocket_api.api_id}/{self.stage.stage_name}/*'
                ]
            )
        )
        