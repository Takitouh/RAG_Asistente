import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAdminAuth } from '../hooks/useAdminAuth';
import { AdminStats, NormativeVersion } from '../types';
import { getAdminStats, listAdminVersions } from '../api/admin';
import { ApiError } from '../api/client';
import { AdminDashboard } from '../components/admin/AdminDashboard';
import { VersionList } from '../components/admin/VersionList';
import { DocumentUploadModal } from '../components/admin/DocumentUploadModal';
import { DocumentDetailModal } from '../components/admin/DocumentDetailModal';
import { MetadataEditModal } from '../components/admin/MetadataEditModal';

export const AdminDashboardPage: React.FC = () => {
  const { logout } = useAdminAuth();
  const navigate = useNavigate();

  const [stats, setStats] = useState<AdminStats | null>(null);
  const [versions, setVersions] = useState<NormativeVersion[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'versions' | 'hierarchy' | 'active_corpus'>('versions');

  // Estados de modales
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedVersionForDetail, setSelectedVersionForDetail] = useState<NormativeVersion | null>(null);
  const [selectedVersionForEdit, setSelectedVersionForEdit] = useState<NormativeVersion | null>(null);

  const handleLogout = useCallback(async () => {
    await logout();
    setStats(null);
    setVersions([]);
    setSelectedVersionForDetail(null);
    setSelectedVersionForEdit(null);
    navigate('/admin/login', { replace: true });
  }, [logout, navigate]);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [statsData, versionsData] = await Promise.all([
        getAdminStats(),
        listAdminVersions(),
      ]);
      setStats(statsData);
      setVersions(versionsData);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 401) {
        await handleLogout();
        return;
      }
    } finally {
      setIsLoading(false);
    }
  }, [handleLogout]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Resumen y Navegación de Pestañas */}
      <AdminDashboard
        stats={stats}
        isLoading={isLoading}
        onRefresh={loadData}
        onOpenUploadModal={() => setIsUploadOpen(true)}
        onLogout={handleLogout}
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
      />

      {/* Vista de Versiones Normativas */}
      {activeTab === 'versions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-800">
              Reglamentos y Versiones Normativas
            </h2>
            <span className="text-xs text-slate-500">
              {versions.length} reglamentos en base de datos
            </span>
          </div>

          <VersionList
            versions={versions}
            isLoading={isLoading}
            onRefresh={loadData}
            onOpenDetail={(v) => setSelectedVersionForDetail(v)}
            onOpenEditMetadata={(v) => setSelectedVersionForEdit(v)}
          />
        </div>
      )}

      {/* Modal de Carga de Documento */}
      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={loadData}
      />

      {/* Modal de Detalle y Auditoría OCR */}
      <DocumentDetailModal
        isOpen={!!selectedVersionForDetail}
        onClose={() => setSelectedVersionForDetail(null)}
        version={selectedVersionForDetail}
        onVersionUpdated={() => {
          loadData();
        }}
      />

      {/* Modal de Edición de Metadatos */}
      <MetadataEditModal
        isOpen={!!selectedVersionForEdit}
        onClose={() => setSelectedVersionForEdit(null)}
        version={selectedVersionForEdit}
        onSuccess={loadData}
      />
    </div>
  );
};
