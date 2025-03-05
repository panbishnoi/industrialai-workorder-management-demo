"use client";
import { useRouter } from 'next/navigation';
import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { amplifyClient } from "@/utils/amplify-utils"; // Ensure this is correctly configured
import { Container, Header, Table, SpaceBetween, Box, StatusIndicator } from "@cloudscape-design/components";
import "@aws-amplify/ui-react/styles.css";
import { GraphQLResult } from "@aws-amplify/api-graphql";
import {WorkOrder, LocationDetails} from '@/types/workorder';



        

const WorkOrdersPage = () => {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch work orders from the backend
  useEffect(() => {
    const fetchWorkOrders = async () => {
      try {
        setLoading(true);
        // Define the GraphQL query with only required fields
        const query = `
          query FetchWorkOrders {
            fetchWorkOrders {
              work_order_id
              asset_id
              description
              location_name
              owner_name
              priority
              safetyCheckPerformedAt
              safetycheckresponse
              scheduled_finish_timestamp
              scheduled_start_timestamp
              status
              location_details {
                location_name  
                address
                description
                latitude
                longitude
              }
            }
          }
        `;
        const response = (await amplifyClient.graphql({ query })) as GraphQLResult<{ fetchWorkOrders: WorkOrder[] }>;

        if (response?.data && response.data?.fetchWorkOrders) {
            setWorkOrders(response.data.fetchWorkOrders as WorkOrder[]); // Cast response.data to WorkOrder[]
          }
      } catch (err) {
        console.error("Error fetching work orders:", err);
        setError("Failed to load work orders.");
      } finally {
        setLoading(false);
      }
    };

    fetchWorkOrders();
  }, []);

  const router = useRouter();
  // Custom StatusBadge component
  const StatusBadge = ({ status }: { status: string }) => {
    
    return <span><StatusIndicator
    type={
      status === "Approved"
        ? "success"
        : status === "In Progress"
        ? "info"
        : status === "Pending"
        ? "warning"
        : "error"
    }
    />
    {status}</span>;
  };

  return (
    
    <Container>
        <Box
          fontSize="display-l"
          fontWeight="bold"
          variant="h2"
          padding="n"
        >
        Workplace Safety Agent
                </Box>
                
      <Box
         variant="p"
         color="text-body-secondary"
          margin={{top:"xs", bottom: "xs" }}
        >
         Using Generative AI to perform Work Order Safety
       </Box>

      <SpaceBetween
          direction="horizontal"
          size="xs"
      ></SpaceBetween>
      {loading ? (
        <div>Loading...</div>
      ) : error ? (
        <div style={{ color: "red" }}>{error}</div>
      ) : (
        <Table
          columnDefinitions={[
            { id: "work_order_id", header: "Work Order ID", cell: (item) => item.work_order_id },
            { id: "asset_id", header: "Asset ID", cell: (item) => item.asset_id },
            { id: "description", header: "Description", cell: (item) => item.description },
            { id: "location_name", header: "Location", cell: (item) => item.location_name },
            { id: "owner_name", header: "Owner", cell: (item) => item.owner_name },
            { id: "priority", header: "Priority", cell: (item) => item.priority },
            { id: "status", header: "Status", cell: (item) => <StatusBadge status = {item.status!} /> },
          ]}
          items={workOrders}
          onRowClick={({ detail }) =>
          router.push(`/workorders/${detail.item.work_order_id}?workOrder=${encodeURIComponent(JSON.stringify(detail.item))}`)}
          loadingText="Loading work orders..."
          empty={
            <div style={{ textAlign: "center" }}>
              No work orders available.
            </div>
          }
          stickyHeader
        />
      )}
    </Container>
  );
};

export default WorkOrdersPage;
