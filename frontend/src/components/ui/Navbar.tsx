import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpen, AlertCircle, Menu, X, Settings, MessageSquare } from 'lucide-react';
import { NormativeVersion } from '../../types';

interface NavbarProps {
  activeVersion: NormativeVersion | null;
  isLoadingVersion?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ activeVersion, isLoadingVersion }) => {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isChatActive = location.pathname === '/';
  const isAdminActive = location.pathname.startsWith('/admin');

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Logo y Nombre Institucional */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-lg bg-uts-green-700 text-white flex items-center justify-center shadow-sm group-hover:bg-uts-green-800 transition-colors">
              <BookOpen className="w-5 h-5 text-uts-gold-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 tracking-tight text-lg">
                  NORMATIVA-TG <span className="text-uts-green-700">UTS</span>
                </span>
                <span className="hidden sm:inline-block text-[10px] font-semibold uppercase tracking-wider bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200">
                  Prototipo F-DC-124
                </span>
              </div>
              <p className="text-xs text-slate-500 font-normal">
                Asistente inteligente para Trabajo de Grado
              </p>
            </div>
          </Link>

          {/* Indicador de Versión Activa en Desktop */}
          <div className="hidden md:flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs border transition-colors bg-slate-50 border-slate-200">
              {isLoadingVersion ? (
                <div className="flex items-center gap-2 text-slate-400">
                  <div className="w-2 h-2 rounded-full bg-slate-300 animate-ping" />
                  <span>Consultando normativa activa...</span>
                </div>
              ) : activeVersion ? (
                <div className="flex items-center gap-2 text-slate-700">
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="font-medium text-slate-900">
                    {activeVersion.nombre}
                  </span>
                  {activeVersion.anio && (
                    <span className="text-slate-400 font-mono">({activeVersion.anio})</span>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2 text-amber-700">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                  <span className="font-medium">Sin reglamento activo</span>
                </div>
              )}
            </div>

            {/* Navegación Desktop */}
            <nav className="flex items-center gap-1 border-l border-slate-200 pl-4">
              <Link
                to="/"
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isChatActive
                    ? 'bg-uts-green-50 text-uts-green-800 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Chat Normativo</span>
              </Link>
              <Link
                to="/admin"
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isAdminActive
                    ? 'bg-uts-green-50 text-uts-green-800 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Settings className="w-4 h-4" />
                <span>Administración</span>
              </Link>
            </nav>
          </div>

          {/* Botón Menú Móvil */}
          <div className="flex md:hidden items-center gap-2">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              aria-label="Abrir menú"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Menú Móvil Desplegable */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-4 space-y-3">
          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
            <div className="font-medium text-slate-500 mb-1">Reglamento activo:</div>
            {activeVersion ? (
              <div className="flex items-center gap-2 text-slate-900 font-medium">
                <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block" />
                <span>{activeVersion.nombre} ({activeVersion.anio})</span>
              </div>
            ) : (
              <div className="text-amber-700 flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5 text-amber-500" />
                <span>Sin normativa activa</span>
              </div>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <Link
              to="/"
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
                isChatActive
                  ? 'bg-uts-green-50 text-uts-green-800 font-semibold'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              <span>Chat Normativo</span>
            </Link>
            <Link
              to="/admin"
              onClick={() => setMobileMenuOpen(false)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${
                isAdminActive
                  ? 'bg-uts-green-50 text-uts-green-800 font-semibold'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Administración</span>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
};
