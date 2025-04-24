import json
import urllib3
import logging
import os
from datetime import datetime, timedelta

log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    format="[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

FUNCTION_NAMES = []

try:
    # Get API key from environment variable
    API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY")
    if API_KEY:
        FUNCTION_NAMES.append("weatherforecast")
except Exception as e:
    print(f"Exception: {e}")

def weatherforecast(lat, long, target_datetime):
    try:
        # Parse the target datetime
        target_dt = datetime.fromisoformat(target_datetime.replace('Z', '+00:00'))
        current_dt = datetime.utcnow()
        
        # Calculate the difference in days
        days_diff = (target_dt - current_dt).days
        
        # Choose the appropriate API endpoint based on the forecast timeframe
        if days_diff <= 0:  # Current weather
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={long}&appid={API_KEY}&units=metric"
            http = urllib3.PoolManager()
            response = http.request('GET', url)
            data = json.loads(response.data.decode('utf-8'))
            
            weather_info = {
                'datetime': current_dt.isoformat(),
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed'],
                'weather_condition': data['weather'][0]['main'],
                'weather_description': data['weather'][0]['description']
            }
            
        elif days_diff <= 5:  # 5-day forecast (3-hour intervals)
            url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={long}&appid={API_KEY}&units=metric"
            http = urllib3.PoolManager()
            response = http.request('GET', url)
            data = json.loads(response.data.decode('utf-8'))
            
            # Find the closest forecast time
            closest_forecast = None
            min_time_diff = float('inf')
            
            for forecast in data['list']:
                forecast_time = datetime.fromtimestamp(forecast['dt'])
                time_diff = abs((forecast_time - target_dt).total_seconds())
                
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_forecast = forecast
            
            if closest_forecast:
                weather_info = {
                    'datetime': datetime.fromtimestamp(closest_forecast['dt']).isoformat(),
                    'temperature': closest_forecast['main']['temp'],
                    'feels_like': closest_forecast['main']['feels_like'],
                    'humidity': closest_forecast['main']['humidity'],
                    'wind_speed': closest_forecast['wind']['speed'],
                    'weather_condition': closest_forecast['weather'][0]['main'],
                    'weather_description': closest_forecast['weather'][0]['description']
                }
            else:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': 'No forecast available for the specified date'})
                }
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Forecast only available for up to 5 days'})
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(weather_info)
        }
        
    except Exception as e:
        logger.error(f"Error in weatherforecast: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error fetching weather data: {str(e)}'})
        }

def lambda_handler(event, context):
    logging.info(f"{event=}")

    agent = event["agent"]
    actionGroup = event["actionGroup"]
    function = event["function"]
    parameters = event.get("parameters", [])
    responseBody = {"TEXT": {"body": "Error, no function was called"}}

    logger.info(f"{actionGroup=}, {function=}, {parameters=}")

    if function in FUNCTION_NAMES:
        if function == "weatherforecast":
            lat = None
            long = None
            target_datetime = None

            for param in parameters:
                if param["name"] == "lat":
                    lat = param["value"]
                elif param["name"] == "long":
                    long = param["value"]
                elif param["name"] == "target_datetime":
                    target_datetime = param["value"]

            if not lat or not long or not target_datetime:
                missing_params = []
                if not lat:
                    missing_params.append("lat")
                if not long:
                    missing_params.append("long")
                if not target_datetime:
                    missing_params.append("target_datetime")
                    
                responseBody = {
                    "TEXT": {"body": f"Missing mandatory parameter(s): {', '.join(missing_params)}"}
                }
            else:
                weather_response = weatherforecast(lat, long, target_datetime)
                logger.debug(f"Weather forecast: {weather_response=}")
                responseBody = {
                    "TEXT": {
                        "body": f"Weather forecast for coordinates ({lat}, {long}) at {target_datetime}: {weather_response['body']}"
                    }
                }

    action_response = {
        "actionGroup": actionGroup,
        "function": function,
        "functionResponse": {"responseBody": responseBody},
    }

    function_response = {
        "response": action_response,
        "messageVersion": event["messageVersion"],
    }

    logger.debug(f"lambda_handler: {function_response=}")

    return function_response