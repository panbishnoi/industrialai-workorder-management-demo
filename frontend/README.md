# Field Workforce Safety Assistant Frontend

This is the frontend application for the Field Workforce Safety Assistant.

## Development

To run the application locally:

```bash
npm install
npm run dev
```

## Environment Configuration

This application uses a runtime configuration approach to handle environment-specific settings:

1. In development mode:
   - The application uses environment variables from the `.env` file
   - This allows for local development without needing to deploy backend resources

2. In production mode:
   - The application loads configuration from `window.APP_CONFIG` provided by `/config.js`
   - This file is generated during deployment with the correct backend resource values
   - No rebuild is needed when backend resources change

## Building

To build the application:

```bash
npm run build
```

The build output will be in the `dist` directory.

## Configuration

The application requires the following configuration values:

- `VITE_API_ENDPOINT`: The endpoint for the main API
- `VITE_WORKORDER_API_ENDPOINT`: The endpoint for the work order API
- `VITE_REGION_NAME`: The AWS region
- `VITE_COGNITO_USER_POOL_ID`: The Cognito user pool ID
- `VITE_COGNITO_USER_POOL_CLIENT_ID`: The Cognito user pool client ID
- `VITE_COGNITO_IDENTITY_POOL_ID`: The Cognito identity pool ID
- `VITE_API_NAME`: The name of the main API (default: "RestAPI")
- `VITE_WorkOrder_API_NAME`: The name of the work order API (default: "WorkOrderAPI")
- `VITE_PROTOTYPE_NAME`: The name of the prototype (default: "WorkOrderSafetyDemo")
- `VITE_COGNITO_DOMAIN`: The Cognito domain suffix (default: ".auth.us-east-1.amazoncognito.com/")
