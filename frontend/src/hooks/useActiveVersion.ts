import { useState, useEffect, useCallback, useRef } from 'react';
import { NormativeVersion } from '../types';
import { getActiveVersion } from '../api/query';

export function useActiveVersion() {
  const [activeVersion, setActiveVersion] = useState<NormativeVersion | null>(null);
  const [hasActiveVersion, setHasActiveVersion] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [versionChangedWarning, setVersionChangedWarning] = useState<string | null>(null);

  const previousVersionIdRef = useRef<string | null>(null);

  const fetchVersion = useCallback(async () => {
    try {
      const data = await getActiveVersion();
      const current = data.active_version;
      const currentId = current?.id || null;

      // Detectar cambio de versión si ya teníamos una cargada
      if (
        previousVersionIdRef.current !== null &&
        previousVersionIdRef.current !== currentId
      ) {
        if (current) {
          setVersionChangedWarning(
            `El administrador activó una nueva normativa: "${current.nombre}". Las nuevas consultas utilizarán esta fuente.`
          );
        } else {
          setVersionChangedWarning(
            'El administrador desactivó la normativa activa. No es posible realizar nuevas consultas hasta que se active otra.'
          );
        }
      }

      previousVersionIdRef.current = currentId;
      setActiveVersion(current);
      setHasActiveVersion(data.has_active_version);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Error al consultar la versión activa.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVersion();
    // Sondeo suave cada 30 segundos para detectar cambios administrativos
    const timer = setInterval(fetchVersion, 30000);
    return () => clearInterval(timer);
  }, [fetchVersion]);

  const dismissWarning = useCallback(() => {
    setVersionChangedWarning(null);
  }, []);

  return {
    activeVersion,
    hasActiveVersion,
    isLoading,
    error,
    versionChangedWarning,
    dismissWarning,
    refetchActiveVersion: fetchVersion,
  };
}
