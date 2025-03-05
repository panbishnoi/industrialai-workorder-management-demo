export interface LocationDetails {
    location_name?: string;
    address?: string;
    description?: string;
    latitude?: string;
    longitude?: string;
  }
  
export interface WorkOrder {
    work_order_id: string;
    asset_id: string;
    description?: string;
    location_name?: string;
    owner_name?: string;
    priority?: number;
    safetyCheckPerformedAt?: string;
    safetycheckresponse?: string;
    scheduled_finish_timestamp?: string;
    scheduled_start_timestamp?: string;
    status?: string;
    location_details?: LocationDetails; // Nested object
}