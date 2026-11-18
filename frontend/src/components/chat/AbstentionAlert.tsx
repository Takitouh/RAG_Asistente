import React from 'react';
import { ShieldAlert, HelpCircle } from 'lucide-react';

interface AbstentionAlertProps {
  reason?: string | null;
  messageText?: string;
}

export const AbstentionAlert: React.FC<AbstentionAlertProps> = ({
  reason,
  messageText,
}) => {
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50/80 p-4 text-amber-900 shadow-xs">
      <div className="flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1.5 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-xs sm:text-sm uppercase tracking-wider text-amber-900">
              Abstención Normativa
            </span>
            <span className="text-[10px] bg-amber-200/80 text-amber-800 font-semibold px-2 py-0.5 rounded-full">
              Evidencia Insuficiente
            </span>
          </div>

          <p className="text-xs sm:text-sm text-amber-800 leading-relaxed">
            {messageText ||
              'El asistente no encontró evidencia suficiente en el reglamento activo para responder con certeza jurídica a esta consulta.'}
          </p>

          {reason && (
            <div className="text-xs text-amber-700 font-mono bg-amber-100/70 p-2 rounded border border-amber-200 mt-2">
              <strong>Motivo de abstención:</strong> {reason}
            </div>
          )}

          <div className="pt-2 border-t border-amber-200/60 text-[11px] text-amber-700 flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>
              Sugerencia: Intente reformular su consulta con términos formales del reglamento (e.g. modalidades, proyecto, comité, plazos, evaluación).
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
