import boto3
import csv
import json
import os
import io
from datetime import datetime
import cfnresponse

dynamodb = boto3.resource('dynamodb')

def get_table(table_name):
    return dynamodb.Table(os.environ.get(f'{table_name}_TABLE_NAME'))

def read_csv_from_s3(bucket_name, key):
    s3_client = boto3.client('s3')
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return list(csv.DictReader(io.TextIOWrapper(response['Body'], encoding='utf-8')))
    except Exception as e:
        print(f"Error reading {key} from S3: {str(e)}")
        return None

def batch_write_items(table, items):
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

def handler(event, context):
    try:
        # Check if this is a CloudFormation custom resource request
        is_cfn_request = 'RequestType' in event
        
        print(f"Event: {json.dumps(event)}")
        print(f"Is CloudFormation request: {is_cfn_request}")
        
        # For CloudFormation Delete requests, just return success
        if is_cfn_request and event['RequestType'] == 'Delete':
            print("Delete request - nothing to do")
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'Message': 'Nothing to do for Delete'
            })
            return
        
        # Proceed with data import for Create/Update or direct invocation
        s3_bucket = os.environ.get('S3_BUCKET_NAME')
        
        csv_files = {
            'work_orders': 'work_orders.csv',
            'locations': 'locations.csv',
            'hazards': 'hazards.csv',
            'incidents': 'incidents.csv',
            'assets': 'assets.csv',
            'location_hazards': 'location_hazards.csv',
            'control_measures': 'control_measures.csv'
        }
        
        results = {}
        for table_name, file_name in csv_files.items():
            items = read_csv_from_s3(s3_bucket, file_name)
            if items:
                table = get_table(table_name.upper())
                batch_write_items(table, items)
                results[table_name] = len(items)
        
        response_data = {
            'message': 'Data import completed successfully',
            'records_imported': results
        }
        
        # If this is a CloudFormation request, send the appropriate response
        if is_cfn_request:
            print("Sending success response to CloudFormation")
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
            return
        
        # For direct Lambda invocations, return a standard response
        return {
            'statusCode': 200,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        
        # If this is a CloudFormation request, send a failure response
        if 'RequestType' in event:
            print("Sending failure response to CloudFormation")
            cfnresponse.send(event, context, cfnresponse.FAILED, {
                'Error': error_message
            })
        
        # For direct Lambda invocations, return an error response
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error importing data: {error_message}')
        }
