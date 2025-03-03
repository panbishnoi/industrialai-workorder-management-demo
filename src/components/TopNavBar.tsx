"use client"
import React from 'react';
import { useState, useEffect } from "react";
import { useAuthenticator } from '@aws-amplify/ui-react';
import { useUserAttributes } from '@/components/UserAttributesProvider';
import {
  TopNavigation,
  Toggle
} from "@cloudscape-design/components";
import { applyMode, Mode } from "@cloudscape-design/global-styles";
import logoSmallTopNavigation from '@/a4e-logo.png';

const TopNavBar = () => {
  // const { signOut, authStatus } = useAuthenticator(context => [context.user, context.authStatus]);
  const { signOut } = useAuthenticator(context => [context.user]);
  // const [anchorElUser, setAnchorElUser] = React.useState<null | HTMLElement>(null);

  const { userAttributes } = useUserAttributes();

  // //TODO Impliment the dropdown menu for the user menu
  // const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
  //   setAnchorElUser(event.currentTarget);
  // };

  // const handleCloseUserMenu = () => {
  //   setAnchorElUser(null);
  // };

  // To support dark mode
  const [useDarkMode, setUseDarkMode] = useState(false);

  useEffect(() => {
    applyMode(useDarkMode ? Mode.Dark : Mode.Light);
  }, [useDarkMode]);

  return (
    <>
      <TopNavigation
        identity={{
          href: "/",
          title: "Agents4Energy",
          logo: {
            src: logoSmallTopNavigation.src,
            alt: "A4E"
          }
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
              { id: "profile", text: "Profile" },
              { id: "preferences", text: "Preferences" },
              { id: "security", text: "Security" },
              {
                id: "support-group",
                text: "Support",
                items: [
                  {
                    id: "documentation",
                    text: "Documentation",
                    href: "#",
                    external: true,
                    externalIconAriaLabel:
                      " (opens in new tab)"
                  },
                  { id: "support", text: "Support" },
                  {
                    id: "feedback",
                    text: "Feedback",
                    href: "#",
                    external: true,
                    externalIconAriaLabel:
                      " (opens in new tab)"
                  }
                ]
              },
              { id: "signout", text: "Sign out"}
            ]
          },
        ]}
      />
      <div className='dark-mode-toggle'>
        <Toggle
          onChange={({ detail }) => setUseDarkMode(detail.checked)}
          checked={useDarkMode}
        >
          Dark Mode
        </Toggle>
      </div>
    </>
  );
};

export default TopNavBar;