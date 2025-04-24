#!/usr/bin/env python3

# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/
import re

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from backend import BackendStack
from bedrock_agents import BedrockAgentsStack

from webappstack import FrontendStack

app = cdk.App()

# Get configuration parameters from context
openweather_api_key: str = app.node.try_get_context("openweather_api_key")


# Get foundation model parameters from context
collaborator_foundation_model: str = app.node.try_get_context("collaborator_foundation_model")
if collaborator_foundation_model is None:
    collaborator_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

supervisor_foundation_model: str = app.node.try_get_context("supervisor_foundation_model")
if supervisor_foundation_model is None:
    supervisor_foundation_model = "anthropic.claude-3-sonnet-20240229-v1:0"

# Default language
language_code = "en"

# Deploy Bedrock Agents stack first
bedrock_agents_stack = BedrockAgentsStack(
    app,
    "BedrockAgentStack",
    collaborator_foundation_model=collaborator_foundation_model,
    supervisor_foundation_model=supervisor_foundation_model,
    openweather_api_key=openweather_api_key
)


# Deploy Backend stack with references to Bedrock Agents stack
main_backend_stack = BackendStack(
    app,
    "MainBackendStack",
    language_code=language_code,
    agent_id=bedrock_agents_stack.supervisor_agent_id,
    agent_alias_id=bedrock_agents_stack.supervisor_agent_alias_id,
    work_order_table_name=bedrock_agents_stack.work_orders_table_name,
    location_table_name=bedrock_agents_stack.locations_table_name,
)

# Add dependency to ensure Bedrock Agents stack is created first
main_backend_stack.add_dependency(bedrock_agents_stack)

# Deploy frontend stack with dependency on backend stack and pass backend outputs
frontend_stack = FrontendStack(
    app,
    "FrontendStack",
    api_endpoint=main_backend_stack.api_endpoint,
    workorder_api_endpoint=main_backend_stack.workorder_api_endpoint,
    region_name=main_backend_stack.region_name,
    cognito_user_pool_id=main_backend_stack.user_pool_id,
    cognito_user_pool_client_id=main_backend_stack.user_pool_client_id,
    cognito_identity_pool_id=main_backend_stack.identity_pool_id
)
frontend_stack.add_dependency(main_backend_stack)


cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
