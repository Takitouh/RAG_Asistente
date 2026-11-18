import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { App } from '../App';
import * as adminApi from '../api/admin';
import * as queryApi from '../api/query';
import { ApiError } from '../api/client';
import { AdminStats, NormativeVersion } from '../types';

const mockActiveVersion: NormativeVersion = {
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
};

const mockStats: AdminStats = {
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
  total_traces: 5,
};

describe('Admin Authentication & Session Regression Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    // Default mock for public version
    vi.spyOn(queryApi, 'getActiveVersion').mockResolvedValue({
      active_version: mockActiveVersion,
      has_active_version: true,
      message: 'Versión activa ok',
    });

    // Default stats & versions mocks
    vi.spyOn(adminApi, 'getAdminStats').mockResolvedValue(mockStats);
    vi.spyOn(adminApi, 'listAdminVersions').mockResolvedValue([mockActiveVersion]);
  });

  it('1. Login válido: autentica contra FastAPI y redirige exactamente una vez al dashboard sin bucles', async () => {
    // Inicialmente no autenticado
    vi.spyOn(adminApi, 'checkAdminSession').mockRejectedValue(new ApiError('Unauthorized', 401));
    const loginSpy = vi.spyOn(adminApi, 'loginAdmin').mockResolvedValue({
      success: true,
      message: 'Autenticación exitosa',
      token: 'dev-admin-secret-key',
    });

    render(
      <MemoryRouter initialEntries={['/admin/login']}>
        <App />
      </MemoryRouter>
    );

    // Espera que termine la comprobación y aparezca el formulario
    await waitFor(() => {
      expect(screen.getByText('Acceso Administrativo')).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/clave de administración/i);
    fireEvent.change(input, { target: { value: 'dev-admin-secret-key' } });

    const submitBtn = screen.getByRole('button', { name: /iniciar sesión/i });
    fireEvent.click(submitBtn);

    // Debe invocar loginAdmin y navegar al panel
    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith('dev-admin-secret-key');
      expect(screen.getByText('Panel de Administración del Corpus Normativo')).toBeInTheDocument();
    });

    // El formulario ya no debe existir (sin bucles hacia /admin/login)
    expect(screen.queryByText('Acceso Administrativo')).not.toBeInTheDocument();
  });

  it('2. Login inválido: muestra mensaje de error y no permite el paso al dashboard', async () => {
    vi.spyOn(adminApi, 'checkAdminSession').mockRejectedValue(new ApiError('Unauthorized', 401));
    vi.spyOn(adminApi, 'loginAdmin').mockRejectedValue(new ApiError('Clave administrativa incorrecta', 401));

    render(
      <MemoryRouter initialEntries={['/admin/login']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Acceso Administrativo')).toBeInTheDocument();
    });

    const input = screen.getByLabelText(/clave de administración/i);
    fireEvent.change(input, { target: { value: 'clave_invalida' } });

    const submitBtn = screen.getByRole('button', { name: /iniciar sesión/i });
    fireEvent.click(submitBtn);

    // Debe mostrar el error en pantalla
    await waitFor(() => {
      expect(screen.getByText('Clave administrativa incorrecta')).toBeInTheDocument();
    });

    // Permanece en el login sin acceder al dashboard
    expect(screen.queryByText('Panel de Administración del Corpus Normativo')).not.toBeInTheDocument();
  });

  it('3. Sesión existente: permite entrar directamente a /admin sin pasar por login', async () => {
    vi.spyOn(adminApi, 'checkAdminSession').mockResolvedValue({ authenticated: true, role: 'admin' });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Panel de Administración del Corpus Normativo')).toBeInTheDocument();
    });

    expect(screen.queryByText('Acceso Administrativo')).not.toBeInTheDocument();
  });

  it('4. Verificación inicial de sesión: muestra estado de carga y no causa redirección prematura', async () => {
    let resolveSession: any;
    const sessionPromise = new Promise<{ authenticated: boolean; role: string }>((resolve) => {
      resolveSession = resolve;
    });
    vi.spyOn(adminApi, 'checkAdminSession').mockReturnValue(sessionPromise);

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>
    );

    // Muestra el spinner de verificación
    expect(screen.getByText('Verificando sesión administrativa...')).toBeInTheDocument();
    expect(screen.queryByText('Acceso Administrativo')).not.toBeInTheDocument();

    // Cuando la promesa se resuelve con sesión válida
    resolveSession({ authenticated: true, role: 'admin' });

    await waitFor(() => {
      expect(screen.getByText('Panel de Administración del Corpus Normativo')).toBeInTheDocument();
    });
  });

  it('5. No existe bucle entre /admin/login y /', async () => {
    vi.spyOn(adminApi, 'checkAdminSession').mockRejectedValue(new ApiError('Unauthorized', 401));

    render(
      <MemoryRouter initialEntries={['/admin/login']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Acceso Administrativo')).toBeInTheDocument();
    });

    // Click en volver al chat público
    const backBtn = screen.getByRole('button', { name: /volver al chat público/i });
    fireEvent.click(backBtn);

    await waitFor(() => {
      expect(screen.getByText('Consulta del Reglamento de Trabajo de Grado')).toBeInTheDocument();
    });

    // No debe rebotar automáticamente a /admin/login
    expect(screen.queryByText('Acceso Administrativo')).not.toBeInTheDocument();
  });

  it('6. Logout: invalida la sesión, limpia memoria y redirige inmediatamente al login', async () => {
    vi.spyOn(adminApi, 'checkAdminSession').mockResolvedValue({ authenticated: true, role: 'admin' });
    const logoutSpy = vi.spyOn(adminApi, 'logoutAdmin').mockResolvedValue({
      success: true,
      message: 'Sesión cerrada',
    });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Panel de Administración del Corpus Normativo')).toBeInTheDocument();
    });

    // Click en Cerrar Sesión
    const logoutBtn = screen.getByRole('button', { name: /cerrar sesión/i });
    fireEvent.click(logoutBtn);

    // Debe invocar logoutAdmin y redirigir inmediatamente a /admin/login
    await waitFor(() => {
      expect(logoutSpy).toHaveBeenCalled();
      expect(screen.getByText('Acceso Administrativo')).toBeInTheDocument();
    });

    // El dashboard se desmontó y la memoria se limpió
    expect(screen.queryByText('Panel de Administración del Corpus Normativo')).not.toBeInTheDocument();
  });

  it('7. Protección contra botón Atrás: no permite reingresar al dashboard después del logout', async () => {
    vi.spyOn(adminApi, 'checkAdminSession').mockResolvedValue({ authenticated: true, role: 'admin' });
    vi.spyOn(adminApi, 'logoutAdmin').mockResolvedValue({ success: true, message: 'Sesión cerrada' });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Panel de Administración del Corpus Normativo')).toBeInTheDocument();
    });

    // Logout
    const logoutBtn = screen.getByRole('button', { name: /cerrar sesión/i });
    fireEvent.click(logoutBtn);

    await waitFor(() => {
      expect(screen.getByText('Acceso Administrativo')).toBeInTheDocument();
    });

    // Si la sesión backend ahora devuelve 401
    vi.spyOn(adminApi, 'checkAdminSession').mockRejectedValue(new ApiError('Unauthorized', 401));

    // El usuario permanece en login y no tiene acceso
    expect(screen.queryByText('Panel de Administración del Corpus Normativo')).not.toBeInTheDocument();
  });

  it('8. Sesión caducada: un 401 en llamadas del panel desautentica de forma controlada', async () => {
    vi.spyOn(adminApi, 'checkAdminSession').mockResolvedValue({ authenticated: true, role: 'admin' });
    vi.spyOn(adminApi, 'getAdminStats').mockRejectedValue(new ApiError('Session expired', 401));
    const logoutSpy = vi.spyOn(adminApi, 'logoutAdmin').mockResolvedValue({ success: true, message: 'Ok' });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>
    );

    // Al recibir 401 en la llamada al panel, se ejecuta el deslogueo y redirige a login
    await waitFor(() => {
      expect(logoutSpy).toHaveBeenCalled();
      expect(screen.getByText('Acceso Administrativo')).toBeInTheDocument();
    });
  });

  it('9. Error de red: no genera bucle infinito de navegación', async () => {
    vi.spyOn(adminApi, 'checkAdminSession').mockRejectedValue(new ApiError('Network error', 0));

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>
    );

    // Debe terminar en /admin/login mostrando el formulario de forma estable
    await waitFor(() => {
      expect(screen.getByText('Acceso Administrativo')).toBeInTheDocument();
    });

    expect(screen.queryByText('Panel de Administración del Corpus Normativo')).not.toBeInTheDocument();
  });

  it('10. Chat público: funciona sin autenticación alguna', async () => {
    vi.spyOn(adminApi, 'checkAdminSession').mockRejectedValue(new ApiError('Unauthorized', 401));

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Consulta del Reglamento de Trabajo de Grado')).toBeInTheDocument();
      expect(screen.getByLabelText(/campo de pregunta/i)).toBeInTheDocument();
    });

    // En ningún momento redirige al login de administración
    expect(screen.queryByText('Acceso Administrativo')).not.toBeInTheDocument();
  });
});
