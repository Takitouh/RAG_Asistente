import { apiClient } from './client';
import {
  AdminStats,
  DocumentCategory,
  DocumentFamily,
  NormativeVersion,
  VersionReportResponse,
} from '../types';

export async function loginAdmin(adminKey: string): Promise<{ success: boolean; message: string; token: string }> {
  return apiClient('/api/admin/login', {
    method: 'POST',
    body: JSON.stringify({ admin_key: adminKey }),
  });
}

export async function logoutAdmin(): Promise<{ success: boolean; message: string }> {
  return apiClient('/api/admin/logout', {
    method: 'POST',
  });
}

export async function checkAdminSession(): Promise<{ authenticated: boolean; role: string }> {
  return apiClient('/api/admin/me');
}

export async function getAdminStats(): Promise<AdminStats> {
  return apiClient<AdminStats>('/api/admin/stats');
}

// --- Categorías Documentales ---

export async function listCategories(includeInactive: boolean = true): Promise<DocumentCategory[]> {
  return apiClient<DocumentCategory[]>(`/api/admin/categories?include_inactive=${includeInactive}`);
}

export async function createCategory(data: {
  id: string;
  nombre: string;
  descripcion?: string;
  estado?: string;
}): Promise<DocumentCategory> {
  return apiClient<DocumentCategory>('/api/admin/categories', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCategory(
  id: string,
  data: { nombre?: string; descripcion?: string; estado?: string }
): Promise<DocumentCategory> {
  return apiClient<DocumentCategory>(`/api/admin/categories/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteCategory(id: string): Promise<{ success: boolean; message: string }> {
  return apiClient(`/api/admin/categories/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

// --- Familias Documentales ---

export async function listFamilies(categoriaId?: string, includeInactive: boolean = true): Promise<DocumentFamily[]> {
  const params = new URLSearchParams();
  if (categoriaId) params.append('categoria_id', categoriaId);
  params.append('include_inactive', String(includeInactive));
  return apiClient<DocumentFamily[]>(`/api/admin/families?${params.toString()}`);
}

export async function createFamily(data: {
  id: string;
  categoria_id: string;
  codigo: string;
  nombre: string;
  descripcion?: string;
  perfil_procesamiento?: string;
  estado?: string;
}): Promise<DocumentFamily> {
  return apiClient<DocumentFamily>('/api/admin/families', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateFamily(
  id: string,
  data: {
    categoria_id?: string;
    codigo?: string;
    nombre?: string;
    descripcion?: string;
    perfil_procesamiento?: string;
    estado?: string;
  }
): Promise<DocumentFamily> {
  return apiClient<DocumentFamily>(`/api/admin/families/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteFamily(id: string): Promise<{ success: boolean; message: string }> {
  return apiClient(`/api/admin/families/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

// --- Versiones Documentales ---

export async function listAdminVersions(familyId?: string): Promise<NormativeVersion[]> {
  const url = familyId
    ? `/api/admin/versions?family_id=${encodeURIComponent(familyId)}`
    : '/api/admin/versions';
  return apiClient<NormativeVersion[]>(url);
}

export async function listActiveCorpus(): Promise<NormativeVersion[]> {
  return apiClient<NormativeVersion[]>('/api/admin/active-corpus');
}

export async function getAdminVersion(versionId: string): Promise<NormativeVersion> {
  return apiClient<NormativeVersion>(`/api/admin/versions/${encodeURIComponent(versionId)}`);
}

export async function getAdminVersionReport(versionId: string): Promise<VersionReportResponse> {
  return apiClient<VersionReportResponse>(`/api/admin/versions/${encodeURIComponent(versionId)}/report`);
}

export async function uploadDocument(formData: FormData): Promise<{
  document: any;
  version: NormativeVersion;
  warning?: string;
}> {
  return apiClient('/api/admin/documents', {
    method: 'POST',
    body: formData,
  });
}

export async function processVersion(versionId: string, forceOcr: boolean = false): Promise<NormativeVersion> {
  return apiClient(`/api/admin/versions/${encodeURIComponent(versionId)}/process?force_ocr=${forceOcr}`, {
    method: 'POST',
  });
}

export async function reviewVersion(
  versionId: string,
  action: 'approve' | 'reject',
  notes?: string
): Promise<{ success: boolean; message: string; version: NormativeVersion }> {
  return apiClient(`/api/admin/versions/${encodeURIComponent(versionId)}/review`, {
    method: 'POST',
    body: JSON.stringify({ action, notes }),
  });
}

export async function activateVersion(versionId: string): Promise<{ success: boolean; message: string; version: NormativeVersion }> {
  return apiClient(`/api/admin/versions/${encodeURIComponent(versionId)}/activate`, {
    method: 'POST',
  });
}

export async function deactivateVersion(versionId: string): Promise<{ success: boolean; message: string; version: NormativeVersion }> {
  return apiClient(`/api/admin/versions/${encodeURIComponent(versionId)}/deactivate`, {
    method: 'POST',
  });
}

export async function updateVersionMetadata(
  versionId: string,
  metadata: {
    nombre?: string;
    numero_acuerdo?: string;
    anio?: number;
    fecha_expedicion?: string;
    estado_vigencia?: string;
    family_id?: string;
    numero_version_institucional?: string;
    procedencia?: string;
    estado_revision?: string;
    observaciones_revision?: string;
  }
): Promise<{ success: boolean; message: string; version: NormativeVersion }> {
  const params = new URLSearchParams();
  if (metadata.nombre !== undefined) params.append('nombre', metadata.nombre);
  if (metadata.numero_acuerdo !== undefined) params.append('numero_acuerdo', metadata.numero_acuerdo);
  if (metadata.anio !== undefined) params.append('anio', String(metadata.anio));
  if (metadata.fecha_expedicion !== undefined) params.append('fecha_expedicion', metadata.fecha_expedicion);
  if (metadata.estado_vigencia !== undefined) params.append('estado_vigencia', metadata.estado_vigencia);
  if (metadata.family_id !== undefined) params.append('family_id', metadata.family_id);
  if (metadata.numero_version_institucional !== undefined) params.append('numero_version_institucional', metadata.numero_version_institucional);
  if (metadata.procedencia !== undefined) params.append('procedencia', metadata.procedencia);
  if (metadata.estado_revision !== undefined) params.append('estado_revision', metadata.estado_revision);
  if (metadata.observaciones_revision !== undefined) params.append('observaciones_revision', metadata.observaciones_revision);

  return apiClient(`/api/admin/versions/${encodeURIComponent(versionId)}/metadata?${params.toString()}`, {
    method: 'PATCH',
  });
}

export async function deleteVersion(versionId: string): Promise<{ success: boolean; message: string }> {
  return apiClient(`/api/admin/versions/${encodeURIComponent(versionId)}`, {
    method: 'DELETE',
  });
}
