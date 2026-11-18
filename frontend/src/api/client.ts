export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

let onUnauthorizedCallback: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorizedCallback = handler;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const defaultHeaders: HeadersInit = {};
  
  if (!(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  const config: RequestInit = {
    ...options,
    credentials: 'include', // Para enviar y recibir cookies de sesión de FastAPI
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };

  let response: Response;
  try {
    response = await fetch(endpoint, config);
  } catch (err: any) {
    throw new ApiError(
      'No se pudo conectar con el servidor backend FastAPI. Verifique que el servicio esté en ejecución.',
      0,
      err
    );
  }

  if (!response.ok) {
    // Si la sesión expiró o las credenciales ya no son válidas en una llamada protegida
    if (
      response.status === 401 &&
      endpoint.startsWith('/api/admin') &&
      endpoint !== '/api/admin/login' &&
      endpoint !== '/api/admin/me'
    ) {
      if (onUnauthorizedCallback) {
        onUnauthorizedCallback();
      }
    }

    let errorDetail = `Error ${response.status}: ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (errorJson?.detail) {
        errorDetail = typeof errorJson.detail === 'string' 
          ? errorJson.detail 
          : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Ignorar fallo de parseo JSON
    }
    throw new ApiError(errorDetail, response.status);
  }

  // Si la respuesta no tiene contenido (204)
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}
