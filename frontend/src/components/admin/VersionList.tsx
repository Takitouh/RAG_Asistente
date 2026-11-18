import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  FileSearch,
  Power,
  Trash2,
  Edit,
  Play,
  Loader2,
} from 'lucide-react';
import { NormativeVersion } from '../../types';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { activateVersion, deactivateVersion, deleteVersion, processVersion } from '../../api/admin';

interface VersionListProps {
  versions: NormativeVersion[];
  isLoading: boolean;
  onRefresh: () => void;
  onOpenDetail: (version: NormativeVersion) => void;
  onOpenEditMetadata: (version: NormativeVersion) => void;
}

export const VersionList: React.FC<VersionListProps> = ({
  versions,
  isLoading,
  onRefresh,
  onOpenDetail,
  onOpenEditMetadata,
}) => {
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleActivate = async (version: NormativeVersion) => {
    if (!window.confirm(`¿Está seguro de activar "${version.nombre}" (${version.id}) como la normativa oficial activa para las consultas? Las demás versiones quedarán inactivas.`)) {
      return;
    }

    setActionLoadingId(version.id);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await activateVersion(version.id);
      setSuccessMessage(res.message);
      setActionLoadingId(null);
      onRefresh();
    } catch (err: any) {
      setActionLoadingId(null);
      setErrorMessage(err.message || 'Error al activar versión.');
    }
  };

  const handleDeactivate = async (version: NormativeVersion) => {
    if (!window.confirm(`¿Desea desactivar "${version.nombre}"? Si la desactiva, el asistente quedará sin normativa activa hasta que se active otra.`)) {
      return;
    }

    setActionLoadingId(version.id);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await deactivateVersion(version.id);
      setSuccessMessage(res.message);
      setActionLoadingId(null);
      onRefresh();
    } catch (err: any) {
      setActionLoadingId(null);
      setErrorMessage(err.message || 'Error al desactivar versión.');
    }
  };

  const handleProcess = async (version: NormativeVersion) => {
    setActionLoadingId(version.id);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await processVersion(version.id, false);
      setSuccessMessage(`Versión '${version.id}' procesada e indexada exitosamente.`);
      setActionLoadingId(null);
      onRefresh();
    } catch (err: any) {
      setActionLoadingId(null);
      setErrorMessage(err.message || 'Error durante el procesamiento documental.');
    }
  };

  const handleDelete = async (version: NormativeVersion) => {
    if (version.is_active) {
      alert('No es posible eliminar una versión activa. Debe desactivarla primero.');
      return;
    }

    if (!window.confirm(`¿Está seguro de eliminar definitivamente la versión "${version.id}" y todos sus chunks asociados? Esta acción no se puede deshacer.`)) {
      return;
    }

    setActionLoadingId(version.id);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await deleteVersion(version.id);
      setSuccessMessage(res.message);
      setActionLoadingId(null);
      onRefresh();
    } catch (err: any) {
      setActionLoadingId(null);
      setErrorMessage(err.message || 'Error al eliminar versión.');
    }
  };

  return (
    <div className="space-y-4">
      {errorMessage && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-rose-700 font-bold ml-2">×</button>
        </div>
      )}

      {successMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-700 font-bold ml-2">×</button>
        </div>
      )}

      {/* Tabla Adaptativa */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[11px] tracking-wider">
                <th className="py-3 px-4">Versión / Nombre</th>
                <th className="py-3 px-3">Año / Acuerdo</th>
                <th className="py-3 px-3">Estado Ingestión</th>
                <th className="py-3 px-3">Vigencia</th>
                <th className="py-3 px-3">Chunks</th>
                <th className="py-3 px-3">Activa</th>
                <th className="py-3 px-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-uts-green-700" />
                    <span>Cargando reglamentos registrados...</span>
                  </td>
                </tr>
              ) : versions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    <AlertCircle className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    <p className="font-medium text-slate-700">No hay reglamentos registrados</p>
                    <p className="text-xs text-slate-400 mt-1">Utilice el botón superior para cargar el primer PDF normativo.</p>
                  </td>
                </tr>
              ) : (
                versions.map((ver) => {
                  const isBusy = actionLoadingId === ver.id;
                  const canActivate = ver.status === 'PROCESADO' && !ver.is_active;

                  return (
                    <tr
                      key={ver.id}
                      className={`hover:bg-slate-50/70 transition-colors ${
                        ver.is_active ? 'bg-uts-green-50/30' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900">{ver.nombre}</div>
                        <div className="text-[11px] font-mono text-slate-400 mt-0.5">{ver.id}</div>
                      </td>

                      <td className="py-3.5 px-3 text-slate-700">
                        <div>{ver.anio || 'N/A'}</div>
                        {ver.numero_acuerdo && (
                          <div className="text-[11px] text-slate-400">{ver.numero_acuerdo}</div>
                        )}
                      </td>

                      <td className="py-3.5 px-3">
                        <Badge status={ver.status} />
                      </td>

                      <td className="py-3.5 px-3 text-slate-600">
                        {ver.estado_vigencia || '—'}
                      </td>

                      <td className="py-3.5 px-3 font-mono font-medium text-slate-700">
                        {ver.chunks_count}
                      </td>

                      <td className="py-3.5 px-3">
                        {ver.is_active ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300 shadow-2xs">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse" />
                            <span>ACTIVA</span>
                          </span>
                        ) : (
                          <span className="text-slate-400 text-xs">Inactiva</span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <div className="inline-flex items-center gap-1">
                          {/* Botón Detalles y Auditoría OCR */}
                          <button
                            type="button"
                            onClick={() => onOpenDetail(ver)}
                            className="p-1.5 rounded text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                            title="Auditoría OCR y Detalles"
                          >
                            <FileSearch className="w-4 h-4 text-uts-green-700" />
                          </button>

                          {/* Botón Editar Metadatos */}
                          <button
                            type="button"
                            onClick={() => onOpenEditMetadata(ver)}
                            className="p-1.5 rounded text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                            title="Editar Metadatos"
                          >
                            <Edit className="w-4 h-4 text-slate-500" />
                          </button>

                          {/* Botón Reprocesar si está en Error o Pendiente */}
                          {(ver.status === 'ERROR' || ver.status === 'RECIBIDO') && (
                            <button
                              type="button"
                              disabled={isBusy}
                              onClick={() => handleProcess(ver)}
                              className="p-1.5 rounded text-blue-600 hover:text-blue-800 hover:bg-blue-50 transition-colors"
                              title="Reintentar Procesamiento e Indexación"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}

                          {/* Botón Activar */}
                          {canActivate && (
                            <Button
                              size="sm"
                              variant="primary"
                              disabled={isBusy}
                              isLoading={isBusy}
                              onClick={() => handleActivate(ver)}
                              className="text-xs py-1 px-2.5 ml-1"
                            >
                              Activar
                            </Button>
                          )}

                          {/* Botón Desactivar */}
                          {ver.is_active && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={isBusy}
                              isLoading={isBusy}
                              onClick={() => handleDeactivate(ver)}
                              className="text-xs py-1 px-2.5 text-amber-700 hover:bg-amber-50 border-amber-300 ml-1"
                              leftIcon={<Power className="w-3.5 h-3.5" />}
                            >
                              Desactivar
                            </Button>
                          )}

                          {/* Botón Eliminar (solo si no es activa) */}
                          {!ver.is_active && (
                            <button
                              type="button"
                              disabled={isBusy}
                              onClick={() => handleDelete(ver)}
                              className="p-1.5 rounded text-rose-500 hover:text-rose-700 hover:bg-rose-50 transition-colors ml-1"
                              title="Eliminar versión del corpus"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
