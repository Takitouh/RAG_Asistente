export type ProcessingStatus =
  | 'RECIBIDO'
  | 'EN_PROCESAMIENTO'
  | 'PENDIENTE_REVISION'
  | 'PROCESADO'
  | 'ERROR';

export type ReviewStatus =
  | 'PENDIENTE'
  | 'APROBADO'
  | 'RECHAZADO'
  | 'CON_DISCREPANCIAS';

export interface DocumentCategory {
  id: string;
  nombre: string;
  descripcion: string | null;
  estado: 'ACTIVO' | 'INACTIVO';
  created_at: string;
  updated_at: string;
}

export interface DocumentFamily {
  id: string;
  categoria_id: string;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  perfil_procesamiento?: string;
  estado: 'ACTIVO' | 'INACTIVO';
  created_at: string;
  updated_at: string;
  categoria_nombre?: string | null;
}

export interface Citation {
  chunk_id: string;
  version_id: string;
  document_id: string;
  document_name: string;
  capitulo_numero: number | null;
  capitulo_romano: string | null;
  capitulo_titulo: string | null;
  articulo_numero: number | null;
  articulo_ordinal: string | null;
  paragrafo_numero: string | null;
  inciso_marker: string | null;
  page_start: number;
  page_end: number;
  location_hint: string;
  texto_fragmento: string;
}

export interface QueryResponse {
  answer: string;
  version_id: string | null;
  document_name: string | null;
  citations: Citation[];
  abstained: boolean;
  abstention_reason: string | null;
  disclaimer: string;
  trace_id: string;
  latency_ms: number;
  response_type?: 'greeting' | 'normative' | 'clarification' | 'abstention';
  clarification_needed?: boolean;
  clarification_question?: string | null;
  authorized_versions?: string[];
}

export interface NormativeVersion {
  id: string;
  document_id: string;
  family_id?: string;
  nombre: string;
  numero_version_institucional?: string | null;
  numero_acuerdo: string | null;
  anio: number | null;
  fecha_expedicion: string | null;
  procedencia?: string | null;
  estado_vigencia: string | null;
  status: ProcessingStatus;
  status_message: string | null;
  estado_revision?: ReviewStatus;
  fecha_revision?: string | null;
  observaciones_revision?: string | null;
  inconsistencia_identidad?: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  activated_at: string | null;
  report_json: string | null;
  chunks_count: number;
  file_hash?: string | null;
  family_name?: string | null;
  categoria_id?: string | null;
  categoria_nombre?: string | null;
}

export interface ActiveVersionResponse {
  active_version: NormativeVersion | null;
  has_active_version: boolean;
  active_corpus?: NormativeVersion[];
  message: string;
}

export interface AdminStats {
  total_categories?: number;
  total_families?: number;
  total_versions: number;
  status_counts: Record<ProcessingStatus, number>;
  active_version: NormativeVersion | null;
  active_corpus?: NormativeVersion[];
  total_chunks: number;
  total_traces: number;
  inconsistent_versions_count?: number;
}

export interface ExtractionReport {
  num_pages: number;
  extraction_methods: {
    text_layer: number;
    ocr: number;
  };
  ocr_confidence_mean: number | null;
  anomalies: string[];
  repairs: Array<{
    tipo: string;
    descripcion: string;
  }>;
  statistics: Record<string, any>;
  cleaning_statistics?: Record<string, any>;
}

export interface VersionReportResponse {
  version_id: string;
  status: string;
  has_report: boolean;
  report: ExtractionReport | null;
  message?: string;
}

export interface ChatMessageItem {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  version_id?: string | null;
  document_name?: string | null;
  citations?: Citation[];
  abstained?: boolean;
  abstention_reason?: string | null;
  latency_ms?: number;
  error?: boolean;
  disclaimer?: string;
  response_type?: 'greeting' | 'normative' | 'clarification' | 'abstention';
  clarification_needed?: boolean;
  clarification_question?: string | null;
}
