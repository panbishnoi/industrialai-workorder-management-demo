# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import typing
from aws_cdk import (
    Duration,
    Stack,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_logs as logs,
    aws_lambda,
    aws_wafv2 as waf,
)
from constructs import Construct
from cdk_nag import NagSuppressions, NagPackSuppression


class CoreApiGateway(Construct):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            region: str,
            user_pool: cognito.UserPool,
            **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.cognito_authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "CognitoUserPoolAuthorizer",
            cognito_user_pools=[user_pool],
        )

        self.log_group = logs.LogGroup(self, "LogGroup")

        self.rest_api = apigateway.RestApi(
            self,
            "RestApi",
            cloud_watch_role=True,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=apigateway.Cors.DEFAULT_HEADERS,
            ),
            binary_media_types=["application/pdf", "text/plain"],
            deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.INFO,
                access_log_destination=apigateway.LogGroupLogDestination(self.log_group),
                access_log_format=apigateway.AccessLogFormat.clf(),
                tracing_enabled=True,
                data_trace_enabled=False,
                stage_name="api",
            ),
            endpoint_export_name=f"{Stack.of(self).stack_name}{construct_id}RestApiEndpoint",
        )

        self.pdf_model = self.rest_api.add_model(
            "PDFDoc",
            schema=apigateway.JsonSchema(),
            content_type="application/pdf",
        )
        self.json_model = self.rest_api.add_model(
            "JSONDoc",
            schema=apigateway.JsonSchema(),
            content_type="application/json",
        )
        self.text_model = self.rest_api.add_model(
            "TextDoc",
            schema=apigateway.JsonSchema(),
            content_type="text/plain",
        )

        self.request_body_validator = apigateway.RequestValidator(
            self,
            "RequestBodyValidator",
            rest_api=self.rest_api,
            request_validator_name="Validate body",
            validate_request_body=True,
            validate_request_parameters=False,
        )

        # Choose a validator based on your needs

        self.request_params_validator = apigateway.RequestValidator(
            self,
            "RequestParametersValidator",
            rest_api=self.rest_api,
            request_validator_name="Validate query string parameters",
            validate_request_body=False,
            validate_request_parameters=True,
        )

        self.request_body_params_validator = apigateway.RequestValidator(
            self,
            "RequestBodyParametersValidator",
            rest_api=self.rest_api,
            request_validator_name="Validate body and query string parameters",
            validate_request_body=True,
            validate_request_parameters=True,
        )

        self.web_acl = waf.CfnWebACL(
            self,
            "WebACL",
            scope="REGIONAL",
            default_action=waf.CfnWebACL.DefaultActionProperty(
                allow=waf.CfnWebACL.AllowActionProperty(),
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                sampled_requests_enabled=True,
                metric_name=construct_id + "-CoreWebACL",
            ),
            rules=[
                waf.CfnWebACL.RuleProperty(
                    name="AWSManagedRules",
                    priority=0,
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet",
                            excluded_rules=[],
                        )
                    ),
                    override_action=waf.CfnWebACL.OverrideActionProperty(
                        count={},
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        sampled_requests_enabled=True,
                        metric_name=construct_id + "-CoreWebACL-AWSManagedRules",
                    ),
                )
            ],
        )

        self.web_acl_assoc = waf.CfnWebACLAssociation(
            self,
            "WebACLAssociation",
            web_acl_arn=self.web_acl.attr_arn,
            resource_arn="arn:aws:apigateway:{}::/restapis/{}/stages/{}".format(
                region,
                self.rest_api.rest_api_id,
                self.rest_api.deployment_stage.stage_name,
            ),
        )

        NagSuppressions.add_resource_suppressions(
            construct=self.rest_api,
            suppressions=[
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="AmazonAPIGatewayPushToCloudWatchLogs",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
                    ],
                ),
            ],
            apply_to_children=True,
        )

    def add_method(
            self,
            resource_path: str,
            http_method: str,
            lambda_function: aws_lambda.Function,
            request_validator: apigateway.RequestValidator,
            request_parameters: typing.Optional[typing.Mapping[str, bool]] = None,
    ):
        path_parts = list(filter(bool, resource_path.split("/")))
        resource = self.rest_api.root
        for path_part in path_parts:
            child_resource = resource.get_resource(path_part)
            if not child_resource:
                child_resource = resource.add_resource(path_part)
            resource = child_resource

        # Define Lambda integration with timeout
        lambda_integration = apigateway.LambdaIntegration(
            handler=lambda_function,
            proxy=True,  # Use proxy integration
            timeout=Duration.seconds(90),  # Set the timeout for the integration (90 seconds) to cater for bedrock agent 
        )

        resource.add_method(
            http_method=http_method,
            integration=lambda_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            request_parameters=request_parameters,
            request_validator=request_validator,
        )

        # Add Cognito auth to all methods except OPTIONS to allow for CORS header lookups
        for method in self.rest_api.methods:
            resource = method.node.find_child("Resource")
            if method.http_method == "OPTIONS":
                resource.add_property_override("AuthorizationType", apigateway.AuthorizationType.NONE)
                NagSuppressions.add_resource_suppressions(
                    construct=resource,
                    suppressions=[
                        NagPackSuppression(
                            id="AwsSolutions-COG4",
                            reason="OPTIONS method for CORS pre-flight should not use authorization",
                        ),
                        NagPackSuppression(
                            id="AwsSolutions-APIG4",
                            reason="OPTIONS method for CORS pre-flight should not use authorization",
                        ),
                    ],
                )
            else:
                resource.add_property_override("AuthorizationType", apigateway.AuthorizationType.COGNITO)
                resource.add_property_override("AuthorizerId", self.cognito_authorizer.authorizer_id)

    def add_s3_method(
            self,
            resource_path: str,
            http_method: str,
            request_validator: apigateway.RequestValidator,
            execution_role: any,
            bucket_name: str,
            request_parameters: typing.Optional[typing.Mapping[str, bool]] = None,
    ):

        s3_apigw_integration = apigateway.AwsIntegration(
            service='s3',
            integration_http_method=http_method,
            path='{}'.format(bucket_name) + '/{folder}/{key}',
            options={
                'credentials_role': execution_role,
                'integration_responses': [
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Content-Type": "integration.response.header.Content-Type",
                            "method.response.header.Access-Control-Allow-Origin": "'*'",
                        },
                    )
                ],
                'request_parameters': {
                    "integration.request.path.folder": "method.request.path.folder",
                    "integration.request.path.key": "method.request.path.key",
                },
                "passthrough_behavior": apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
            },
        )

        path_parts = list(filter(bool, resource_path.split("/")))
        resource = self.rest_api.root
        for path_part in path_parts:
            child_resource = resource.get_resource(path_part)
            if not child_resource:
                child_resource = resource.add_resource(path_part)
            resource = child_resource

        resource.add_method(
            http_method=http_method,
            integration=s3_apigw_integration,
            authorizer=self.cognito_authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            request_parameters=request_parameters,
            request_validator=request_validator,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Content-Type": True,
                        "method.response.header.Access-Control-Allow-Origin": True,
                    },
                )
            ],
            request_models={
                "application/pdf": self.pdf_model,
                "text/plain": self.text_model,
            }
        )

        # resource.add_cors_preflight(allow_origins=['*'])

        # Add Cognito auth to all methods except OPTIONS to allow for CORS header lookups
        for method in self.rest_api.methods:
            resource = method.node.find_child("Resource")
            if method.http_method == "OPTIONS":
                resource.add_property_override("AuthorizationType", apigateway.AuthorizationType.NONE)
                NagSuppressions.add_resource_suppressions(
                    construct=resource,
                    suppressions=[
                        NagPackSuppression(
                            id="AwsSolutions-COG4",
                            reason="OPTIONS method for CORS pre-flight should not use authorization",
                        ),
                        NagPackSuppression(
                            id="AwsSolutions-APIG4",
                            reason="OPTIONS method for CORS pre-flight should not use authorization",
                        ),
                    ],
                )
            else:
                resource.add_property_override("AuthorizationType", apigateway.AuthorizationType.COGNITO)
                resource.add_property_override("AuthorizerId", self.cognito_authorizer.authorizer_id)
