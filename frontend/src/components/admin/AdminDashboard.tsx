import React, { useState, useEffect } from 'react';
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
  FileCheck,
  ShieldAlert,
} from 'lucide-react';
import { AdminStats, DocumentCategory, DocumentFamily } from '../../types';
import { Button } from '../ui/Button';
import { listCategories, listFamilies, createCategory, createFamily, updateFamily } from '../../api/admin';

interface AdminDashboardProps {
  stats: AdminStats | null;
  isLoading: boolean;
  onRefresh: () => void;
  onOpenUploadModal: () => void;
  onLogout: () => void;
  activeTab?: 'versions' | 'hierarchy' | 'active_corpus';
  onTabChange?: (tab: 'versions' | 'hierarchy' | 'active_corpus') => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({
  stats,
  isLoading,
  onRefresh,
  onOpenUploadModal,
  onLogout,
  activeTab = 'versions',
  onTabChange,
}) => {
  const [categories, setCategories] = useState<DocumentCategory[]>([]);
  const [families, setFamilies] = useState<DocumentFamily[]>([]);
  const [showCatModal, setShowCatModal] = useState(false);
  const [showFamModal, setShowFamModal] = useState(false);

  // Formularios de categoría
  const [catId, setCatId] = useState('');
  const [catName, setCatName] = useState('');
  const [catDesc, setCatDesc] = useState('');
  const [catStatus] = useState('ACTIVO');

  // Formularios de familia
  const [famId, setFamId] = useState('');
  const [famCatId, setFamCatId] = useState('');
  const [famCode, setFamCode] = useState('');
  const [famName, setFamName] = useState('');
  const [famDesc, setFamDesc] = useState('');
  const [famProfile, setFamProfile] = useState('reglamento_estructurado');
  const [famStatus] = useState('ACTIVO');

  const [savingMsg, setSavingMsg] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab === 'hierarchy') {
      loadHierarchyData();
    }
  }, [activeTab, isLoading]);

  const loadHierarchyData = async () => {
    try {
      const [cats, fams] = await Promise.all([listCategories(), listFamilies()]);
      setCategories(cats);
      setFamilies(fams);
    } catch {
      // Ignorar en render inicial
    }
  };

  const handleUpdateFamilyProfile = async (familyId: string, newProfile: string) => {
    try {
      await updateFamily(familyId, { perfil_procesamiento: newProfile });
      setSavingMsg('Perfil de procesamiento actualizado exitosamente');
      setTimeout(() => setSavingMsg(null), 3000);
      loadHierarchyData();
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error actualizando perfil de procesamiento');
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catId || !catName) return;
    try {
      await createCategory({
        id: catId.trim(),
        nombre: catName.trim(),
        descripcion: catDesc.trim() || undefined,
        estado: catStatus,
      });
      setCatId('');
      setCatName('');
      setCatDesc('');
      setShowCatModal(false);
      setSavingMsg('Categoría creada exitosamente');
      setTimeout(() => setSavingMsg(null), 3000);
      loadHierarchyData();
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error creando categoría');
    }
  };

  const handleCreateFamily = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!famId || !famCatId || !famCode || !famName) return;
    try {
      await createFamily({
        id: famId.trim(),
        categoria_id: famCatId.trim(),
        codigo: famCode.trim(),
        nombre: famName.trim(),
        descripcion: famDesc.trim() || undefined,
        perfil_procesamiento: famProfile,
        estado: famStatus,
      });
      setFamId('');
      setFamCode('');
      setFamName('');
      setFamDesc('');
      setFamProfile('reglamento_estructurado');
      setShowFamModal(false);
      setSavingMsg('Familia creada exitosamente');
      setTimeout(() => setSavingMsg(null), 3000);
      loadHierarchyData();
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error creando familia documental');
    }
  };

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
            Gestión documental institucional: Categorías, Familias y Versiones para el motor RAG.
          </p>
        </div>

        <div className="flex items-center gap-2 self-stretch sm:self-auto flex-wrap">
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

      {savingMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{savingMsg}</span>
        </div>
      )}

      {/* Tarjetas de Métricas Reales */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 sm:gap-4">
        {/* Versión Activa / Corpus Activo */}
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
              {stats.active_corpus && stats.active_corpus.length > 1 && (
                <div className="text-[11px] text-emerald-700 mt-1">
                  Corpus activo: {stats.active_corpus.length} documentos habilitados
                </div>
              )}
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

        {/* Familias */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            <FileCheck className="w-4 h-4 text-uts-green-700" />
            <span>Familias</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {stats?.total_families ?? families.length}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Documentos base</div>
        </div>
      </div>

      {/* Alerta de Inconsistencias o Discrepancias SHA-256 */}
      {Boolean(stats?.inconsistent_versions_count && stats.inconsistent_versions_count > 0) && (
        <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs sm:text-sm text-rose-900 flex items-start gap-2.5 shadow-xs">
          <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Advertencia de Discrepancia Documental detectada:</span>
            <p className="mt-0.5 text-xs text-rose-700">
              Existen {stats?.inconsistent_versions_count} versión(es) con inconsistencia documental (huellas SHA-256 duplicadas con metadatos divergentes).
              Por regla de negocio, estas versiones están bloqueadas para activación hasta que se aclare su procedencia oficial.
            </p>
          </div>
        </div>
      )}

      {/* Pestañas de Navegación del Panel */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => onTabChange && onTabChange('versions')}
          className={`px-3 py-1.5 text-xs sm:text-sm font-semibold rounded-lg transition-colors ${
            activeTab === 'versions'
              ? 'bg-uts-green-700 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Versiones Normativas ({stats?.total_versions ?? 0})
        </button>

        <button
          onClick={() => onTabChange && onTabChange('hierarchy')}
          className={`px-3 py-1.5 text-xs sm:text-sm font-semibold rounded-lg transition-colors ${
            activeTab === 'hierarchy'
              ? 'bg-uts-green-700 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Categorías y Familias ({categories.length} / {families.length})
        </button>

        <button
          onClick={() => onTabChange && onTabChange('active_corpus')}
          className={`px-3 py-1.5 text-xs sm:text-sm font-semibold rounded-lg transition-colors ${
            activeTab === 'active_corpus'
              ? 'bg-uts-green-700 text-white shadow-xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          Corpus Activo ({stats?.active_corpus?.length ?? (stats?.active_version ? 1 : 0)})
        </button>
      </div>

      {/* Vista de Categorías y Familias */}
      {activeTab === 'hierarchy' && (
        <div className="space-y-6 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
            <div>
              <h3 className="text-base font-bold text-slate-800">
                Estructura Documental Institucional
              </h3>
              <p className="text-xs text-slate-500">
                Configure dinámicamente las categorías y familias de documentos sin modificar el código.
              </p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setShowCatModal(true)}>
                + Nueva Categoría
              </Button>
              <Button size="sm" variant="primary" onClick={() => setShowFamModal(true)}>
                + Nueva Familia
              </Button>
            </div>
          </div>

          {/* Lista de Categorías con sus Familias */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {categories.map((cat) => {
              const catFams = families.filter((f) => f.categoria_id === cat.id);
              return (
                <div key={cat.id} className="border border-slate-200 rounded-xl p-4 bg-slate-50/50 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-bold text-slate-900 text-sm">{cat.nombre}</span>
                      <div className="text-[11px] font-mono text-slate-400">{cat.id}</div>
                    </div>
                    <span className="text-[10px] font-semibold bg-slate-200 text-slate-700 px-2 py-0.5 rounded">
                      {cat.estado}
                    </span>
                  </div>
                  {cat.descripcion && (
                    <p className="text-xs text-slate-600 leading-relaxed">{cat.descripcion}</p>
                  )}

                  <div className="pt-2 border-t border-slate-200 space-y-1.5">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                      Familias Asociadas ({catFams.length}):
                    </span>
                    {catFams.map((f) => (
                      <div key={f.id} className="text-xs bg-white p-2.5 rounded-lg border border-slate-200 space-y-1.5 shadow-2xs">
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="font-semibold text-slate-800">{f.codigo}</span>
                            <span className="text-slate-500 ml-1.5 truncate">{f.nombre}</span>
                          </div>
                          <span className="text-[10px] font-mono text-slate-400">{f.id}</span>
                        </div>
                        <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[11px]">
                          <span className="text-slate-500 font-medium">Perfil:</span>
                          <select
                            value={f.perfil_procesamiento || 'reglamento_estructurado'}
                            onChange={(e) => handleUpdateFamilyProfile(f.id, e.target.value)}
                            aria-label={`Perfil de procesamiento para ${f.nombre}`}
                            className="text-[11px] font-medium bg-slate-50 border border-slate-200 rounded px-1.5 py-0.5 text-slate-700 focus:outline-none focus:ring-1 focus:ring-uts-green-600"
                          >
                            <option value="reglamento_estructurado">Reglamento estructurado</option>
                            <option value="procedimiento_institucional">Procedimiento institucional</option>
                            <option value="formato_institucional">Formato institucional</option>
                            <option value="documento_general">Documento general</option>
                          </select>
                        </div>
                      </div>
                    ))}
                    {catFams.length === 0 && (
                      <span className="text-xs text-slate-400 italic block">Sin familias asignadas</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Modal Crear Categoría */}
          {showCatModal && (
            <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
                <h4 className="font-bold text-slate-900 text-base">Crear Categoría Documental</h4>
                <form onSubmit={handleCreateCategory} className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">ID Único *</label>
                    <input
                      type="text"
                      placeholder="ej: cat_circulares"
                      required
                      value={catId}
                      onChange={(e) => setCatId(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Nombre *</label>
                    <input
                      type="text"
                      placeholder="ej: Circulares Institucionales"
                      required
                      value={catName}
                      onChange={(e) => setCatName(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Descripción</label>
                    <textarea
                      placeholder="Descripción de la categoría"
                      value={catDesc}
                      onChange={(e) => setCatDesc(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <Button type="button" variant="outline" size="sm" onClick={() => setShowCatModal(false)}>
                      Cancelar
                    </Button>
                    <Button type="submit" size="sm">
                      Guardar Categoría
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Modal Crear Familia */}
          {showFamModal && (
            <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
                <h4 className="font-bold text-slate-900 text-base">Crear Familia Documental</h4>
                <form onSubmit={handleCreateFamily} className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Categoría Asociada *</label>
                    <select
                      value={famCatId}
                      onChange={(e) => setFamCatId(e.target.value)}
                      required
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                    >
                      <option value="">Seleccione categoría...</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>{c.nombre}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">ID Único *</label>
                    <input
                      type="text"
                      placeholder="ej: fam_f_dc_128"
                      required
                      value={famId}
                      onChange={(e) => setFamId(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Código Institucional *</label>
                    <input
                      type="text"
                      placeholder="ej: F-DC-128"
                      required
                      value={famCode}
                      onChange={(e) => setFamCode(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Nombre Institucional *</label>
                    <input
                      type="text"
                      placeholder="ej: Formato de Práctica Empresarial"
                      required
                      value={famName}
                      onChange={(e) => setFamName(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Perfil de Procesamiento *</label>
                    <select
                      value={famProfile}
                      onChange={(e) => setFamProfile(e.target.value)}
                      required
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                    >
                      <option value="reglamento_estructurado">Reglamento estructurado (Capítulos, Artículos, Parágrafos)</option>
                      <option value="procedimiento_institucional">Procedimiento institucional (Secciones 1-9, Tablas de Actividades)</option>
                      <option value="formato_institucional">Formato institucional (Plantilla, Rúbricas e Instrucciones)</option>
                      <option value="documento_general">Documento general (Segmentación por párrafos y páginas)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Descripción</label>
                    <textarea
                      placeholder="Descripción de la familia documental"
                      value={famDesc}
                      onChange={(e) => setFamDesc(e.target.value)}
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <Button type="button" variant="outline" size="sm" onClick={() => setShowFamModal(false)}>
                      Cancelar
                    </Button>
                    <Button type="submit" size="sm">
                      Guardar Familia
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Vista de Corpus Activo */}
      {activeTab === 'active_corpus' && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
            <div>
              <h3 className="text-base font-bold text-slate-800">
                Documentos que Componen el Corpus Activo
              </h3>
              <p className="text-xs text-slate-500">
                Solo estos fragmentos son autorizados para ser recuperados por el motor RAG en las consultas de usuarios.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {stats?.active_corpus && stats.active_corpus.length > 0 ? (
              stats.active_corpus.map((ver) => (
                <div key={ver.id} className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/40 space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="font-bold text-slate-900 text-sm">{ver.nombre}</span>
                      <div className="text-xs text-slate-500">
                        Familia: <span className="font-semibold text-slate-700">{ver.family_name || ver.family_id}</span>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded-full border border-emerald-300">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
                      ACTIVO
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 pt-2 border-t border-emerald-100 font-mono">
                    <div>ID: {ver.id}</div>
                    <div>Chunks: {ver.chunks_count}</div>
                    <div>Año: {ver.anio || 'N/A'}</div>
                    <div>Acuerdo: {ver.numero_acuerdo || 'N/A'}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-2 py-8 text-center text-slate-400">
                No hay ningún documento activo en el corpus normativo.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
