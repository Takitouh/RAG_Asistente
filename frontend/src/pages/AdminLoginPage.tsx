import React, { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { Lock, Shield, AlertCircle, ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useAdminAuth } from '../hooks/useAdminAuth';

export const AdminLoginPage: React.FC = () => {
  const [adminKey, setAdminKey] = useState('');
  const { authStatus, isAuthenticated, isLoading, authError, login } = useAdminAuth();
  const navigate = useNavigate();

  // Durante la comprobación inicial de sesión, mostrar spinner para evitar redirecciones prematuras o parpadeo
  if (authStatus === 'checking') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] gap-3 bg-slate-100/60">
        <Loader2 className="w-8 h-8 text-uts-green-700 animate-spin" />
        <span className="text-sm text-slate-500 font-medium">Verificando sesión administrativa...</span>
      </div>
    );
  }

  // Si ya está autenticado con sesión activa, redirigir al panel administrativo
  if (isAuthenticated) {
    return <Navigate to="/admin" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adminKey.trim()) return;

    const ok = await login(adminKey.trim());
    if (ok) {
      navigate('/admin', { replace: true });
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-4 sm:p-6 bg-slate-100/60">
      <div className="max-w-md w-full bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xl">
        <div className="text-center mb-6">
          <div className="w-12 h-12 bg-uts-green-100 text-uts-green-800 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-xs">
            <Lock className="w-6 h-6 text-uts-green-700" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            Acceso Administrativo
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Gestión documental y control de versiones del reglamento normativo UTS
          </p>
        </div>

        {authError && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{authError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="adminKeyInput"
              className="block text-xs font-semibold text-slate-700 mb-1"
            >
              Clave de Administración (X-Admin-Key)
            </label>
            <input
              id="adminKeyInput"
              type="password"
              required
              autoFocus
              value={adminKey}
              onChange={(e) => setAdminKey(e.target.value)}
              placeholder="Ingrese la clave administrativa configurada..."
              className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl focus:ring-2 focus:ring-uts-green-600 focus:outline-none transition-all"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              La clave es validada directamente contra FastAPI y nunca se almacena en el cliente.
            </p>
          </div>

          <Button
            type="submit"
            isLoading={isLoading}
            disabled={!adminKey.trim() || isLoading}
            className="w-full py-2.5 rounded-xl font-semibold"
            leftIcon={<Shield className="w-4 h-4" />}
          >
            Iniciar Sesión
          </Button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-100 text-center">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-uts-green-800 transition-colors font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Volver al Chat Público</span>
          </button>
        </div>
      </div>
    </div>
  );
};
