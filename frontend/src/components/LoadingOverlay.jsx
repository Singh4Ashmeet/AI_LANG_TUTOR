import React from 'react';
import { useAuth } from '../context/AuthContext';

const LoadingOverlay = () => {
  const { isLoading } = useAuth();
  if (!isLoading) return null;
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white'
    }}>
      Loading...
    </div>
  );
};

export default LoadingOverlay;
