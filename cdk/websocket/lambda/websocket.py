import json
import os
import boto3
import time
import requests
from datetime import datetime
import functools
import traceback
import re
from collections import OrderedDict
from boto3.dynamodb.conditions import Key
from jose import jwt
from aws_lambda_powertools import Logger

# Initialize services and constants
logger = Logger()
def log(message):
    logger.info(message)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['WS_CONNECTION_TABLE_NAME'])

# Environment variables
REGION = os.environ.get("REGION", "us-east-1")
USER_POOL_ID = os.environ.get("USER_POOL_ID", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")
AGENT_ALIAS_ID = os.getenv("AGENT_ALIAS_ID")
AGENT_ID = os.getenv("AGENT_ID")

def verify_token(token: str) -> dict:
    url = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"
    response = requests.get(url)
    keys = response.json()["keys"]
    header = jwt.get_unverified_header(token)
    key = [k for k in keys if k["kid"] == header["kid"]][0]
    
    decoded = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        options={"verify_at_hash": False},
        audience=CLIENT_ID,
    )
    return decoded

def handle_connect(connection_id):
    try:
        logger.info("adding new connection entry to dynamo for ",connection_id)
        table.put_item(
            Item={
                'connectionId': connection_id,
                'ttl': int(time.time()) + 10 * 60,  # 24 hour TTL
                'timestamp': str(datetime.now())
            }
        )
        return {'statusCode': 200, 'body': 'Connected'}
    except Exception as e:
        logger.error(f"Connection handling error: {str(e)}")
        return {'statusCode': 200, 'body': 'Connected'}
        #return {'statusCode': 500, 'body': 'Failed to connect'}

def handle_disconnect(connection_id):
    try:
        table.delete_item(Key={'connectionId': connection_id})
        return {'statusCode': 200, 'body': 'Disconnected'}
    except Exception as e:
        logger.error(f"Disconnect handling error: {str(e)}")
        #return {'statusCode': 500, 'body': 'Failed to disconnect'}
        return {'statusCode': 200, 'body': 'Disconnected'}

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

def handle_message(api_client, connection_id, event):
    try:
        body = json.loads(event['body'])
        data = body['data']

        session_id = body['sessionId']
    
        # Convert the data dictionary to a JSON string
        data_string = json.dumps(data)
    
        # Create your query string
        query = f'Perform Work Order Safety and Weather checks for the data shared in json:::{data_string}'
        
        print("performing weather and safety checks for ::",query)
        bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')
        # invoke the agent API
        agentResponse = bedrock_agent_runtime_client.invoke_agent(
            inputText=query,
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            enableTrace=False,
            endSession=False
        )
        response = get_agent_response(agentResponse)

        api_client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps({
                        'message': response,
                        'sender': connection_id,
                        'timestamp': str(datetime.now())
                    }))
        
             
        return {'statusCode': 200, 'body': 'Message sent'}
    except json.JSONDecodeError:
        return {'statusCode': 400, 'body': 'Invalid message format'}
    except Exception as e:
        logger.error(f"Message handling error: {str(e)}")
        return {'statusCode': 500, 'body': 'Failed to process message'}


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        # Log the incoming event for debugging
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Safely get requestContext or raise a more descriptive error
        if 'requestContext' not in event:
            logger.error(f"Missing requestContext in event: {event}")
            return {'statusCode': 400, 'body': 'Invalid WebSocket event structure'}
            
        request_context = event['requestContext']
        route_key = request_context.get('routeKey')
        connection_id = request_context.get('connectionId')
        
        if not route_key or not connection_id:
            logger.error(f"Missing required fields in requestContext: {request_context}")
            return {'statusCode': 400, 'body': 'Missing required WebSocket fields'}

        if route_key == '$connect':
            logger.info("connected")
            return handle_connect(connection_id)
        elif route_key == '$disconnect':
            logger.info("disconnected")
            return handle_disconnect(connection_id)
        elif route_key == '$default':
            # Initialize API client only if needed

            # Extract the message from the event
            message = json.loads(event['body'])
            
            # Check if the message is a heartbeat
            if message.get('messageType') == 'heartbeat':
                return {
                    'statusCode': 200,
                    'body': json.dumps({'message': 'Heartbeat received, no action taken'})
                }       
            #process other messages     
            api_client = None
            logger.info("inside process messages for default")
            if request_context.get('domainName') and request_context.get('stage'):
                domain_name = request_context['domainName']
                stage = request_context['stage']
                api_client = boto3.client(
                    'apigatewaymanagementapi',
                    endpoint_url=f'https://{domain_name}/{stage}'
                )
        
            if not api_client:
                return {'statusCode': 500, 'body': 'Failed to initialize API client'}
                
            try:
                body = json.loads(event.get("body", "{}"))
                token = body.get("token")
                if not token:
                    return {'statusCode': 403, 'body': 'Token is required'}
                decoded = verify_token(token)
                logger.info("valid token!!!",decoded)

                return handle_message(api_client, connection_id, event)
            except json.JSONDecodeError:
                return {'statusCode': 400, 'body': 'Invalid JSON in request body'}
            except Exception as e:
                logger.error(f"Token verification failed: {str(e)}")
                return {'statusCode': 403, 'body': 'Invalid Token'}
        else:
            return {'statusCode': 400, 'body': f'Unsupported route: {route_key}'}
            
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {'statusCode': 500, 'body': str(e)}

