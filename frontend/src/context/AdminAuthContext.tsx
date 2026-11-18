import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { checkAdminSession, loginAdmin, logoutAdmin } from '../api/admin';
import { setUnauthorizedHandler } from '../api/client';

export type AuthStatus = 'checking' | 'authenticated' | 'unauthenticated';

export interface AdminAuthContextType {
  authStatus: AuthStatus;
  isAuthenticated: boolean;
  isLoading: boolean;
  authError: string | null;
  login: (adminKey: string) => Promise<boolean>;
  logout: () => Promise<void>;
  verifySession: () => Promise<boolean>;
}

export const AdminAuthContext = createContext<AdminAuthContextType | null>(null);

const fallbackAuthContext: AdminAuthContextType = {
  authStatus: 'unauthenticated',
  isAuthenticated: false,
  isLoading: false,
  authError: null,
  login: async () => false,
  logout: async () => {},
  verifySession: async () => false,
};

export interface AdminAuthProviderProps {
  children: React.ReactNode;
}

export const AdminAuthProvider: React.FC<AdminAuthProviderProps> = ({ children }) => {
  const [authStatus, setAuthStatus] = useState<AuthStatus>('checking');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const verifySession = useCallback(async (): Promise<boolean> => {
    setAuthStatus('checking');
    setAuthError(null);
    try {
      const res = await checkAdminSession();
      if (res && res.authenticated) {
        setAuthStatus('authenticated');
        return true;
      } else {
        setAuthStatus('unauthenticated');
        return false;
      }
    } catch {
      setAuthStatus('unauthenticated');
      return false;
    }
  }, []);

  useEffect(() => {
    verifySession();
  }, [verifySession]);

  // Manejo de expiración de sesión vía código 401 en llamadas protegidas
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setAuthStatus('unauthenticated');
    });
    return () => {
      setUnauthorizedHandler(null);
    };
  }, []);

  const login = useCallback(async (adminKey: string): Promise<boolean> => {
    setIsSubmitting(true);
    setAuthError(null);
    try {
      await loginAdmin(adminKey);
      setAuthStatus('authenticated');
      setAuthError(null);
      return true;
    } catch (err: any) {
      setAuthStatus('unauthenticated');
      setAuthError(err.message || 'Clave administrativa incorrecta.');
      return false;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    // 1. Invalida inmediatamente el estado de autenticación en memoria
    setAuthStatus('unauthenticated');
    setAuthError(null);
    try {
      // 2. Invalida la cookie de sesión en el backend FastAPI
      await logoutAdmin();
    } catch {
      // Si falla la red durante logout, el estado en memoria ya fue invalidado
    }
  }, []);

  const isAuthenticated = authStatus === 'authenticated';
  const isLoading = authStatus === 'checking' || isSubmitting;

  const value = useMemo<AdminAuthContextType>(
    () => ({
      authStatus,
      isAuthenticated,
      isLoading,
      authError,
      login,
      logout,
      verifySession,
    }),
    [authStatus, isAuthenticated, isLoading, authError, login, logout, verifySession]
  );

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  );
};

export function useAdminAuth(): AdminAuthContextType {
  const context = useContext(AdminAuthContext);
  if (!context) {
    return fallbackAuthContext;
  }
  return context;
}
