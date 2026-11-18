import React from 'react';
import { ProcessingStatus } from '../../types';

interface BadgeProps {
  status?: ProcessingStatus | 'ACTIVO' | 'INACTIVO';
  children?: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ status, children, className = '' }) => {
  let colorClasses = 'bg-slate-100 text-slate-700 border-slate-300';
  let label = children;

  switch (status) {
    case 'PROCESADO':
      colorClasses = 'bg-emerald-50 text-emerald-800 border-emerald-200';
      label = label || 'Procesado';
      break;
    case 'PENDIENTE_REVISION':
      colorClasses = 'bg-amber-50 text-amber-800 border-amber-200';
      label = label || 'Pendiente Revisión';
      break;
    case 'EN_PROCESAMIENTO':
      colorClasses = 'bg-blue-50 text-blue-800 border-blue-200 animate-pulse';
      label = label || 'En Procesamiento';
      break;
    case 'RECIBIDO':
      colorClasses = 'bg-slate-50 text-slate-700 border-slate-200';
      label = label || 'Recibido';
      break;
    case 'ERROR':
      colorClasses = 'bg-rose-50 text-rose-800 border-rose-200';
      label = label || 'Error';
      break;
    case 'ACTIVO':
      colorClasses = 'bg-uts-green-50 text-uts-green-800 border-uts-green-300 ring-1 ring-uts-green-400';
      label = label || 'Activo';
      break;
    case 'INACTIVO':
      colorClasses = 'bg-slate-100 text-slate-500 border-slate-200';
      label = label || 'Inactivo';
      break;
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClasses} ${className}`}
    >
      {label}
    </span>
  );
};
