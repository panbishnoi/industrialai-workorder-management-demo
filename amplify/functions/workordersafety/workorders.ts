import { DynamoDB } from 'aws-sdk';

// Initialize the DynamoDB Document Client
const dynamodb = new DynamoDB.DocumentClient();

// Access environment variables
const workOrderTableName = process.env.WorkOrderTableName!;
const locationTableName = process.env.LocationTableName!;

// Define the handler for the Lambda function
export const handler = async () => {
  try {
    // Fetch work orders from DynamoDB
    const workOrdersResponse = await dynamodb.scan({ TableName: workOrderTableName }).promise();
    const workOrders = workOrdersResponse.Items || [];

    // Fetch locations from DynamoDB
    const locationsResponse = await dynamodb.scan({ TableName: locationTableName }).promise();
    const locations = (locationsResponse.Items || []).reduce((acc: any, loc: any) => {
      if (loc.location_name) {
        acc[loc.location_name] = loc; // Ensure location_name exists
      }
      return acc;
    }, {} as Record<string, any>);

    // Add location details to each work order
    for (const order of workOrders) {
      const locationName = order.location_name;
      order.location_details = locations[locationName] || null; // Handle missing location details
    }

    // Sort work orders by 'work_order_id'
    const sortedWorkOrders = workOrders.sort((a:any, b:any) => 
      (a.work_order_id > b.work_order_id ? 1 : -1)
    );
    
    console.log('The sorted workorders are:', sortedWorkOrders);


    return sortedWorkOrders; // Return the sorted list of work orders
  } catch (error) {
    console.error('Error querying DynamoDB:', error);
    throw new Error('Failed to fetch work orders'); // Throw a new error with a message
  }
};
