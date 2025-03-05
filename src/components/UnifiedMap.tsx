"use client";

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

// Import the UnifiedMapProps type
import { UnifiedMapProps } from '@/types/emergency';

// Dynamically import the map component with no SSR
const MapComponent = dynamic(
  () => import('@/components/MapComponent'), 
  { 
    ssr: false,
    loading: () => <div style={{ height: '500px', width: '100%', background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading map...</div>
  }
);

const UnifiedMap = (props: UnifiedMapProps) => {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) return null;

  return <MapComponent {...props} />;
};

export default UnifiedMap;
