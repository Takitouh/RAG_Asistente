import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { NormativeVersion } from '../../types';
import { updateVersionMetadata } from '../../api/admin';

interface MetadataEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  version: NormativeVersion | null;
  onSuccess: () => void;
}

export const MetadataEditModal: React.FC<MetadataEditModalProps> = ({
  isOpen,
  onClose,
  version,
  onSuccess,
}) => {
  const [nombre, setNombre] = useState('');
  const [numeroAcuerdo, setNumeroAcuerdo] = useState('');
  const [anio, setAnio] = useState<number>(0);
  const [fechaExpedicion, setFechaExpedicion] = useState('');
  const [estadoVigencia, setEstadoVigencia] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (version) {
      setNombre(version.nombre || '');
      setNumeroAcuerdo(version.numero_acuerdo || '');
      setAnio(version.anio || 0);
      setFechaExpedicion(version.fecha_expedicion || '');
      setEstadoVigencia(version.estado_vigencia || 'Vigente');
      setError(null);
      setSuccessMsg(null);
    }
  }, [version]);

  if (!version) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      await updateVersionMetadata(version.id, {
        nombre: nombre.trim() || undefined,
        numero_acuerdo: numeroAcuerdo.trim() || undefined,
        anio: anio || undefined,
        fecha_expedicion: fechaExpedicion.trim() || undefined,
        estado_vigencia: estadoVigencia.trim() || undefined,
      });

      setSuccessMsg('Metadatos actualizados correctamente.');
      setTimeout(() => {
        setIsLoading(false);
        onSuccess();
        onClose();
      }, 1000);
    } catch (err: any) {
      setIsLoading(false);
      setError(err.message || 'Error al actualizar metadatos.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Editar Metadatos: ${version.id}`}
      subtitle="Corrección explícita antes de la activación en el asistente"
      maxWidth="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Nombre Oficial de la Normativa
          </label>
          <input
            type="text"
            required
            disabled={isLoading}
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Número de Acuerdo
            </label>
            <input
              type="text"
              disabled={isLoading}
              value={numeroAcuerdo}
              onChange={(e) => setNumeroAcuerdo(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Año
            </label>
            <input
              type="number"
              disabled={isLoading}
              value={anio}
              onChange={(e) => setAnio(parseInt(e.target.value, 10) || 0)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Fecha de Expedición
            </label>
            <input
              type="date"
              disabled={isLoading}
              value={fechaExpedicion}
              onChange={(e) => setFechaExpedicion(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Estado de Vigencia
            </label>
            <select
              disabled={isLoading}
              value={estadoVigencia}
              onChange={(e) => setEstadoVigencia(e.target.value)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none bg-white"
            >
              <option value="Vigente">Vigente</option>
              <option value="Derogado">Derogado</option>
              <option value="En Revisión">En Revisión</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancelar
          </Button>
          <Button type="submit" isLoading={isLoading} disabled={isLoading}>
            Guardar Cambios
          </Button>
        </div>
      </form>
    </Modal>
  );
};
