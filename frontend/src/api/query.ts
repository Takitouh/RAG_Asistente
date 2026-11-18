import { apiClient } from './client';
import { ActiveVersionResponse, QueryResponse } from '../types';

export async function getActiveVersion(): Promise<ActiveVersionResponse> {
  return apiClient<ActiveVersionResponse>('/api/versions/active');
}

export async function queryNormativa(query: string): Promise<QueryResponse> {
  return apiClient<QueryResponse>('/api/query', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
}

export function getVersionPdfUrl(versionId: string, page?: number): string {
  const base = `/api/versions/${encodeURIComponent(versionId)}/pdf`;
  return page ? `${base}#page=${page}` : base;
}
