import React, { createContext, useContext, useEffect, useState } from 'react';
import { setVentureId as setApiVentureId } from '../api/apiClient';

type VentureContextValue = {
  ventureId: string | null;
  setVentureId: (id: string | null) => void;
  userId: string | null;
  setUserId: (id: string | null) => void;
};

const VentureContext = createContext<VentureContextValue>({
  ventureId: null,
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  setVentureId: () => {},
  userId: null,
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  setUserId: () => {},
});

export const VentureProvider = ({ children }: { children: React.ReactNode }) => {
  const [ventureId, setVentureIdState] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    try {
      return window.localStorage.getItem('ventureId');
    } catch {
      return null;
    }
  });

  const [userId, setUserIdState] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    try {
      return window.localStorage.getItem('userId');
    } catch {
      return null;
    }
  });

  useEffect(() => {
    setApiVentureId(ventureId);
    if (typeof window === 'undefined') return;
    try {
      if (ventureId) {
        window.localStorage.setItem('ventureId', ventureId);
      } else {
        window.localStorage.removeItem('ventureId');
      }
    } catch {
      // ignore storage errors
    }
  }, [ventureId]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      if (userId) {
        window.localStorage.setItem('userId', userId);
      } else {
        window.localStorage.removeItem('userId');
      }
    } catch {
      // ignore storage errors
    }
  }, [userId]);

  const setVentureId = (id: string | null) => {
    setVentureIdState(id);
  };

  const setUserId = (id: string | null) => {
    setUserIdState(id);
  };

  return (
    <VentureContext.Provider value={{ ventureId, setVentureId, userId, setUserId }}>
      {children}
    </VentureContext.Provider>
  );
};

export const useVenture = () => useContext(VentureContext);
