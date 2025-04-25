# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import os
import subprocess
import time
from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_s3 as s3,
    aws_s3_deployment as s3_deploy,
    aws_wafv2 as wafv2,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_lambda as lambda_,
    aws_iam as iam,
    CustomResource,
    Duration,
    custom_resources as cr,
)
from constructs import Construct
from cdk_nag import NagSuppressions

class FrontendStack(Stack):
    def __init__(self, scope: Construct, id: str, 
                 api_endpoint: str,
                 workorder_api_endpoint: str,
                 region_name: str,
                 cognito_user_pool_id: str,
                 cognito_user_pool_client_id: str,
                 cognito_identity_pool_id: str,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Add stack-level suppressions right at the beginning
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "AWS Lambda Basic Execution Role is required for Lambda functions",
                    "appliesTo": ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Required S3 permissions for deployment",
                    "appliesTo": [
                        "Resource::*/*",
                        "Action::s3:GetObject*",
                        "Action::s3:GetBucket*",
                        "Action::s3:List*",
                        "Action::s3:DeleteObject*",
                        "Action::s3:Abort*"
                    ]
                },
                {
                    "id": "AwsSolutions-L1",
                    "reason": "CDK-managed Lambda functions use runtimes we cannot directly control",
                    "appliesTo": [
                        "Resource::*Custom::CDKBucketDeployment*",
                        "Resource::*framework-onEvent*"
                    ]
                },
                {
                    "id": "AwsSolutions-S1",
                    "reason": "For prototyping purposes we chose not to log access to bucket",
                    "appliesTo": ["Resource::*Bucket*"]
                },
                {
                    "id": "AwsSolutions-CFR4",
                    "reason": "Amazon S3 doesn't support HTTPS for website endpoints",
                    "appliesTo": ["Resource::*Distribution*"]
                },
                {
                    "id": "AwsSolutions-CFR3",
                    "reason": "For prototyping purposes we chose not to log access",
                    "appliesTo": ["Resource::*Distribution*"]
                }
            ]
        )

        # Build the frontend at synth time
        print("Building frontend application...")
        try:
            # Run npm install and build in the frontend directory
            subprocess.run(
                "cd ../frontend && npm install --legacy-peer-deps && npm run build:skip-typescript",
                shell=True,
                check=True
            )
            print("Frontend build completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error building frontend: {e}")
            raise e

        # Create S3 bucket for webapp
        webapp_bucket = s3.Bucket(
            self, "WebappDeploymentBucket",
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )
        
        # Deploy the built frontend to S3
        bucket_deployment = s3_deploy.BucketDeployment(
            self, "DeployFrontend",
            sources=[s3_deploy.Source.asset("../frontend/dist")],
            destination_bucket=webapp_bucket,
        )
        
        # Create a Lambda function to update config.js with actual backend values
        config_lambda = lambda_.Function(
            self, "ConfigUpdateLambda",
            runtime=lambda_.Runtime.NODEJS_20_X,
            handler="index.handler",
            timeout=Duration.minutes(5),
            memory_size=512,
            code=lambda_.Code.from_asset("./webappstack/lambda-config"),
            environment={
                "S3_BUCKET_NAME": webapp_bucket.bucket_name
            }
        )

        # Grant the Lambda function permissions to read/write to the S3 bucket
        webapp_bucket.grant_read_write(config_lambda)

        # Create a custom resource provider
        provider = cr.Provider(
            self, "ConfigUpdateProvider",
            on_event_handler=config_lambda,
            log_retention=None
        )

        # Create a custom resource to trigger the Lambda function
        config_custom_resource = CustomResource(
            self, "ConfigUpdateResource",
            service_token=provider.service_token,
            properties={
                "ApiEndpoint": api_endpoint,
                "WorkorderApiEndpoint": workorder_api_endpoint,
                "RegionName": region_name,
                "CognitoUserPoolId": cognito_user_pool_id,
                "CognitoUserPoolClientId": cognito_user_pool_client_id,
                "CognitoIdentityPoolId": cognito_identity_pool_id,
                "BuildTimestamp": time.time()  # Force update on each deployment
            }
        )
        
        # Ensure the custom resource runs after the bucket deployment completes
        config_custom_resource.node.add_dependency(bucket_deployment)

        # Create WAF Web ACL
        web_acl = wafv2.CfnWebACL(
            self, "WebACL",
            name="WebACLTest",
            description="WAF rules for CloudFront",
            scope="CLOUDFRONT",
            default_action={
                "allow": {}
            },
            visibility_config={
                "cloudWatchMetricsEnabled": True,
                "metricName": "WebACLMetric",
                "sampledRequestsEnabled": True
            },
            rules=[
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedRules",
                    priority=0,
                    override_action={
                        "none": {}
                    },
                    statement={
                        "managedRuleGroupStatement": {
                            "vendorName": "AWS",
                            "name": "AWSManagedRulesCommonRuleSet",
                            "excludedRules": []
                        }
                    },
                    visibility_config={
                        "sampledRequestsEnabled": True,
                        "cloudWatchMetricsEnabled": True,
                        "metricName": "AWSManagedRulesMetric"
                    }
                )
            ]
        )

        # Create Origin Access Control
        origin_access_control = cloudfront.CfnOriginAccessControl(
            self, "WebappOriginAccessControl",
            origin_access_control_config=cloudfront.CfnOriginAccessControl.OriginAccessControlConfigProperty(
                name="WebappOAC",
                origin_access_control_origin_type="s3",
                signing_behavior="always",
                signing_protocol="sigv4"
            )
        )

        # Create CloudFront distribution with OAC
        distribution = cloudfront.Distribution(self, "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    webapp_bucket,
                    origin_access_levels=[cloudfront.AccessLevel.READ]
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED
            ),
            default_root_object="index.html",
            web_acl_id=web_acl.attr_arn
        )
        self.frontend_url = f"https://{distribution.distribution_domain_name}"
        # Output CloudFront URL
        CfnOutput(
            self, "FrontendUrl",
            value=f"https://{distribution.distribution_domain_name}"
        )
