import { useAuthenticator } from "@aws-amplify/ui-react";
import TopNavigation from "@cloudscape-design/components/top-navigation";

export default function NavBar() {
  const { user, signOut } = useAuthenticator((context) => [context.user]);
  const env = import.meta.env; // Vite environment variables



  return (
    <TopNavigation
      identity={{
        href: "/",
        title: env.VITE_APP_NAME || "My App", // App name from environment variables
      }}
      utilities={
        [
        {
            type: "button",
            text: user?.username || "User",
        },
        {
          type: "button",
          text: "Logout",
        
          onClick: signOut,
        }

      ]}
    />
  );
}
