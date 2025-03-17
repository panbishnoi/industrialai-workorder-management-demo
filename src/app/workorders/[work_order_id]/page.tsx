"use client";

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState, useRef } from 'react';
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
import { amplifyClient, getMessageCatigory } from "@/utils/amplify-utils"; // Ensure this is correctly configured
import type { Schema } from '@/../amplify/data/resource';
import { createChatSession } from "@/../amplify/functions/graphql/mutations";
import ReactMarkdown from "react-markdown";
const WorkOrderDetails = () => {
  const searchParams = useSearchParams(); 
  const router = useRouter();
  const [workOrder, setWorkOrder] = useState<WorkOrder | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLocationVisible, setIsLocationVisible] = useState(true);
  
  const [emergencies, setEmergencies] = useState<Emergency[]>([]);
  const [loadingEmergencies, setLoadingEmergencies] = useState(false);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  
  const [safetyAgentResponse, setSafetyAgentResponse] = useState(""); // For real-time updates

  const [formattedResponse, setFormattedResponse] = useState<Chunk[]>([]); // Correctly typed state
  const [messages, setMessages] = useState<Array<Schema["ChatMessage"]["createType"]>>([]);
  // Use a ref to store the subscription object
  const subscriptionRef = useRef<any>(null);
  const [isSubscriptionActive, setIsSubscriptionActive] = useState(false); // Track subscription status
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

 
  interface Chunk {
    index: number; // Index of the chunk
    content: string; // Content of the chunk
  }
  
    
  const subscribeToUpdates = (chatSessionId: string) => {
    if (!chatSessionId) return;
  
    // Set subscription as active
    setIsSubscriptionActive(true);
  
    // Initialize with a placeholder chunk (like the chat implementation does)
    setFormattedResponse([{
      index: -1,
      content: ""
    }]);
  
    // Subscribe to updates
    subscriptionRef.current = amplifyClient.subscriptions
      .recieveResponseStreamChunk({ chatSessionId })
      .subscribe({
        next: (newChunk) => {
          console.log("Received chunk:", newChunk);
          
          setFormattedResponse((prevStream) => {
            // Determine the chunk index - if not provided, use position after last chunk
            const chunkIndex = (typeof newChunk.index === 'undefined' || newChunk.index === null)
              ? (prevStream.length > 0 ? Math.max(...prevStream.map(c => c.index)) + 1 : 0)
              : newChunk.index;
              
            // Create a copy of the previous stream to avoid direct mutation
            const newStream = [...prevStream];
            
            // Format the new chunk
            const formattedNewChunk = {
              index: chunkIndex,
              content: newChunk.chunk
            };
            
            // Find if this index already exists
            const existingIndex = newStream.findIndex(item => item.index === chunkIndex);
            
            // Find the position where this chunk should be inserted (based on index)
            const insertPosition = newStream.findIndex(item => item.index > chunkIndex);
            
            if (existingIndex !== -1) {
              // Replace existing chunk with the same index
              newStream[existingIndex] = formattedNewChunk;
            } else if (insertPosition === -1) {
              // If no larger index found, append to end
              newStream.push(formattedNewChunk);
            } else {
              // Insert at the correct position to maintain order
              newStream.splice(insertPosition, 0, formattedNewChunk);
            }
            
            // Sort chunks by index to ensure proper order
            // This is a safety measure in case chunks arrive out of order
            return newStream.sort((a, b) => a.index - b.index);
          });
        },
        error: (err) => {
          console.error("Error in subscription:", err);
          setError("Failed to receive real-time updates.");
          setIsSubscriptionActive(false);
        },
        complete: () => {
          console.log("Subscription completed.");
          setIsSubscriptionActive(false);
        },
      });
  
    // Add timeout handling for subscription
    const subscriptionTimeoutId = setTimeout(() => {
      console.log("Subscription timeout reached");
      if (subscriptionRef.current) {
        subscriptionRef.current.unsubscribe();
        subscriptionRef.current = null;
      }
      setIsSubscriptionActive(false);
    }, 60000); // 60 seconds timeout
  
    return () => {
      clearTimeout(subscriptionTimeoutId);
      if (subscriptionRef.current) {
        console.log("Unsubscribing from updates");
        subscriptionRef.current.unsubscribe();
        subscriptionRef.current = null;
      }
      setIsSubscriptionActive(false);
    };
  };

const combineAndSortMessages = ((arr1: Array<Message>, arr2: Array<Message>) => {
    const combinedMessages = [...arr1, ...arr2]
    const uniqueMessages = combinedMessages.filter((message, index, self) =>
        index === self.findIndex((p) => p.id === message.id)
    );
    return uniqueMessages.sort((a, b) => {
        if (!a.createdAt || !b.createdAt) throw new Error("createdAt is missing")
        return a.createdAt.localeCompare(b.createdAt)
    });
})  

const subscribeToChatUpdates = (chatSessionId: string) => {
            const sub = amplifyClient.models.ChatMessage.observeQuery({
                filter: {
                    chatSessionId: { eq: chatSessionId }
                }
            }).subscribe({
                next: ({ items }) => { //isSynced is an option here to
                    setMessages((prevMessages) => {
                        //If the message has type plot, attach the previous tool_table_events and tool_table_trend messages to it.
                        const sortedMessages = combineAndSortMessages(prevMessages, items)

                        const sortedMessageWithPlotContext = sortedMessages.map((message, index) => {
                            const messageCatigory = getMessageCatigory(message)
                            if (messageCatigory === 'tool_plot') {
                                //Get the messages with a lower index than the tool_plot's index
                                const earlierMessages = sortedMessages.slice(0, index).reverse()

                                const earlierEventsTable = earlierMessages.find((previousMessage) => {
                                    const previousMessageCatigory = getMessageCatigory(previousMessage)
                                    return previousMessageCatigory === 'tool_table_events'
                                })

                                const earlierTrendTable = earlierMessages.find((previousMessage) => {
                                    const previousMessageCatigory = getMessageCatigory(previousMessage)
                                    return previousMessageCatigory === 'tool_table_trend'
                                })

                                return {
                                    ...message,
                                    previousTrendTableMessage: earlierTrendTable,
                                    previousEventTableMessage: earlierEventsTable
                                }
                            } else return message
                        })
                        console.log("@@@@@",sortedMessageWithPlotContext)
                        return sortedMessageWithPlotContext
                    })
                }
            }
            )
            return () => sub.unsubscribe();
  };

  // Perform safety check and invoke Bedrock Agent
  const performSafetyCheck = async () => {
    try {
      setLoading(true);
      setError(null);
      setSafetyAgentResponse(""); // Clear previous response
      setFormattedResponse([]); // Clear formatted response
      // Create a sanitized version of the work order without the safety check fields
      const sanitizedWorkOrder = { ...workOrder };
      delete sanitizedWorkOrder.safetycheckresponse;
      delete sanitizedWorkOrder.safetyCheckPerformedAt;
      //const prompt = `Perform weather, hazard, and emergency checks for WorkOrder ID ${workOrder?.work_order_id}.`;
    // Create a prompt that includes the work order details
    // Create a prompt that includes the work order details
    const prompt = `Perform weather, hazard, and emergency checks for the following work order:
                    ${JSON.stringify(sanitizedWorkOrder, null, 2)}
                    Please analyze potential safety risks, weather conditions, and any emergency situations that might affect this work order.`;

      // Create a new chat session
      const testChatSession = await amplifyClient.graphql({
        query: createChatSession,
        variables: { input: {} },
      });

      const newChatSessionId = testChatSession.data.createChatSession.id;
      if (!newChatSessionId) throw new Error("Failed to create chat session");

      setChatSessionId(newChatSessionId);

     // Call the subscription function
    subscribeToUpdates(newChatSessionId);      
    subscribeToChatUpdates(newChatSessionId);
      // Fire-and-forget invocation of Bedrock Agent
     await amplifyClient.queries
        .invokeBedrockAgent({
          prompt,
          agentId: "OKXTFRR08S",
          agentAliasId: "KZENI6GIPM",
          chatSessionId: newChatSessionId,
        })
        .then(() => {
          console.log("Safety check initiated successfully.");
        })
        .catch((err) => {
          console.error("Error invoking Bedrock Agent:", err);
          setError("Failed to invoke Bedrock Agent.");
        });
    } catch (err) {
      console.error("Error performing safety check:", err);
      setError("Failed to initiate safety check.");
    } finally {
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
                lng,
                lat,
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

    <ExpandableSection headerText="Safety Agent Response" expanded={true}>
    {isSubscriptionActive ? (
        formattedResponse.length > 0 ? (
        <div
        className="messages"
        role="region"
        aria-label="Chat"
        style={{
            overflowY: 'auto', // Enable vertical scrolling
            height: '100%',    // Take full height
            padding: '16px',   // Add padding for better spacing
            backgroundColor: '#f9f9f9', // Light background for better readability
            borderRadius: '8px', // Rounded corners for a clean look
            border: '1px solid #ddd', // Subtle border for separation
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}
        >        
         <div className="prose !max-w-none w-full" >
            {formattedResponse.map((chunk) => (
                <ReactMarkdown key={chunk.index}>{chunk.content}</ReactMarkdown>            
            ))}
        </div>
        </div>
        ) : (
        <Box>Waiting for response...</Box>
        )
    ) : workOrder?.safetycheckresponse ? (
        <div className="safety-check-response"
            dangerouslySetInnerHTML={{ __html:
            workOrder.safetycheckresponse.replace(/^"|"$/g, '') // Remove leading and trailing quotes
            .replace(/\\n/g, '') // Remove \n characters
            .replace(/\\u00b0C/g, '°C') // Replace \u00b0C with °C (escaped version)
            .replace(/\u00b0C/g, '°C')
            }} />

    ) : (
        <Box>No safety check response available.</Box>
    )}
    </ExpandableSection>


  </SpaceBetween>
  );
};

export default WorkOrderDetails;
