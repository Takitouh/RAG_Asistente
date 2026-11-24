import React from 'react';
import { BookOpen, HelpCircle } from 'lucide-react';
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
