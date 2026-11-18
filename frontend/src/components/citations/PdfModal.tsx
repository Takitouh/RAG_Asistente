import React from 'react';
import { ExternalLink, FileText, Download } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { getVersionPdfUrl } from '../../api/query';

interface PdfModalProps {
  isOpen: boolean;
  onClose: () => void;
  versionId: string;
  documentName: string;
  page?: number;
  locationHint?: string;
}

export const PdfModal: React.FC<PdfModalProps> = ({
  isOpen,
  onClose,
  versionId,
  documentName,
  page,
  locationHint,
}) => {
  const pdfUrl = getVersionPdfUrl(versionId, page);
  const rawPdfUrl = getVersionPdfUrl(versionId);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Visor Documental — ${documentName}`}
      subtitle={locationHint ? `Ubicación: ${locationHint} (Página ${page ?? 1})` : `Página ${page ?? 1}`}
      maxWidth="5xl"
    >
      <div className="flex flex-col h-[70vh]">
        {/* Barra superior de controles */}
        <div className="flex items-center justify-between bg-slate-100 px-4 py-2 rounded-t-lg border border-b-0 border-slate-200 text-xs text-slate-600">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-uts-green-700" />
            <span className="font-medium text-slate-800 truncate max-w-md">
              {documentName}
            </span>
            {page && (
              <span className="bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700 font-semibold">
                Pág. {page}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <a
              href={pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-slate-50 text-slate-700 rounded border border-slate-300 font-medium transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Abrir en pestaña nueva</span>
            </a>
            <a
              href={rawPdfUrl}
              download={documentName}
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-uts-green-700 hover:bg-uts-green-800 text-white rounded font-medium transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Descargar</span>
            </a>
          </div>
        </div>

        {/* Contenedor del PDF Iframe */}
        <div className="flex-1 w-full bg-slate-200 border border-slate-300 rounded-b-lg overflow-hidden">
          <iframe
            src={pdfUrl}
            title={`Documento ${documentName}`}
            className="w-full h-full border-0"
          />
        </div>
      </div>
    </Modal>
  );
};
