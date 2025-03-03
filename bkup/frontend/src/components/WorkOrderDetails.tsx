import { useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import '@components/WorkOrderDetails.css';
import 'leaflet/dist/leaflet.css';
import { postSafetyCheckRequest, pollSafetyCheckStatus, postEmergencyCheckRequest } from '@lib/api';
import { customAlphabet } from "nanoid";
import UnifiedMap from '@components/UnifiedMap';
import emergencyData from '@/emergencydata.json'; 
import { Emergency } from '@/types/emergency';
import {
  Container,
  Header,
  SpaceBetween,
  Button,
  StatusIndicator,
  Box,
  ExpandableSection,
} from "@cloudscape-design/components";

interface SafetyCheckResponse {
  requestId: string;
  status: string;
  safetycheckresponse: string;
}

interface LocationDetails {
  latitude: number;
  longitude: number;
}

interface WorkOrder {
  work_order_id: string;
  description: string;
  asset_id: string;
  scheduled_start_timestamp: string;
  scheduled_finish_timestamp: string;
  owner_name: string;
  status: string;
  priority: string;
  location_name: string;
  location_details?: LocationDetails;
  safetycheckresponse?: string;
}

const WorkOrderDetails = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const workOrder = location.state?.workOrder as WorkOrder;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLocationVisible, setIsLocationVisible] = useState(true);
  
  const [emergencies, setEmergencies] = useState<Emergency[]>([]);
  const [loadingEmergencies, setLoadingEmergencies] = useState(false);
  if (!workOrder) {
    return <div>No details found for this Work Order.</div>;
  }


  const performSafetyCheck = async () => {
    try {
      setLoading(true);
      const queryObject = {
        query: "Perform hazard safety and weather safety checks for WorkOrder::",
        workorderdetails: {
          work_order_id: workOrder.work_order_id,
          workOrderLocationAssetDetails: workOrder,
        },
        session_id: customAlphabet("1234567890", 20)()
      };

      const response = (await postSafetyCheckRequest(queryObject) as unknown) as SafetyCheckResponse;
      if (response?.requestId) {
        startPolling(response.requestId);
      }
    } catch (err) {
      setError('Failed to initiate safety check');
      setLoading(false);
    }
  };

  const performEmergencyCheck = async () => {
    try {
      setLoadingEmergencies(true);
            // Extract latitude and longitude
      const latitude = workOrder.location_details?.latitude;
      const longitude = workOrder.location_details?.longitude;

      // Validate that both latitude and longitude are defined
      if (latitude === undefined || longitude === undefined) {
        throw new Error('Work order location details are incomplete.');
      }
      const queryObject = {
          latitude: latitude,
          longitude: longitude,
        };

      const response = (await postEmergencyCheckRequest(queryObject) as unknown) as unknown;
      setEmergencies(response as Emergency[]);
      console.log(response);
    } catch (err) {
      setError('Failed to initiate safety check');
    } finally {
      setLoadingEmergencies(false);
    }
  };


  const checkStatus = async (requestId: string): Promise<boolean> => {
    try {
      const result = (await pollSafetyCheckStatus(requestId) as unknown) as SafetyCheckResponse;
      if (result?.status === 'COMPLETED') {

        workOrder.safetycheckresponse = result.safetycheckresponse

        setEmergencies(emergencyData as Emergency[]);
        setLoading(false);
        return true;
      }
      return false;
    } catch (err) {
      setError('Failed to fetch status');
      setLoading(false);
      return true;
    }
  };

  
  const startPolling = async (requestId: string) => {
    let attempts = 0;
    const maxAttempts = 20;
    const pollInterval = 3000;

    const poll = async () => {
      try {
        attempts++;
        const shouldStop = await checkStatus(requestId);
        if (!shouldStop && attempts < maxAttempts) {
          setTimeout(poll, pollInterval);
        } else if (attempts >= maxAttempts) {
          setError('Error in getting safety check response');
          setLoading(false);
        }
      } catch (error) {
        setError('Error in getting safety check response');
        setLoading(false);
      }
    };
    poll();
  };

  return (
    <SpaceBetween size="l">
      {/* Back Button */}
      <Button onClick={() => navigate("/")} variant="link">
        ← Back to List
      </Button>

      {/* Work Order Details */}
      <Container
        header={<Header>Work Order Details</Header>}
        footer={
          <Button
            variant="primary"
            loading={loading}
            onClick={performSafetyCheck}
          >
            Perform Safety Check
          </Button>
        }
      >
        <SpaceBetween size="m">
          <Box>
            <strong>ID:</strong> {workOrder.work_order_id}
          </Box>
          <Box>
            <strong>Description:</strong> {workOrder.description}
          </Box>
          <Box>
            <strong>Asset:</strong> {workOrder.asset_id}
          </Box>
          <Box>
            <strong>Scheduled Start:</strong>{" "}
            {new Date(workOrder.scheduled_start_timestamp).toLocaleString()}
          </Box>
          <Box>
            <strong>Scheduled Finish:</strong>{" "}
            {new Date(workOrder.scheduled_finish_timestamp).toLocaleString()}
          </Box>
          <Box>
            <strong>Status:</strong>{" "}
            <StatusIndicator
              type={
                workOrder.status === "Approved"
                  ? "success"
                  : workOrder.status === "In Progress"
                  ? "info"
                  : workOrder.status === "Pending"
                  ? "warning"
                  : "error"
              }
            >
              {workOrder.status}
            </StatusIndicator>
          </Box>
          <Box>
            <strong>Priority:</strong> {workOrder.priority}
          </Box>
        </SpaceBetween>
      </Container>

      {/* Location Section */}
      {workOrder.location_name && (
        <ExpandableSection
          headerText={
            <SpaceBetween direction="horizontal" size="xs">
              <span>Location Details</span>
          </SpaceBetween>
        }
          expanded={isLocationVisible}
          onChange={({ detail }) => setIsLocationVisible(detail.expanded)}
        >
          <SpaceBetween size="l">
          {isLocationVisible && (
            <>
            {workOrder.location_details?.latitude && workOrder.location_details?.longitude ? (
              <UnifiedMap 
              centerPoint={[
                workOrder.location_details?.longitude,
                workOrder.location_details?.latitude,
              ]}
              description={workOrder.location_name} 
              emergencies={emergencies}
                />
              ) : (
                "No location coordinates available."
              )}
            </>
          )}
          <Button
                variant="primary"
                loading={loadingEmergencies}
                onClick={performEmergencyCheck}
              >
                Load Emergency Warnings
            </Button>
          </SpaceBetween>
        </ExpandableSection>
      )}

      {/* Collapsible Location Section */}

        {error && <div className="safety-check-response">{error}</div>}
        {loading ? (
          <div className="safety-check-response">
            <p>Performing fresh safety check...</p>
          </div>
        ) : 
        (workOrder.safetycheckresponse) && (
          <div className="safety-check-response" 
            dangerouslySetInnerHTML={{ __html:
              workOrder.safetycheckresponse.replace(/^"|"$/g, '') // Remove leading and trailing quotes
              .replace(/\\n/g, '')   // Remove \n characters
              .replace(/\\u00b0C/g, '°C') // Replace \u00b0C with °C (escaped version)
              .replace(/\u00b0C/g, '°C')
               }} />
        )}

  </SpaceBetween>
  );
};


export default WorkOrderDetails;
