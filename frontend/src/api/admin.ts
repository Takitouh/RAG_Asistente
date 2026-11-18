import { apiClient } from './client';
import {
  AdminStats,
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

export async function listAdminVersions(): Promise<NormativeVersion[]> {
  return apiClient<NormativeVersion[]>('/api/admin/versions');
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
  }
): Promise<{ success: boolean; message: string; version: NormativeVersion }> {
  const params = new URLSearchParams();
  if (metadata.nombre !== undefined) params.append('nombre', metadata.nombre);
  if (metadata.numero_acuerdo !== undefined) params.append('numero_acuerdo', metadata.numero_acuerdo);
  if (metadata.anio !== undefined) params.append('anio', String(metadata.anio));
  if (metadata.fecha_expedicion !== undefined) params.append('fecha_expedicion', metadata.fecha_expedicion);
  if (metadata.estado_vigencia !== undefined) params.append('estado_vigencia', metadata.estado_vigencia);

  return apiClient(`/api/admin/versions/${encodeURIComponent(versionId)}/metadata?${params.toString()}`, {
    method: 'PATCH',
  });
}

export async function deleteVersion(versionId: string): Promise<{ success: boolean; message: string }> {
  return apiClient(`/api/admin/versions/${encodeURIComponent(versionId)}`, {
    method: 'DELETE',
  });
}
