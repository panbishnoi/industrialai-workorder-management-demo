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
    aws_cloudfront_origins as origins
)
from constructs import Construct
from cdk_nag import NagSuppressions

class FrontendStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create S3 bucket for webapp
        webapp_bucket = s3.Bucket(
            self, "WebappDeploymentBucket",
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.S3_MANAGED,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )

        # Execute build command
      #  subprocess.run(
       #     "cd ../../frontend && npm run build --no-warnings",
        #    shell=True,
         #   check=True,
          #  text=True
       # )

        # Deploy to S3
        deployment = s3_deploy.BucketDeployment(
            self, "DeployWebapp",
            sources=[s3_deploy.Source.asset(os.path.join(os.path.dirname(__file__),"..",  "..", "frontend", "dist"))],
            destination_bucket=webapp_bucket,
        )

        # Create WAF Web ACL
        web_acl = wafv2.CfnWebACL(
            self, "WebACL",
            name="WebACLTest",  # Required unique name
            description="WAF rules for CloudFront",  # Optional description
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
                wafv2.CfnWebACL.RuleProperty(  # Use the proper RuleProperty class
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

        

        # Output CloudFront URL
        CfnOutput(
            self, "RepositoryCloneUrlHttp",
            value=distribution.distribution_domain_name
        )

        # Add NAG suppressions
        NagSuppressions.add_resource_suppressions(
            webapp_bucket,
            [{
                "id": "AwsSolutions-S1",
                "reason": "For prototyping purposes we chose not to log access to bucket. You should consider logging as you move to production."
            }]
        )

        NagSuppressions.add_resource_suppressions(
            deployment.handler_role,
            [{
                "id": "AwsSolutions-IAM4",
                "reason": "The bucket deployment CDK construct uses a lambda function which uses AWSLambdaBasicExecutionRole managed policy",
                "applies_to": ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
            }]
        )

        NagSuppressions.add_resource_suppressions(
            deployment.handler_role,
            [{
                "id": "AwsSolutions-IAM5",
                "reason": "The bucket deployment CDK construct requires wildcard permissions for deploying assets to the bucket"
            }],
            True
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            "/FrontendStack/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/Resource",
            [{
                "id": "AwsSolutions-L1",
                "reason": "The bucket deployment CDK construct maintainers are responsible for updating non-container lambda runtimes"
            }]
        )

        NagSuppressions.add_resource_suppressions(
            distribution,
            [{
                "id": "AwsSolutions-CFR4",
                "reason": "Amazon S3 doesn't support HTTPS for website endpoints"
            }]
        )

        NagSuppressions.add_resource_suppressions(
            distribution,
            [{
                "id": "AwsSolutions-CFR3",
                "reason": "For prototyping purposes we chose not to log access to bucket. You should consider logging as you move to production."
            }]
        )
