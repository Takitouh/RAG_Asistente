import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../components/admin/ProtectedRoute';
import { AdminDashboard } from '../components/admin/AdminDashboard';
import { VersionList } from '../components/admin/VersionList';
import { DocumentUploadModal } from '../components/admin/DocumentUploadModal';
import { AdminStats, NormativeVersion } from '../types';

const mockStats: AdminStats = {
  total_versions: 2,
  status_counts: {
    PROCESADO: 1,
    PENDIENTE_REVISION: 1,
    ERROR: 0,
    RECIBIDO: 0,
    EN_PROCESAMIENTO: 0,
  },
  active_version: {
    id: 'uts_tg_2019',
    document_id: 'doc_1',
    nombre: 'Reglamento 2019',
    numero_acuerdo: '001',
    anio: 2019,
    fecha_expedicion: '2019-01-01',
    estado_vigencia: 'Vigente',
    status: 'PROCESADO',
    status_message: 'Ok',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    activated_at: '2026-01-01T00:00:00Z',
    report_json: null,
    chunks_count: 181,
  },
  total_chunks: 181,
  total_traces: 6,
};

const mockVersions: NormativeVersion[] = [
  {
    id: 'uts_tg_2019',
    document_id: 'doc_1',
    nombre: 'Reglamento 2019',
    numero_acuerdo: '001',
    anio: 2019,
    fecha_expedicion: '2019-01-01',
    estado_vigencia: 'Vigente',
    status: 'PROCESADO',
    status_message: 'Indexado exitosamente',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    activated_at: '2026-01-01T00:00:00Z',
    report_json: null,
    chunks_count: 181,
  },
  {
    id: 'uts_tg_2021',
    document_id: 'doc_2',
    nombre: 'Reglamento 2021',
    numero_acuerdo: '005',
    anio: 2021,
    fecha_expedicion: '2021-05-10',
    estado_vigencia: 'Vigente',
    status: 'PROCESADO',
    status_message: 'Listo para activación',
    is_active: false,
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    activated_at: null,
    report_json: null,
    chunks_count: 195,
  },
  {
    id: 'uts_tg_escaneado',
    document_id: 'doc_3',
    nombre: 'Reglamento Escaneado',
    numero_acuerdo: '010',
    anio: 2023,
    fecha_expedicion: '2023-08-01',
    estado_vigencia: 'En Revisión',
    status: 'PENDIENTE_REVISION',
    status_message: 'Confianza OCR bajo umbral (71.5%)',
    is_active: false,
    created_at: '2026-01-03T00:00:00Z',
    updated_at: '2026-01-03T00:00:00Z',
    activated_at: null,
    report_json: null,
    chunks_count: 120,
  },
];

describe('Admin Panel Components & Security Tests', () => {
  it('1. ProtectedRoute: redirige a /admin/login si el usuario no está autenticado', () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route
            path="/admin"
            element={
              <ProtectedRoute isAuthenticated={false} isLoading={false}>
                <div>Contenido Administrativo Protegido</div>
              </ProtectedRoute>
            }
          />
          <Route path="/admin/login" element={<div>Pantalla de Login</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.queryByText('Contenido Administrativo Protegido')).not.toBeInTheDocument();
    expect(screen.getByText('Pantalla de Login')).toBeInTheDocument();
  });

  it('2. ProtectedRoute: permite el paso cuando el usuario está autenticado', () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route
            path="/admin"
            element={
              <ProtectedRoute isAuthenticated={true} isLoading={false}>
                <div>Contenido Administrativo Protegido</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Contenido Administrativo Protegido')).toBeInTheDocument();
  });

  it('3. AdminDashboard: renderiza métricas reales del corpus', () => {
    render(
      <AdminDashboard
        stats={mockStats}
        isLoading={false}
        onRefresh={vi.fn()}
        onOpenUploadModal={vi.fn()}
        onLogout={vi.fn()}
      />
    );

    expect(screen.getByText('Reglamento 2019')).toBeInTheDocument();
    expect(screen.getByText('181 chunks activos')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // total_versions
    expect(screen.getByText('181')).toBeInTheDocument(); // total_chunks
    expect(screen.getByText('6')).toBeInTheDocument(); // total_traces
  });

  it('4. VersionList: muestra versiones registradas y distingue versión activa', () => {
    render(
      <VersionList
        versions={mockVersions}
        isLoading={false}
        onRefresh={vi.fn()}
        onOpenDetail={vi.fn()}
        onOpenEditMetadata={vi.fn()}
      />
    );

    expect(screen.getByText('Reglamento 2019')).toBeInTheDocument();
    expect(screen.getByText('Reglamento 2021')).toBeInTheDocument();
    expect(screen.getByText('Reglamento Escaneado')).toBeInTheDocument();

    // Comprueba el badge ACTIVA en 2019
    expect(screen.getByText('ACTIVA')).toBeInTheDocument();

    // Comprueba que 2021 tiene botón "Activar" disponible
    const activateButtons = screen.getAllByRole('button', { name: /activar/i });
    expect(activateButtons.length).toBeGreaterThanOrEqual(1);

    // Comprueba que la versión PENDIENTE_REVISION muestra su estado
    expect(screen.getByText('Pendiente Revisión')).toBeInTheDocument();
  });

  it('5. DocumentUploadModal: valida archivo PDF antes de enviar', () => {
    render(
      <DocumentUploadModal
        isOpen={true}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
      />
    );

    expect(screen.getByText('Cargar Nueva Normativa (PDF)')).toBeInTheDocument();
    const submitBtn = screen.getByRole('button', { name: /cargar y procesar/i });
    expect(submitBtn).toBeDisabled(); // Deshabilitado porque aún no se selecciona archivo
  });
});
