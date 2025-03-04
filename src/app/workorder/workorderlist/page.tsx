"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { amplifyClient } from "@/utils/amplify-utils"; // Ensure this is correctly configured
import { Container, Header, Table } from "@cloudscape-design/components";
import "@aws-amplify/ui-react/styles.css";

interface WorkOrder {
  id: string;
  work_order_id: string;
  asset_id: string;
  description: string;
  location_name: string;
  owner_name: string;
  priority: number;
  safetyCheckPerformedAt: string;
  scheduled_start_timestamp: string;
  scheduled_finish_timestamp: string;
  status: string;
}

const WorkOrdersPage = () => {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch work orders from the backend
  useEffect(() => {
    const fetchWorkOrders = async () => {
      try {
        setLoading(true);
        const response = await amplifyClient.queries.fetchWorkOrders(); // Replace with your actual query
        setWorkOrders(response.data.fetchWorkOrders || []);
      } catch (err) {
        console.error("Error fetching work orders:", err);
        setError("Failed to load work orders.");
      } finally {
        setLoading(false);
      }
    };

    fetchWorkOrders();
  }, []);

  return (
    <Container
      header={<Header variant="h2">Work Orders</Header>}
    >
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
            { id: "priority", header: "Priority", cell: (item) => item.priority.toString() },
            { id: "status", header: "Status", cell: (item) => item.status },
          ]}
          items={workOrders}
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
