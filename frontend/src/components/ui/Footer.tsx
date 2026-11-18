import React from 'react';
import { Info, ShieldAlert } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto py-6 text-xs text-slate-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-start gap-2.5 max-w-2xl text-center md:text-left">
            <Info className="w-4 h-4 text-uts-green-700 shrink-0 mt-0.5 hidden sm:block" />
            <p className="leading-relaxed">
              <strong className="text-slate-700">NORMATIVA-TG UTS (F-DC-124):</strong> Prototipo académico de asistencia inteligente basado en RAG para la consulta del Reglamento de Trabajo de Grado de las Unidades Tecnológicas de Santander.
            </p>
          </div>

          <div className="flex items-center gap-2 text-slate-400 text-[11px] shrink-0">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
            <span>Orientativo • No vinculante oficialmente</span>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-400 gap-2">
          <div>
            Desarrollado con FastAPI, React, TypeScript, Qdrant y Ollama local.
          </div>
          <div>
            Unidades Tecnológicas de Santander — Bucaramanga, Colombia
          </div>
        </div>
      </div>
    </footer>
  );
};
