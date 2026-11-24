import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ChatPage } from '../pages/ChatPage';
import { AdminDashboardPage } from '../pages/AdminDashboardPage';
import * as queryApi from '../api/query';
import * as adminApi from '../api/admin';
import { NormativeVersion, QueryResponse } from '../types';

describe('Integration Flow Tests (Chat & Admin)', () => {
  const mockActiveVersion: NormativeVersion = {
    id: 'uts_tg_2019',
    document_id: 'doc_1',
    nombre: 'Reglamento de Trabajo de Grado 2019',
    numero_acuerdo: 'Acuerdo 01-002',
    anio: 2019,
    fecha_expedicion: '2019-03-15',
    estado_vigencia: 'Vigente',
    status: 'PROCESADO',
    status_message: 'Indexado exitosamente',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    activated_at: '2026-01-01T00:00:00Z',
    report_json: null,
    chunks_count: 181,
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('Flujo completo de consulta en Chat: detecta versión activa, envía pregunta y renderiza citas', async () => {
    vi.spyOn(queryApi, 'getActiveVersion').mockResolvedValue({
      active_version: mockActiveVersion,
      has_active_version: true,
      message: 'Versión activa ok',
    });

    const mockQueryRes: QueryResponse = {
      answer: 'Para optar al grado el estudiante debe presentar su anteproyecto y matricular la modalidad elegida.',
      version_id: 'uts_tg_2019',
      document_name: 'reglamento_trabajo_grado.pdf',
      citations: [
        {
          chunk_id: 'chk_20',
          version_id: 'uts_tg_2019',
          document_id: 'doc_1',
          document_name: 'reglamento_trabajo_grado.pdf',
          capitulo_numero: 1,
          capitulo_romano: 'I',
          capitulo_titulo: 'Disposiciones Generales',
          articulo_numero: 5,
          articulo_ordinal: '5°',
          paragrafo_numero: null,
          inciso_marker: null,
          page_start: 4,
          page_end: 4,
          location_hint: 'Capítulo I, Artículo 5',
          texto_fragmento: 'El trabajo de grado es un requisito indispensable para optar al título académico.',
        },
      ],
      abstained: false,
      abstention_reason: null,
      disclaimer: 'Orientativo según F-DC-124.',
      trace_id: 'trace_abc123',
      latency_ms: 850,
    };

    const querySpy = vi.spyOn(queryApi, 'queryNormativa').mockResolvedValue(mockQueryRes);

    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    );

    // Esperar a que se cargue la versión activa en el campo de entrada
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Reglamento de Trabajo de Grado 2019/i)).toBeInTheDocument();
    });

    // Enviar pregunta
    const input = screen.getByLabelText(/campo de pregunta/i);
    fireEvent.change(input, { target: { value: '¿Es obligatorio el trabajo de grado?' } });

    const sendBtn = screen.getByLabelText(/enviar pregunta/i);
    fireEvent.click(sendBtn);

    // Esperar a que aparezca la respuesta del asistente y las citas
    await waitFor(() => {
      expect(querySpy).toHaveBeenCalledWith('¿Es obligatorio el trabajo de grado?');
      expect(screen.getByText(/Para optar al grado el estudiante debe presentar su anteproyecto/i)).toBeInTheDocument();
      expect(screen.getByText(/Capítulo I • Art\. 5/i)).toBeInTheDocument();
      expect(screen.getByText(/Orientativo según F-DC-124/i)).toBeInTheDocument();
    });
  });

  it('Flujo administrativo: carga estadísticas reales y lista de reglamentos', async () => {
    vi.spyOn(adminApi, 'getAdminStats').mockResolvedValue({
      total_versions: 1,
      status_counts: {
        PROCESADO: 1,
        PENDIENTE_REVISION: 0,
        ERROR: 0,
        RECIBIDO: 0,
        EN_PROCESAMIENTO: 0,
      },
      active_version: mockActiveVersion,
      total_chunks: 181,
      total_traces: 10,
    });

    vi.spyOn(adminApi, 'listAdminVersions').mockResolvedValue([mockActiveVersion]);

    render(
      <MemoryRouter>
        <AdminDashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Panel de Administración del Corpus Normativo')).toBeInTheDocument();
      expect(screen.getByText('181 chunks activos')).toBeInTheDocument();
      expect(screen.getByText('1 reglamentos en base de datos')).toBeInTheDocument();
    });
  });
});
