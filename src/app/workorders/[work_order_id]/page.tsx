"use client";

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  Container,
  Header,
  SpaceBetween,
  Button,
  StatusIndicator,
  Box,
  ExpandableSection,
} from "@cloudscape-design/components";
import UnifiedMap from '@/components/UnifiedMap';
import {WorkOrder, LocationDetails} from '@/types/workorder';
import { Emergency } from '@/types/emergency';

const WorkOrderDetails = () => {
  const searchParams = useSearchParams(); 
  const router = useRouter();
  const [workOrder, setWorkOrder] = useState<WorkOrder | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLocationVisible, setIsLocationVisible] = useState(true);
  
  const [emergencies, setEmergencies] = useState<Emergency[]>([]);
  const [loadingEmergencies, setLoadingEmergencies] = useState(false);
  useEffect(() => {
    const workOrderParam = searchParams.get('workOrder');
    if (workOrderParam) {
      const parsedData = JSON.parse(workOrderParam);
      setWorkOrder(parsedData);
    }
  }, [searchParams]);

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
//        session_id: customAlphabet("1234567890", 20)()
      };

    //      const response = (await postSafetyCheckRequest(queryObject) as unknown) as SafetyCheckResponse;
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

      //const response = (await postEmergencyCheckRequest(queryObject) as unknown) as unknown;
     // setEmergencies(response as Emergency[]);
      //console.log(response);
    } catch (err) {
      setError('Failed to initiate safety check');
    } finally {
      setLoadingEmergencies(false);
    }
  };

  const lat = parseFloat(workOrder.location_details?.latitude || "0");
  const lng = parseFloat(workOrder.location_details?.longitude || "0");


  return (
    <SpaceBetween size="l">
      {/* Back Button */}
      <Button onClick={() => router.push('/workorders')} variant="link">← Back to List</Button>

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
            {workOrder.scheduled_start_timestamp}
          </Box>
          <Box>
            <strong>Scheduled Finish:</strong>{" "}
            {workOrder.scheduled_finish_timestamp}
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
                lat,
                lng,
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
