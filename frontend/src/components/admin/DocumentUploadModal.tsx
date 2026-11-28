import React, { useState, useEffect } from 'react';
import { UploadCloud, FileText, AlertCircle, CheckCircle, FolderTree, FileCheck } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { listCategories, listFamilies, createFamily, uploadDocument } from '../../api/admin';
import { DocumentCategory, DocumentFamily } from '../../types';

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
  const [categories, setCategories] = useState<DocumentCategory[]>([]);
  const [families, setFamilies] = useState<DocumentFamily[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('cat_reglamentos');
  const [selectedFamily, setSelectedFamily] = useState<string>('fam_reglamento_tg');

  // Modo crear nueva familia
  const [isCreatingFamily, setIsCreatingFamily] = useState<boolean>(false);
  const [newFamilyCode, setNewFamilyCode] = useState<string>('');
  const [newFamilyName, setNewFamilyName] = useState<string>('');
  const [newFamilyDesc, setNewFamilyDesc] = useState<string>('');
  const [newFamilyProfile, setNewFamilyProfile] = useState<string>('reglamento_estructurado');

  const [file, setFile] = useState<File | null>(null);
  const [versionId, setVersionId] = useState('');
  const [nombre, setNombre] = useState('');
  const [numeroVersionInst, setNumeroVersionInst] = useState('');
  const [numeroAcuerdo, setNumeroAcuerdo] = useState('');
  const [anio, setAnio] = useState<number>(new Date().getFullYear());
  const [fechaExpedicion, setFechaExpedicion] = useState('');
  const [procedencia, setProcedencia] = useState('');
  const [estadoVigencia, setEstadoVigencia] = useState('Vigente');
  const [autoProcess, setAutoProcess] = useState(true);
  const [forceOcr, setForceOcr] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Cargar categorías y familias cuando se abre el modal
  useEffect(() => {
    if (isOpen) {
      loadHierarchy();
    }
  }, [isOpen]);

  const loadHierarchy = async () => {
    try {
      const [cats, fams] = await Promise.all([listCategories(), listFamilies()]);
      setCategories(cats);
      setFamilies(fams);
      if (cats.length > 0 && !selectedCategory) {
        setSelectedCategory(cats[0].id);
      }
      if (fams.length > 0 && !selectedFamily) {
        setSelectedFamily(fams[0].id);
      }
    } catch (e: any) {
      setError(e.message || 'Error cargando categorías y familias.');
    }
  };

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

  const filteredFamilies = families.filter(
    (f) => !selectedCategory || f.categoria_id === selectedCategory
  );

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
      setError('El nombre de la versión es obligatorio.');
      return;
    }

    let targetFamilyId = selectedFamily;

    setIsLoading(true);
    setError(null);
    setWarning(null);
    setSuccessMsg(null);

    try {
      // Si se solicitó crear nueva familia en el mismo flujo
      if (isCreatingFamily) {
        if (!newFamilyCode.trim() || !newFamilyName.trim()) {
          throw new Error('Debe especificar código y nombre para la nueva familia documental.');
        }
        const generatedFamId = `fam_${newFamilyCode.toLowerCase().replace(/[^a-z0-9_-]/g, '_')}`;
        const createdFam = await createFamily({
          id: generatedFamId,
          categoria_id: selectedCategory,
          codigo: newFamilyCode.trim(),
          nombre: newFamilyName.trim(),
          descripcion: newFamilyDesc.trim() || undefined,
          perfil_procesamiento: newFamilyProfile,
          estado: 'ACTIVO',
        });
        targetFamilyId = createdFam.id;
      }

      const formData = new FormData();
      formData.append('file', file);
      formData.append('version_id', versionId.trim());
      formData.append('nombre', nombre.trim());
      formData.append('family_id', targetFamilyId);
      if (numeroVersionInst.trim()) formData.append('numero_version_institucional', numeroVersionInst.trim());
      if (numeroAcuerdo.trim()) formData.append('numero_acuerdo', numeroAcuerdo.trim());
      if (anio) formData.append('anio', String(anio));
      if (fechaExpedicion.trim()) formData.append('fecha_expedicion', fechaExpedicion.trim());
      if (procedencia.trim()) formData.append('procedencia', procedencia.trim());
      if (estadoVigencia.trim()) formData.append('estado_vigencia', estadoVigencia.trim());
      formData.append('auto_process', String(autoProcess));
      formData.append('force_ocr', String(forceOcr));

      const res = await uploadDocument(formData);

      if (res.warning) {
        setWarning(res.warning);
      } else {
        setSuccessMsg(`Documento y versión '${res.version.id}' registrados correctamente en la familia documental.`);
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
      subtitle="Flujo institucional: Categoría → Familia Documental → Versión → Procesamiento"
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

        {/* 1. Categoría y Familia Documental */}
        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5 uppercase tracking-wide">
              <FolderTree className="w-4 h-4 text-uts-green-700" />
              1. Jerarquía Documental Institucional
            </span>
            <button
              type="button"
              onClick={() => setIsCreatingFamily(!isCreatingFamily)}
              className="text-xs text-uts-green-700 hover:text-uts-green-900 font-semibold underline"
            >
              {isCreatingFamily ? '← Seleccionar familia existente' : '+ Crear nueva familia'}
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Categoría Documental *
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                disabled={isLoading}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </div>

            {!isCreatingFamily ? (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Familia Documental *
                </label>
                <select
                  value={selectedFamily}
                  onChange={(e) => setSelectedFamily(e.target.value)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                >
                  {filteredFamilies.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.codigo} — {f.nombre}
                    </option>
                  ))}
                  {filteredFamilies.length === 0 && (
                    <option value="" disabled>
                      Sin familias en esta categoría
                    </option>
                  )}
                </select>
              </div>
            ) : (
              <div className="space-y-2 col-span-2 bg-white p-3 rounded-lg border border-slate-200">
                <span className="text-[11px] font-semibold text-slate-600 block">
                  Definición de Nueva Familia Documental:
                </span>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Código (ej. P-DC-28)"
                    value={newFamilyCode}
                    onChange={(e) => setNewFamilyCode(e.target.value)}
                    className="px-2.5 py-1.5 text-xs border border-slate-300 rounded focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                  />
                  <input
                    type="text"
                    placeholder="Nombre institucional"
                    value={newFamilyName}
                    onChange={(e) => setNewFamilyName(e.target.value)}
                    className="px-2.5 py-1.5 text-xs border border-slate-300 rounded focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                  />
                </div>
                <input
                  type="text"
                  placeholder="Descripción del documento institucional"
                  value={newFamilyDesc}
                  onChange={(e) => setNewFamilyDesc(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                />
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                    Perfil de Procesamiento Técnico:
                  </label>
                  <select
                    value={newFamilyProfile}
                    onChange={(e) => setNewFamilyProfile(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs border border-slate-300 rounded bg-white focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                  >
                    <option value="reglamento_estructurado">Reglamento estructurado (Capítulos, Artículos, Parágrafos)</option>
                    <option value="procedimiento_institucional">Procedimiento institucional (Numerales 1-9, Actividades)</option>
                    <option value="formato_institucional">Formato institucional (Plantillas y Criterios)</option>
                    <option value="documento_general">Documento general (Párrafos y Páginas)</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 2. Archivo PDF */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            2. Archivo PDF oficial *
          </label>
          <div className="border-2 border-dashed border-slate-300 hover:border-uts-green-600 rounded-xl p-4 text-center bg-slate-50 hover:bg-uts-green-50/30 transition-all cursor-pointer relative">
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              disabled={isLoading}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="flex flex-col items-center justify-center gap-1.5 pointer-events-none">
              <UploadCloud className="w-7 h-7 text-uts-green-700" />
              {file ? (
                <div className="flex items-center gap-2 text-xs font-medium text-uts-green-900 bg-uts-green-100 px-3 py-1 rounded-full">
                  <FileText className="w-3.5 h-3.5" />
                  <span className="truncate max-w-xs">{file.name}</span>
                  <span className="text-[11px] text-uts-green-700">
                    ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                  </span>
                </div>
              ) : (
                <>
                  <p className="text-xs font-medium text-slate-700">
                    Arrastre el PDF oficial o <span className="text-uts-green-700 underline">explore sus archivos</span>
                  </p>
                  <p className="text-[11px] text-slate-400">PDF con capa de texto preferida o escaneo nítido para OCR</p>
                </>
              )}
            </div>
          </div>
        </div>

        {/* 3. Metadatos de la Versión */}
        <div className="space-y-3">
          <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5 uppercase tracking-wide">
            <FileCheck className="w-4 h-4 text-uts-green-700" />
            3. Metadatos de la Versión
          </span>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                ID Técnico de Versión *
              </label>
              <input
                type="text"
                required
                disabled={isLoading}
                value={versionId}
                onChange={(e) => setVersionId(e.target.value)}
                placeholder="ej: uts_tg_2021"
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Nombre de la Versión *
              </label>
              <input
                type="text"
                required
                disabled={isLoading}
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="ej: Reglamento de Trabajo de Grado 2021"
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Versión Institucional (ej. 3.0)
              </label>
              <input
                type="text"
                disabled={isLoading}
                value={numeroVersionInst}
                onChange={(e) => setNumeroVersionInst(e.target.value)}
                placeholder="ej: 3.0"
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Acuerdo / Resolución
              </label>
              <input
                type="text"
                disabled={isLoading}
                value={numeroAcuerdo}
                onChange={(e) => setNumeroAcuerdo(e.target.value)}
                placeholder="ej: Acuerdo 01-026"
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
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
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Fecha Expedición
              </label>
              <input
                type="date"
                disabled={isLoading}
                value={fechaExpedicion}
                onChange={(e) => setFechaExpedicion(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Procedencia / Fuente Oficial
              </label>
              <input
                type="text"
                disabled={isLoading}
                value={procedencia}
                onChange={(e) => setProcedencia(e.target.value)}
                placeholder="ej: Consejo Directivo UTS"
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Estado de Vigencia Institucional
              </label>
              <select
                disabled={isLoading}
                value={estadoVigencia}
                onChange={(e) => setEstadoVigencia(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
              >
                <option value="Vigente">Vigente</option>
                <option value="Derogado">Derogado</option>
                <option value="En Revisión">En Revisión</option>
              </select>
            </div>
          </div>
        </div>

        {/* Opciones de Ingestión */}
        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-2">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700">
            <input
              type="checkbox"
              checked={autoProcess}
              onChange={(e) => setAutoProcess(e.target.checked)}
              disabled={isLoading}
              className="rounded text-uts-green-700 focus:ring-uts-green-600 h-4 w-4"
            />
            <span>Iniciar procesamiento e indexación vectorial automáticamente tras la carga</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-700">
            <input
              type="checkbox"
              checked={forceOcr}
              onChange={(e) => setForceOcr(e.target.checked)}
              disabled={isLoading || !autoProcess}
              className="rounded text-uts-green-700 focus:ring-uts-green-600 h-4 w-4"
            />
            <span>Forzar OCR completo incluso si el PDF posee capa de texto</span>
          </label>
        </div>

        {/* Botones de acción */}
        <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
          <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button type="submit" isLoading={isLoading} disabled={isLoading || !file}>
            Cargar y Procesar Versión
          </Button>
        </div>
      </form>
    </Modal>
  );
};
