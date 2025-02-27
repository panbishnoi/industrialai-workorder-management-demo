import { useAuthenticator } from "@aws-amplify/ui-react";
import TopNavigation from "@cloudscape-design/components/top-navigation";
import { useEffect, useState } from "react";
import { fetchUserAttributes, type FetchUserAttributesOutput } from "aws-amplify/auth";

export default function NavBar() {
  const { user, signOut } = useAuthenticator((context) => [context.user]);
  const env = import.meta.env; // Vite environment variables
  
  // Update the type to match fetchUserAttributes output
  const [userAttributes, setUserAttributes] = useState<FetchUserAttributesOutput>({});

  // Extract user details with type assertion to fix TypeScript error
  const username = user?.username || "User";
  const emailFromTypeAssertion = (user as any)?.attributes?.email || "";

  // Alternative approach using fetchUserAttributes
  useEffect(() => {
    async function getUserAttributes() {
      try {
        const attributes = await fetchUserAttributes();
        setUserAttributes(attributes);
      } catch (error) {
        console.log('Error fetching user attributes:', error);
      }
    }
    
    if (user) {
      getUserAttributes();
    }
  }, [user]);

  // Use email from fetchUserAttributes (preferred) or fallback to type assertion approach
  const email = userAttributes.email || emailFromTypeAssertion || "";

  return (
    <TopNavigation
      identity={{
        href: "/",
        title: "Field Workforce safety assistant",
      }}
      utilities={[
        {
          type: "menu-dropdown",
          text: userAttributes?.email || "Customer Name",
          description: userAttributes?.email || "email@example.com",
          iconName: "user-profile",
          onItemClick: (item) => {
            if (item.detail.id === 'signout') signOut()
          },
          items: [
            { id: "signout", text: "Sign out" }
          ]
        }
      ]}
    />
  );
}