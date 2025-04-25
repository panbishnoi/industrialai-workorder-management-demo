# CDK Deployment for Field Workforce Safety Assistant

This directory contains the AWS CDK code for deploying the Field Workforce Safety Assistant application.

## Architecture

The application is structured as a parent stack with three nested stacks:

1. **BedrockAgentStack** - Creates Bedrock agents, DynamoDB tables, and Lambda functions
2. **BackendAPIStack** - Creates API Gateway, Cognito, and backend services
3. **FrontendStack** - Builds and deploys the frontend application

Using nested stacks provides these benefits:
- All resources are deployed and deleted together with the parent stack
- Backend and frontend stacks can be conditionally deployed
- Proper dependency management between stacks

## Runtime Configuration

The frontend application uses a runtime configuration approach to handle environment-specific settings. This solves the issue of needing backend resource information during the build process.

### How it works:

1. A placeholder `config.js` file is included in the frontend's public directory
2. During deployment, the CDK Lambda function:
   - Builds the frontend application
   - Generates a runtime `config.js` with actual backend resource values
   - Uploads both to the S3 bucket

3. When the application loads in the browser:
   - The `config.js` file is loaded before the application code
   - The application reads configuration from `window.APP_CONFIG` instead of environment variables

This approach allows:
- Building the frontend once and deploying to multiple environments
- Updating configuration without rebuilding the application
- Avoiding the need for backend resource information during the build process

## Deployment

To deploy the application:

```bash
# Install dependencies
npm install

# Deploy the application with all stacks
cdk deploy

# Deploy only the Bedrock Agents stack (without backend and frontend)
cdk deploy --context deploy_frontend=no
```

## Configuration

The application uses CDK context variables for configuration:

- `openweather_api_key` - API key for OpenWeather service
- `collaborator_foundation_model` - Foundation model for collaborator agents
- `supervisor_foundation_model` - Foundation model for supervisor agent
- `deploy_frontend` - Whether to deploy backend and frontend stacks (yes/no)

You can set these in cdk.json or pass them via command line:

```bash
cdk deploy --context openweather_api_key=YOUR_API_KEY --context deploy_frontend=yes
```

## Development

For local development, the application will fall back to using the `.env` file if `window.APP_CONFIG` is not available.
