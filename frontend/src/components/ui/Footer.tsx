import React from 'react';
import { Info } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto py-6 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-start gap-2.5 max-w-2xl text-center sm:text-left">
            <Info className="w-4 h-4 text-uts-green-700 shrink-0 mt-0.5 hidden sm:block" />
            <p className="leading-relaxed">
              <strong className="text-slate-700">NORMATIVA-TG UTS:</strong> Prototipo académico de asistencia inteligente basado en RAG para la consulta del Reglamento de Trabajo de Grado de la Universitaria Tecnológica de Santander.
            </p>
          </div>

          <div className="text-[11px] text-slate-400">
            Universitaria Tecnológica de Santander — Bucaramanga, Colombia
          </div>
        </div>
      </div>
    </footer>
  );
};
