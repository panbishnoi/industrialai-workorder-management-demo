#!/usr/bin/env python3

# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/
import re

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from backend import BackendStack

from frontend import FrontendStack

app = cdk.App()

# get configuration parameters from context
agent_id: str = app.node.try_get_context("agent_id")

if agent_id is None:
    agent_id = "RTEKYDANRQ"

# get configuration parameters from context
agent_alias_id: str = app.node.try_get_context("agent_alias_id")

if agent_alias_id is None:
    agent_alias_id = "PPLSUDEKES"


# get configuration parameters from context
work_order_table_name: str = app.node.try_get_context("work_order_table_name")

if work_order_table_name is None:
    work_order_table_name = "fieldworkforce-safety-app-work-orders"

# get configuration parameters from context
location_table_name: str = app.node.try_get_context("location_table_name")

if location_table_name is None:
    location_table_name = "fieldworkforce-safety-app-locations"

#default language
language_code = "en"

main_backend_stack = BackendStack(
    app,
    "AmplifyMainBackendStack",
    language_code=language_code,
    agent_id=agent_id,
    agent_alias_id=agent_alias_id,
    work_order_table_name=work_order_table_name,
    location_table_name=location_table_name,
)

#main_backend_stack = FrontendStack(
#    app,
#    "AmplifyFrontendStack"
#)

cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
