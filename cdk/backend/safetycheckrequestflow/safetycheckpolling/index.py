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
        request_id = event_body['requestId']
            

        ddbworkordertable = dynamodb.Table(work_order_requests_table)

        response = ddbworkordertable.get_item(
            Key={'requestId': request_id}
        )

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Request not found'})
        }
            
        item = response['Item']

        if item['status'] != 'COMPLETED':
            return {
                'statusCode': 202,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': 'true'
                },
                'body': json.dumps({
                    'requestId': request_id,
                    'status': item['status']
                })
            }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({
                'requestId': request_id,
                'status': 'COMPLETED',
                'safetycheckresponse': item['safetycheckresponse']
            })
        }


    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {'statusCode': 500, 'body': "error in processing request"}
    

    