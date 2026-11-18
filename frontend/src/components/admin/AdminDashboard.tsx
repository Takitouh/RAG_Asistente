import React from 'react';
import {
  CheckCircle,
  AlertTriangle,
  Layers,
  Database,
  History,
  Plus,
  RefreshCw,
  LogOut,
  ShieldCheck,
} from 'lucide-react';
import { AdminStats } from '../../types';
import { Button } from '../ui/Button';

interface AdminDashboardProps {
  stats: AdminStats | null;
  isLoading: boolean;
  onRefresh: () => void;
  onOpenUploadModal: () => void;
  onLogout: () => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({
  stats,
  isLoading,
  onRefresh,
  onOpenUploadModal,
  onLogout,
}) => {
  return (
    <div className="space-y-6">
      {/* Barra Superior del Panel */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
              Panel de Administración del Corpus Normativo
            </h1>
            <span className="text-xs bg-uts-green-100 text-uts-green-800 font-semibold px-2 py-0.5 rounded border border-uts-green-200">
              Admin
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Gestión documental, extracción OCR, auditoría estructural y activación exclusiva de versiones para el motor RAG.
          </p>
        </div>

        <div className="flex items-center gap-2 self-stretch sm:self-auto">
          <Button
            size="sm"
            variant="outline"
            onClick={onRefresh}
            isLoading={isLoading}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Actualizar
          </Button>

          <Button
            size="sm"
            variant="primary"
            onClick={onOpenUploadModal}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Cargar PDF Normativo
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={onLogout}
            className="text-slate-600 hover:text-rose-700 hover:border-rose-300"
            leftIcon={<LogOut className="w-3.5 h-3.5" />}
          >
            Cerrar Sesión
          </Button>
        </div>
      </div>

      {/* Tarjetas de Métricas Reales */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
        {/* Versión Activa */}
        <div className="col-span-2 bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Reglamento en Producción</span>
          </div>
          {stats?.active_version ? (
            <div>
              <div className="text-base sm:text-lg font-bold text-slate-900 truncate">
                {stats.active_version.nombre}
              </div>
              <div className="text-xs text-slate-500 mt-1 flex items-center gap-2">
                <span className="font-mono bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200">
                  {stats.active_version.id}
                </span>
                <span>•</span>
                <span>{stats.active_version.chunks_count} chunks activos</span>
              </div>
            </div>
          ) : (
            <div className="text-sm font-medium text-amber-700 flex items-center gap-2 mt-2">
              <AlertTriangle className="w-4 h-4" />
              <span>Ninguna versión activa actualmente</span>
            </div>
          )}
        </div>

        {/* Total Versiones */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            <Layers className="w-4 h-4 text-blue-600" />
            <span>Versiones</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {stats?.total_versions ?? '—'}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Registradas en SQLite</div>
        </div>

        {/* Chunks Totales */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            <Database className="w-4 h-4 text-uts-green-700" />
            <span>Chunks Vectoriales</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {stats?.total_chunks ?? '—'}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Indexados en Qdrant</div>
        </div>

        {/* Consultas Trazadas */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            <History className="w-4 h-4 text-purple-600" />
            <span>Trazas de Consulta</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {stats?.total_traces ?? '—'}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Registros de auditoría</div>
        </div>
      </div>

      {/* Distribución por Estado de Ingestión */}
      {stats && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 text-xs">
          <span className="font-semibold text-slate-700">Estado de ingestión de reglamentos:</span>
          <div className="flex flex-wrap items-center gap-4">
            <span className="flex items-center gap-1.5 text-emerald-800">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
              <strong>{stats.status_counts['PROCESADO'] || 0}</strong> Procesados
            </span>
            <span className="flex items-center gap-1.5 text-amber-800">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              <strong>{stats.status_counts['PENDIENTE_REVISION'] || 0}</strong> Pendientes Revisión
            </span>
            <span className="flex items-center gap-1.5 text-rose-800">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
              <strong>{stats.status_counts['ERROR'] || 0}</strong> Errores
            </span>
            <span className="flex items-center gap-1.5 text-slate-600">
              <strong>{stats.status_counts['RECIBIDO'] || 0}</strong> Recibidos
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
