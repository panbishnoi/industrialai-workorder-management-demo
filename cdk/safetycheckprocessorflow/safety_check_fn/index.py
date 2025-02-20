import os
import json
import functools
import boto3
import traceback
import re
import time
from datetime import datetime
from collections import OrderedDict
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.config import Config
from aws_lambda_powertools import Logger

logger = Logger()
def log(message):
    logger.info(message)

AGENT_ID = os.getenv("AGENT_ID")
AGENT_ALIAS_ID = os.getenv("AGENT_ALIAS_ID")
WORK_ORDER_REQUEST_TABLE_NAME = os.getenv("WORK_ORDER_REQUEST_TABLE_NAME")
WORK_ORDER_TABLE_NAME = os.getenv("WORK_ORDER_TABLE_NAME")
# Initialize DynamoDB 
dynamodb = boto3.resource('dynamodb')
bedrock_agent_runtime_client = boto3.client(
        'bedrock-agent-runtime',
        config=Config(
            retries=dict(
                max_attempts=3,
                mode='adaptive'
            ),
            read_timeout=120,
            connect_timeout=5
        )
)

def get_agent_response(response):
    logger.info(f"Getting agent response... {response}")
    if "completion" not in response:
        return f"No completion found in response: {response}"

    for event in response["completion"]:
        log(f"Event keys: {event.keys()}")

        # Extract the traces
        if "chunk" in event:
            # Extract the bytes from the chunk
            chunk_bytes = event["chunk"]["bytes"]

            # Convert bytes to string, assuming UTF-8 encoding
            chunk_text = chunk_bytes.decode("utf-8")

            # Print the response text
            print("Response from the agent:", chunk_text)
            # If there are citations with more detailed responses, print them
            if (
                "attribution" in event["chunk"]
                and "citations" in event["chunk"]["attribution"]
            ):
                for citation in event["chunk"]["attribution"]["citations"]:
                    if (
                        "generatedResponsePart" in citation
                        and "textResponsePart" in citation["generatedResponsePart"]
                    ):
                        text_part = citation["generatedResponsePart"][
                            "textResponsePart"
                        ]["text"]
                        print("Detailed response part:", text_part)


    return chunk_text


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, _context: LambdaContext):
    """
    Lambda function to classify an image
    @param event:
    @param context:
    @return:
    """

    print("Invoke safety check function")

    print("The event")
    print(event)

    ddsafetycheckrequesttable = dynamodb.Table(WORK_ORDER_REQUEST_TABLE_NAME)
    ddworkordertable = dynamodb.Table(WORK_ORDER_TABLE_NAME)
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            request_id = record['dynamodb']['NewImage']['requestId']['S']
            work_order_id = record['dynamodb']['NewImage']['work_order_id']['S']
            payload = record['dynamodb']['NewImage']['payload']['S']

            logger.info(payload)
            try:
                # invoke the agent API
                agentResponse = bedrock_agent_runtime_client.invoke_agent(
                inputText=payload,
                agentId=AGENT_ID,
                agentAliasId=AGENT_ALIAS_ID,
                sessionId=request_id,
                enableTrace=False,
                endSession=False
                )
                response = get_agent_response(agentResponse)

                ddsafetycheckrequesttable.update_item(
                    Key={
                        'requestId': request_id
                    },
                    UpdateExpression='SET #status = :status, #safetycheckresponse = :safetycheckresponse, #updatedAt = :updatedAt',
                    ExpressionAttributeNames={
                        '#status': 'status',
                        '#safetycheckresponse': 'safetycheckresponse',
                        '#updatedAt': 'updatedAt'
                    },
                    ExpressionAttributeValues={
                        ':status': 'COMPLETED',
                        ':safetycheckresponse': json.dumps(response),
                        ':updatedAt': datetime.utcnow().isoformat()
                    }
                )

                # Update work order table with safety check response
                ddworkordertable.update_item(
                    Key={
                        'work_order_id': work_order_id
                    },
                    UpdateExpression='SET #safetycheckresponse = :safetycheckresponse, #safetyCheckPerformedAt = :safetyCheckPerformedAt',
                    ExpressionAttributeNames={
                        '#safetycheckresponse': 'safetycheckresponse',
                        '#safetyCheckPerformedAt': 'safetyCheckPerformedAt'
                    },
                    ExpressionAttributeValues={
                        ':safetycheckresponse': json.dumps(response),
                        ':safetyCheckPerformedAt': datetime.utcnow().isoformat()
                    }
                )

            except Exception as e:
                logger.info(e)

    