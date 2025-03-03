import json
import boto3
import uuid
from datetime import datetime
import os

from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools import Logger

from aws_lambda_powertools import Logger

logger = Logger()
def log(message):
    logger.info(message)

work_order_requests_table = os.getenv("work_order_requests_table")
# Initialize DynamoDB 
dynamodb = boto3.resource('dynamodb')


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, _context: LambdaContext):
    try:
        print(event)

        event_body = json.loads(event["body"])
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        payload = json.dumps(event_body)

        try:
            # Extract query object
            query_object = event_body['query']
            workorderdetails = event_body['workorderdetails']
            work_order_id = workorderdetails['work_order_id']
            # Remove safetycheckresponse from nested workOrderLocationAssetDetails
            if "workOrderLocationAssetDetails" in workorderdetails:
                workOrderLocationAssetDetails = workorderdetails["workOrderLocationAssetDetails"]
                if "safetycheckresponse" in workOrderLocationAssetDetails:
                    del workOrderLocationAssetDetails["safetycheckresponse"]
                if "safetyCheckPerformedAt" in workOrderLocationAssetDetails:
                    del workOrderLocationAssetDetails["safetyCheckPerformedAt"]

            # Create prompt string by concatenating query and workorder details
            payload = f"{query_object} {json.dumps(workorderdetails)}"    
        except Exception as ex:
            logger.error(f"Error in getting work order: {str(ex)}")

        logger.info('work_order_id is :',work_order_id)
        logger.info('payload is :',payload)
        # Create DynamoDB item
        item = {
            'requestId': request_id,
            'work_order_id': work_order_id,
            'payload': payload,
            'status': 'PENDING',
            'createdAt': datetime.utcnow().isoformat(),
        }

        ddbworkordertable = dynamodb.Table(work_order_requests_table)

        ddbworkordertable.put_item(Item=item)

        return {
                "statusCode": 202,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true"
                },
                "body": json.dumps({"requestId": request_id})
            }
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {'statusCode': 500, 'body': "error in processing request"}
    

    