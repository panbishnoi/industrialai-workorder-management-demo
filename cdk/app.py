#!/usr/bin/env python3

# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    NestedStack,
    CfnParameter,
    CfnOutput
)
from constructs import Construct
from cdk_nag import AwsSolutionsChecks

from backend import BackendStack
from bedrock_agents import BedrockAgentsStack
from webappstack import FrontendStack

class BedrockAgentsNestedStack(NestedStack):
    """Nested stack version of BedrockAgentsStack"""
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        collaborator_foundation_model: str,
        supervisor_foundation_model: str,
        openweather_api_key: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create the BedrockAgentsStack within this nested stack
        # We're using composition instead of inheritance to avoid multiple inheritance issues
        self.bedrock_stack = BedrockAgentsStack(
            self,
            construct_id,  # Pass the construct_id to the inner stack
            collaborator_foundation_model=collaborator_foundation_model,
            supervisor_foundation_model=supervisor_foundation_model,
            openweather_api_key=openweather_api_key
        )
        
        # Expose the properties needed by other stacks
        self.work_orders_table_name = self.bedrock_stack.work_orders_table_name
        self.locations_table_name = self.bedrock_stack.locations_table_name
        self.supervisor_agent_id = self.bedrock_stack.supervisor_agent_id
        self.supervisor_agent_alias_id = self.bedrock_stack.supervisor_agent_alias_id

class BackendNestedStack(NestedStack):
    """Nested stack version of BackendStack"""
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        language_code: str,
        agent_id: str,
        agent_alias_id: str,
        work_order_table_name: str,
        location_table_name: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create the BackendStack within this nested stack
        # Using composition instead of inheritance
        self.backend_stack = BackendStack(
            self,
            construct_id,  # Pass the construct_id to the inner stack
            language_code=language_code,
            agent_id=agent_id,
            agent_alias_id=agent_alias_id,
            work_order_table_name=work_order_table_name,
            location_table_name=location_table_name
        )
        
        # Expose the properties needed by the frontend stack
        self.api_endpoint = self.backend_stack.api_endpoint
        self.workorder_api_endpoint = self.backend_stack.workorder_api_endpoint
        self.region_name = self.backend_stack.region_name
        self.user_pool_id = self.backend_stack.user_pool_id
        self.user_pool_client_id = self.backend_stack.user_pool_client_id
        self.identity_pool_id = self.backend_stack.identity_pool_id

class FrontendNestedStack(NestedStack):
    """Nested stack version of FrontendStack"""
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        api_endpoint: str,
        workorder_api_endpoint: str,
        region_name: str,
        cognito_user_pool_id: str,
        cognito_user_pool_client_id: str,
        cognito_identity_pool_id: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Create the FrontendStack within this nested stack
        # Using composition instead of inheritance
        self.frontend_stack = FrontendStack(
            self,
            construct_id,  # Pass the construct_id to the inner stack
            api_endpoint=api_endpoint,
            workorder_api_endpoint=workorder_api_endpoint,
            region_name=region_name,
            cognito_user_pool_id=cognito_user_pool_id,
            cognito_user_pool_client_id=cognito_user_pool_client_id,
            cognito_identity_pool_id=cognito_identity_pool_id
        )
        
        # Expose frontend URL for parent stack output
        self.frontend_url = self.frontend_stack.frontend_url

class FieldWorkforceSafetyParentStack(Stack):
    """Parent stack that contains all nested stacks"""
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        # Get configuration parameters from context
        deploy_frontend = self.node.try_get_context("deploy_frontend")
        if deploy_frontend is None:
            deploy_frontend = "yes"

        # Get configuration parameters from context
        openweather_api_key = self.node.try_get_context("openweather_api_key")

        # Get foundation model parameters from context
        collaborator_foundation_model = self.node.try_get_context("collaborator_foundation_model")
        if collaborator_foundation_model is None:
            collaborator_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

        supervisor_foundation_model = self.node.try_get_context("supervisor_foundation_model")
        if supervisor_foundation_model is None:
            supervisor_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

        # Default language
        language_code = "en"

        # Deploy Bedrock Agents nested stack (always deployed)
        bedrock_agents_stack = BedrockAgentsNestedStack(
            self,
            "BedrockAgentStack",
            collaborator_foundation_model=collaborator_foundation_model,
            supervisor_foundation_model=supervisor_foundation_model,
            openweather_api_key=openweather_api_key
        )

        # Conditionally deploy Backend and Frontend stacks based on the single parameter
        if deploy_frontend.lower() == "yes":
            # Deploy Backend stack
            backend_stack = BackendNestedStack(
                self,
                "BackendAPIStack",
                language_code=language_code,
                agent_id=bedrock_agents_stack.supervisor_agent_id,
                agent_alias_id=bedrock_agents_stack.supervisor_agent_alias_id,
                work_order_table_name=bedrock_agents_stack.work_orders_table_name,
                location_table_name=bedrock_agents_stack.locations_table_name,
            )
            # Add dependency to ensure Bedrock Agents stack is created first
            backend_stack.add_dependency(bedrock_agents_stack)

            # Deploy Frontend stack
            frontend_stack = FrontendNestedStack(
                self,
                "FrontendStack",
                api_endpoint=backend_stack.api_endpoint,
                workorder_api_endpoint=backend_stack.workorder_api_endpoint,
                region_name=backend_stack.region_name,
                cognito_user_pool_id=backend_stack.user_pool_id,
                cognito_user_pool_client_id=backend_stack.user_pool_client_id,
                cognito_identity_pool_id=backend_stack.identity_pool_id
            )
            # Add dependency to ensure Backend stack is created first
            frontend_stack.add_dependency(backend_stack)

            # Add output for webapp url
            CfnOutput(
                self,
                "FrontendUrl",
                value=frontend_stack.frontend_url,
                description="Frontend App Access URL"
            )

        # Add outputs for Bedrock Agents stack (always deployed)
        CfnOutput(
            self,
            "BedrockAgentStackId",
            value=bedrock_agents_stack.nested_stack_id,
            description="Bedrock Agent Stack ID"
        )

# Create the app and deploy the parent stack
app = cdk.App()
parent_stack = FieldWorkforceSafetyParentStack(app, "FieldWorkforceSafetyStack")
cdk.Aspects.of(app).add(AwsSolutionsChecks())
app.synth()
