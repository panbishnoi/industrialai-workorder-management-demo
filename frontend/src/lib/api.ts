// Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.]
// SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
// Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import { Amplify } from "aws-amplify";
import { fetchAuthSession } from "aws-amplify/auth";
import { post } from "aws-amplify/api";
import { getErrorMessage } from "./utils";
import { QueryObject,EmergencyCheckQuery } from "@/types";
import { config } from "./config";

interface WorkOrderResponse {
  body: {
    json(): Promise<WorkOrder[]>;
  }
}

export interface WorkOrder {
  work_order_id: string;
  asset_id: string;
  description: string;
  location_name: string;
  owner_name: string;
  priority: number;
  safetycheckresponse: string
  safetyCheckPerformedAt: string;
  scheduled_start_timestamp: string;
  scheduled_finish_timestamp: string;
  status: string;
  location_details: {
    location_name: string;
    address: string;
    description: string;
    latitude: number;
    longitude: number;
  };
}

// Use runtime config instead of env variables
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: config.COGNITO_USER_POOL_ID,
      userPoolClientId: config.COGNITO_USER_POOL_CLIENT_ID,
      identityPoolId: config.COGNITO_IDENTITY_POOL_ID,
      loginWith: {
        oauth: {
          domain: config.COGNITO_DOMAIN,
          scopes: ["openid", "email"],
          redirectSignIn: [import.meta.env.VITE_APP_REDIRECT_SIGNIN_URL],
          redirectSignOut: [import.meta.env.VITE_APP_REDIRECT_SIGNOUT_URL],
          responseType: 'code',
        },
      },
    },
  },
});

const existingConfig = Amplify.getConfig();

Amplify.configure({
  ...existingConfig,
  API: {
    REST: {
      [config.API_NAME]: {
        endpoint: config.API_ENDPOINT,
        region: config.REGION_NAME,
      },
      [config.WorkOrder_API_NAME]:{
        endpoint: config.WORKORDER_API_ENDPOINT,
        region: config.REGION_NAME,
      },
    },
  },
});

// Create a function to get auth token
const getAuthToken = async () => {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (!token) {
      throw new Error('No auth token available');
    }
    return token;
  } catch (error) {
    console.error('Error getting auth token:', error);
    throw error;
  }
};
// Create a function to get REST input with fresh token
const getRestInput = async (apiName: string) => {
  const authToken = await getAuthToken();
  return {
    apiName,
    options: {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    },
  };
};


export async function postSafetyCheckRequest(queryObject: QueryObject) {
  try {
    const restInput = await getRestInput(config.API_NAME);
    const restOperation = post({
      ...restInput,
      path: `safetycheck/request`,
      options: {
        ...restInput.options,
        body: queryObject,
      },
    });
    console.log(restOperation)
    const response = await restOperation.response;
    console.log(response)
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
  }
}

interface WorkOrderResponse {
  body: {
    json(): Promise<WorkOrder[]>;
  }
}


export async function postWorkOrderQuery(): Promise<WorkOrder[]> {
  try {
    const restInput = await getRestInput(config.WorkOrder_API_NAME);
    const restOperation = post({
      ...restInput,
      path: `workorders`,
      options: {
        ...restInput.options,
        body: {} // Changed from empty string to empty object
      }
    });
    const response = await (restOperation.response as unknown) as WorkOrderResponse;
    
    // Add null check and provide default empty array
    return response.body.json() ?? [];
  } catch (e: unknown) {
    console.log("postWorkOrderQuery call failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function pollSafetyCheckStatus(requestId: string) {
  try {
      const restInput = await getRestInput(config.API_NAME);
      const restOperation = await post({
          ...restInput,
          path: `safetycheck/status`,
          options: {
              ...restInput.options,
              body: { requestId }
          }
      });
      const response = await restOperation.response;
    
      return response.body.json();
  } catch (e: unknown) {
      console.log("Status polling failed: ", getErrorMessage(e));
      throw e;
  }
}

export async function postEmergencyCheckRequest(queryObject: EmergencyCheckQuery) {
  try {
    const restInput = await getRestInput(config.API_NAME);
    const restOperation = post({
      ...restInput,
      path: `emergencycheck/request`,
      options: {
        ...restInput.options,
        body: queryObject,
      },
    });
    console.log(restOperation)
    const response = await restOperation.response;
    console.log(response)
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
  }
}