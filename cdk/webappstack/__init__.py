# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License http://aws.amazon.com/asl/

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

        # Build the frontend at synth time
        print("Building frontend application...")
        try:
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

        # Create Lambda function with latest runtime
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

        # Create custom resource provider
        provider = cr.Provider(
            self, "ConfigUpdateProvider",
            on_event_handler=config_lambda
        )

        # Create custom resource
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
                "BuildTimestamp": time.time()
            }
        )
        config_custom_resource.node.add_dependency(bucket_deployment)

        # Create CloudFront distribution
        distribution = cloudfront.Distribution(
            self, "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin(webapp_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED
            ),
            default_root_object="index.html"
        )

        # --------------------------
        # cdk-nag Suppressions
        # --------------------------
        NagSuppressions.add_stack_suppressions(self, [
            {
                "id": "AwsSolutions-IAM5",
                "reason": "CDK-generated deployment role requires asset bucket access",
                "appliesTo": [
                    f"Resource::arn:aws:s3:::cdk-*-{self.account}-{self.region}/*",
                    f"Resource::{webapp_bucket.bucket_arn}/*",
                    "Resource::*Custom::CDKBucketDeployment*",
                    "Resource::*framework-onEvent*"
                ]
            },
            {
                "id": "AwsSolutions-L1",
                "reason": "CDK-managed Lambda functions use pinned runtimes",
                "appliesTo": [
                    "Resource::*Custom::CDKBucketDeployment*",
                    "Resource::*framework-onEvent*"
                ]
            }
        ])

        # Resource-specific suppressions
        NagSuppressions.add_resource_suppressions(webapp_bucket, [
            {"id": "AwsSolutions-S1", "reason": "Prototype bucket doesn't require access logging"}
        ])

        NagSuppressions.add_resource_suppressions(config_lambda.role, [
            {
                "id": "AwsSolutions-IAM5", 
                "reason": "Requires write access to specific S3 paths",
                "appliesTo": [f"Resource::{webapp_bucket.bucket_arn}/*"]
            }
        ])

        NagSuppressions.add_resource_suppressions(provider.on_event_handler.role, [
            {
                "id": "AwsSolutions-IAM5",
                "reason": "CDK custom resource requires Lambda invocation",
                "appliesTo": ["Resource::*"]
            }
        ])

        # Outputs
        self.frontend_url = f"https://{distribution.distribution_domain_name}"
        CfnOutput(self, "FrontendUrl", value=self.frontend_url)
