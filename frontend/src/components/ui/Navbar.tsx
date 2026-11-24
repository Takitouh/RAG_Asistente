import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BookOpen, Menu, X, Settings, MessageSquare } from 'lucide-react';
import { NormativeVersion } from '../../types';

interface NavbarProps {
  activeVersion?: NormativeVersion | null;
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
              </div>
              <p className="text-xs text-slate-500 font-normal">
                Asistente inteligente para Trabajo de Grado
              </p>
            </div>
          </Link>

          {/* Indicador de Versión Activa y Navegación Desktop */}
          <div className="hidden md:flex items-center gap-3">
            {isLoadingVersion ? (
              <span className="text-[11px] text-slate-400">Consultando reglamento...</span>
            ) : activeVersion ? (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs text-slate-600 bg-slate-50 border border-slate-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                <span className="font-medium text-slate-700 truncate max-w-[240px]">
                  {activeVersion.nombre}
                </span>
                {activeVersion.anio && (
                  <span className="text-slate-400 text-[11px]">({activeVersion.anio})</span>
                )}
              </div>
            ) : null}

            <nav className={`flex items-center gap-1 ${activeVersion ? 'border-l border-slate-200 pl-3' : ''}`}>
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
          {activeVersion && (
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
              <span className="font-medium text-slate-700 truncate">{activeVersion.nombre}</span>
              {activeVersion.anio && (
                <span className="text-slate-400 text-[11px]">({activeVersion.anio})</span>
              )}
            </div>
          )}
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
