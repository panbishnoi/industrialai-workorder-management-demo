# CDK Deployment for Field Workforce Safety Assistant

This directory contains the AWS CDK code for deploying the Field Workforce Safety Assistant application.

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

# Deploy the application
cdk deploy --all
```

## Development

For local development, the application will fall back to using the `.env` file if `window.APP_CONFIG` is not available.
