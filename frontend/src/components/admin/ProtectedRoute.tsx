import React from 'react';
import { Navigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAdminAuth } from '../../hooks/useAdminAuth';

interface ProtectedRouteProps {
  isAuthenticated?: boolean;
  isLoading?: boolean;
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  isAuthenticated: propIsAuthenticated,
  isLoading: propIsLoading,
  children,
}) => {
  const auth = useAdminAuth();

  const isAuthenticated =
    propIsAuthenticated !== undefined ? propIsAuthenticated : auth.isAuthenticated;
  const isLoading =
    propIsLoading !== undefined ? propIsLoading : auth.isLoading;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Loader2 className="w-8 h-8 text-uts-green-700 animate-spin" />
        <span className="text-sm text-slate-500 font-medium">Verificando sesión administrativa...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />;
  }

  return <>{children}</>;
};
