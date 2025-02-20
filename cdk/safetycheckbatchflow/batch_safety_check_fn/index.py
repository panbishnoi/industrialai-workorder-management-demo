import os
import json
import functools
import boto3
import traceback
import re
import time
from collections import OrderedDict
from aws_lambda_powertools.utilities.typing import LambdaContext
import uuid
from aws_lambda_powertools import Logger
from datetime import datetime, timedelta
import random
logger = Logger()
def log(message):
    logger.info(message)

WORK_ORDER_TABLE_NAME = os.getenv("WORK_ORDER_TABLE_NAME")
WORK_ORDER_REQUEST_TABLE_NAME = os.getenv("WORK_ORDER_REQUEST_TABLE_NAME")
WORK_ORDER_LOCATION_TABLE_NAME = os.getenv("WORK_ORDER_LOCATION_TABLE_NAME")
# Initialize DynamoDB 
dynamodb = boto3.resource('dynamodb')


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, _context: LambdaContext):
    try:
        # Get all work orders that need safety checks
        work_orders_table = dynamodb.Table(WORK_ORDER_TABLE_NAME)
        locations_table = dynamodb.Table(WORK_ORDER_LOCATION_TABLE_NAME)
        
        work_orders = work_orders_table.scan()
        locations = locations_table.scan()
        
        # Create locations dictionary for lookup
        locations_dict = {loc['location_name']: loc for loc in locations['Items']}
        
        current_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        for work_order in work_orders['Items']:
            
            request_id = str(uuid.uuid4())
            location_name = work_order.get('location_name')

            if "safetycheckresponse" in work_order:
                del work_order["safetycheckresponse"]
            if "safetyCheckPerformedAt" in work_order:
                del work_order["safetyCheckPerformedAt"]

            # Look up location details
            work_order['location_details'] = locations_dict.get(location_name)

            logger.info("work order in perform batch analysis is :",work_order)
            # Create safety check request with proper payload format
            safety_request = {
                'requestId': request_id,
                'work_order_id': work_order['work_order_id'],
                'payload': f"Perform weather safety and hazard safety checks for WorkOrder :{json.dumps(work_order)}",
                'status': 'PENDING',
                'createdAt': current_time.isoformat(),
                'source': 'SCHEDULED'
            }
            
            # Store request in safety checks table
            dynamodb.Table(WORK_ORDER_REQUEST_TABLE_NAME).put_item(Item=safety_request)
            
            # Calculate new timestamps
            future_days = random.uniform(1, 2)
            workorder_hours = random.uniform(4, 8)
            # Get current time and set minutes/seconds to 00:00
            
            start_time = current_time + timedelta(days=future_days)
            finish_time = start_time + timedelta(hours=workorder_hours)

            # round to nearest hour
            start_time = start_time.replace(minute=0, second=0, microsecond=0)
            finish_time = finish_time.replace(minute=0, second=0, microsecond=0)
            # Update work order timestamps
            work_orders_table.update_item(
                Key={'work_order_id': work_order['work_order_id']},
                UpdateExpression='SET scheduled_start_timestamp = :start, scheduled_finish_timestamp = :finish',
                ExpressionAttributeValues={
                    ':start': start_time.isoformat(),
                    ':finish': finish_time.isoformat()
                }
            )
            #sleep for 10 seconds to ensure the downsteam Bedrock agent can process the calls
            time.sleep(10)

    except Exception as e:
        logger.error(f"Error in scheduled safety check: {str(e)}")
        raise e

    