import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Bookmark, ExternalLink } from 'lucide-react';
import { Citation } from '../../types';
import { PdfModal } from './PdfModal';

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export const CitationCard: React.FC<CitationCardProps> = ({ citation, index }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isPdfModalOpen, setIsPdfModalOpen] = useState(false);

  // Formato legible de ubicación
  const buildLocationSummary = () => {
    const parts: string[] = [];
    if (citation.capitulo_romano || citation.capitulo_numero) {
      parts.push(`Capítulo ${citation.capitulo_romano || citation.capitulo_numero}`);
    }
    if (citation.articulo_numero) {
      parts.push(`Art. ${citation.articulo_numero}`);
    }
    if (citation.paragrafo_numero) {
      parts.push(`Parágrafo ${citation.paragrafo_numero}`);
    }
    if (citation.inciso_marker) {
      parts.push(`Inciso ${citation.inciso_marker}`);
    }
    return parts.length > 0 ? parts.join(' • ') : citation.location_hint || 'Referencia normativa';
  };

  return (
    <>
      <div className="border border-slate-200 rounded-lg bg-white overflow-hidden shadow-xs hover:border-slate-300 transition-all">
        {/* Cabecera de la Cita */}
        <div
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center justify-between p-3 cursor-pointer bg-slate-50/70 hover:bg-slate-100/70 transition-colors select-none"
        >
          <div className="flex items-center gap-2.5 min-w-0 pr-2">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-uts-green-100 text-uts-green-800 text-xs font-bold shrink-0">
              {index + 1}
            </span>
            <div className="truncate">
              <span className="font-semibold text-slate-800 text-xs sm:text-sm">
                {buildLocationSummary()}
              </span>
              <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5 truncate">
                <span className="font-medium text-slate-600">{citation.document_name}</span>
                <span>•</span>
                <span className="bg-slate-200/80 text-slate-700 px-1.5 py-0.2 rounded font-mono">
                  Pág. {citation.page_start}
                </span>
                <span>•</span>
                <span className="text-slate-400 font-mono">v:{citation.version_id}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsPdfModalOpen(true);
              }}
              title="Abrir página en PDF original"
              className="p-1 rounded text-slate-500 hover:text-uts-green-700 hover:bg-slate-200 transition-colors inline-flex items-center gap-1 text-xs px-2"
            >
              <FileText className="w-3.5 h-3.5 text-uts-green-700" />
              <span className="hidden sm:inline">Ver PDF</span>
            </button>
            <button
              type="button"
              className="p-1 text-slate-400 hover:text-slate-600"
              aria-label={isExpanded ? 'Contraer cita' : 'Expandir cita'}
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Cuerpo expandible con el texto normativo exacto */}
        {isExpanded && (
          <div className="p-3.5 bg-white border-t border-slate-100 text-xs space-y-2.5">
            <div className="flex items-center gap-1.5 text-uts-green-800 font-semibold text-[11px] uppercase tracking-wider">
              <Bookmark className="w-3.5 h-3.5" />
              <span>Texto Normativo Verificado (Evidencia del Chunk):</span>
            </div>
            <blockquote className="p-3 rounded-md bg-slate-50 border-l-3 border-uts-green-600 text-slate-700 font-serif leading-relaxed italic whitespace-pre-line">
              "{citation.texto_fragmento}"
            </blockquote>

            <div className="flex items-center justify-between pt-1 text-[11px] text-slate-400">
              <span className="font-mono">Referencia documental verificada</span>
              <button
                type="button"
                onClick={() => setIsPdfModalOpen(true)}
                className="text-uts-green-700 hover:underline font-medium inline-flex items-center gap-1"
              >
                <span>Localizar en el documento oficial (Página {citation.page_start})</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal de PDF */}
      <PdfModal
        isOpen={isPdfModalOpen}
        onClose={() => setIsPdfModalOpen(false)}
        versionId={citation.version_id}
        documentName={citation.document_name}
        page={citation.page_start}
        locationHint={citation.location_hint}
      />
    </>
  );
};
