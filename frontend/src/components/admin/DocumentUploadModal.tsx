import React, { useState } from 'react';
import { UploadCloud, FileText, AlertCircle, CheckCircle } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { uploadDocument } from '../../api/admin';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [versionId, setVersionId] = useState('');
  const [nombre, setNombre] = useState('');
  const [numeroAcuerdo, setNumeroAcuerdo] = useState('');
  const [anio, setAnio] = useState<number>(new Date().getFullYear());
  const [fechaExpedicion, setFechaExpedicion] = useState('');
  const [estadoVigencia, setEstadoVigencia] = useState('Vigente');
  const [autoProcess, setAutoProcess] = useState(true);
  const [forceOcr, setForceOcr] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (!selected.name.toLowerCase().endsWith('.pdf')) {
        setError('El archivo seleccionado debe ser un documento PDF (.pdf)');
        setFile(null);
        return;
      }
      setFile(selected);
      setError(null);
      // Sugerir nombre y version_id basados en el archivo si están vacíos
      if (!nombre) {
        setNombre(selected.name.replace(/\.pdf$/i, '').replace(/_/g, ' '));
      }
      if (!versionId) {
        setVersionId(
          selected.name
            .toLowerCase()
            .replace(/\.pdf$/i, '')
            .replace(/[^a-z0-9_-]/g, '_')
            .substring(0, 30)
        );
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Por favor seleccione un archivo PDF.');
      return;
    }
    if (!versionId.trim()) {
      setError('El identificador de versión (version_id) es obligatorio.');
      return;
    }
    if (!nombre.trim()) {
      setError('El nombre del reglamento es obligatorio.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setWarning(null);
    setSuccessMsg(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('version_id', versionId.trim());
      formData.append('nombre', nombre.trim());
      if (numeroAcuerdo.trim()) formData.append('numero_acuerdo', numeroAcuerdo.trim());
      if (anio) formData.append('anio', String(anio));
      if (fechaExpedicion.trim()) formData.append('fecha_expedicion', fechaExpedicion.trim());
      if (estadoVigencia.trim()) formData.append('estado_vigencia', estadoVigencia.trim());
      formData.append('auto_process', String(autoProcess));
      formData.append('force_ocr', String(forceOcr));

      const res = await uploadDocument(formData);

      if (res.warning) {
        setWarning(res.warning);
      } else {
        setSuccessMsg(`Documento y versión '${res.version.id}' registrados correctamente.`);
      }

      setTimeout(() => {
        setIsLoading(false);
        onSuccess();
        onClose();
      }, 1500);
    } catch (err: any) {
      setIsLoading(false);
      setError(err.message || 'Error al cargar el documento.');
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Cargar Nueva Normativa (PDF)"
      subtitle="Registre una versión del reglamento de trabajo de grado en el corpus"
      maxWidth="2xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {warning && (
          <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg text-xs flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <span>{warning}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Zona de subida de archivo */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Archivo PDF oficial *
          </label>
          <div className="border-2 border-dashed border-slate-300 hover:border-uts-green-600 rounded-xl p-4 sm:p-6 text-center bg-slate-50 hover:bg-uts-green-50/30 transition-all cursor-pointer relative">
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              disabled={isLoading}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            {file ? (
              <div className="flex items-center justify-center gap-3 text-slate-800">
                <FileText className="w-8 h-8 text-uts-green-700" />
                <div className="text-left">
                  <p className="text-sm font-semibold truncate max-w-xs">{file.name}</p>
                  <p className="text-xs text-slate-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-1 text-slate-600">
                <UploadCloud className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <p className="text-sm font-medium">Haga clic o arrastre el archivo PDF aquí</p>
                <p className="text-xs text-slate-400">Solo formato PDF (máx. 50 MB)</p>
              </div>
            )}
          </div>
        </div>

        {/* Metadatos normativos */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              ID de Versión (único) *
            </label>
            <input
              type="text"
              required
              disabled={isLoading}
              value={versionId}
              onChange={(e) => setVersionId(e.target.value)}
              placeholder="e.g. uts_tg_2021"
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Nombre de la Normativa *
            </label>
            <input
              type="text"
              required
              disabled={isLoading}
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="e.g. Reglamento de Trabajo de Grado 2021"
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Número de Acuerdo / Resolución
            </label>
            <input
              type="text"
              disabled={isLoading}
              value={numeroAcuerdo}
              onChange={(e) => setNumeroAcuerdo(e.target.value)}
              placeholder="e.g. Acuerdo 01-005"
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Año de Expedición
            </label>
            <input
              type="number"
              disabled={isLoading}
              value={anio}
              onChange={(e) => setAnio(parseInt(e.target.value, 10) || 0)}
              className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
            />
          </div>

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

        {/* Opciones de procesamiento */}
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2 text-xs">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoProcess}
              onChange={(e) => setAutoProcess(e.target.checked)}
              disabled={isLoading}
              className="rounded text-uts-green-600 focus:ring-uts-green-500"
            />
            <span className="font-medium text-slate-700">
              Procesar e indexar inmediatamente (extracción, limpieza, chunks y embeddings)
            </span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={forceOcr}
              onChange={(e) => setForceOcr(e.target.checked)}
              disabled={isLoading}
              className="rounded text-uts-green-600 focus:ring-uts-green-500"
            />
            <span className="text-slate-600">
              Forzar OCR completo incluso si el PDF posee capa de texto (más lento)
            </span>
          </label>
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
          <Button
            type="submit"
            isLoading={isLoading}
            disabled={isLoading || !file}
          >
            {autoProcess ? 'Cargar y Procesar' : 'Cargar Documento'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
