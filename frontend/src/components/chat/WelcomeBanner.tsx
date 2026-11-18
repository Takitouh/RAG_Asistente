import React from 'react';
import { BookOpen, HelpCircle, CheckCircle2, AlertTriangle } from 'lucide-react';
import { NormativeVersion } from '../../types';

interface WelcomeBannerProps {
  activeVersion: NormativeVersion | null;
  onSelectPrompt: (prompt: string) => void;
}

export const WelcomeBanner: React.FC<WelcomeBannerProps> = ({
  activeVersion,
  onSelectPrompt,
}) => {
  const exampleQuestions = [
    '¿Cuáles son las modalidades de trabajo de grado permitidas?',
    '¿Qué requisitos debe cumplir un estudiante para postular su propuesta?',
    '¿Cuál es el plazo máximo para presentar el informe final de grado?',
    '¿Qué causales existen para la reprobación de un proyecto de grado?',
  ];

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 text-center">
      <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-uts-green-100 text-uts-green-800 mb-4 shadow-xs">
        <BookOpen className="w-8 h-8 text-uts-green-700" />
      </div>

      <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
        Consulta del Reglamento de Trabajo de Grado
      </h1>
      <p className="mt-2 text-sm sm:text-base text-slate-600 max-w-xl mx-auto">
        Asistente académico basado en RAG para orientar a estudiantes, directores y evaluadores sobre la normativa oficial de las UTS.
      </p>

      {/* Tarjeta de estado de la normativa activa */}
      <div className="mt-6 p-4 rounded-xl border bg-white shadow-xs max-w-xl mx-auto text-left">
        {activeVersion ? (
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs uppercase font-semibold text-emerald-800 tracking-wider">
                Reglamento Oficial Activo
              </div>
              <div className="text-sm font-bold text-slate-900 mt-0.5">
                {activeVersion.nombre}
              </div>
              <div className="text-xs text-slate-500 mt-1 flex flex-wrap gap-x-3 gap-y-1">
                {activeVersion.numero_acuerdo && (
                  <span>Acuerdo: <strong>{activeVersion.numero_acuerdo}</strong></span>
                )}
                {activeVersion.anio && (
                  <span>Año: <strong>{activeVersion.anio}</strong></span>
                )}
                <span>Chunks indexados: <strong>{activeVersion.chunks_count}</strong></span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-3 text-amber-800">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs uppercase font-semibold text-amber-800 tracking-wider">
                Sin normativa activa
              </div>
              <p className="text-xs text-amber-700 mt-1">
                Actualmente no hay ninguna versión del reglamento activa en el sistema. Un administrador debe activar un reglamento procesado desde el panel para habilitar las consultas.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Preguntas de ejemplo */}
      {activeVersion && (
        <div className="mt-8 text-left max-w-2xl mx-auto">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
            <HelpCircle className="w-4 h-4 text-uts-green-700" />
            <span>Consultas frecuentes sobre la normativa</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {exampleQuestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectPrompt(q)}
                className="p-3 text-left rounded-lg border border-slate-200 bg-white hover:bg-uts-green-50/50 hover:border-uts-green-300 text-xs sm:text-sm text-slate-700 transition-all shadow-xs group"
              >
                <span className="group-hover:text-uts-green-900 font-medium leading-snug block">
                  {q}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
