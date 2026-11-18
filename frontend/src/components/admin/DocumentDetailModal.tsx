import React, { useState, useEffect } from 'react';
import {
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
  ShieldAlert,
  Loader2,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { NormativeVersion, VersionReportResponse } from '../../types';
import { getAdminVersionReport, reviewVersion } from '../../api/admin';
import { PdfModal } from '../citations/PdfModal';

interface DocumentDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  version: NormativeVersion | null;
  onVersionUpdated: () => void;
}

export const DocumentDetailModal: React.FC<DocumentDetailModalProps> = ({
  isOpen,
  onClose,
  version,
  onVersionUpdated,
}) => {
  const [reportData, setReportData] = useState<VersionReportResponse | null>(null);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [isPdfModalOpen, setIsPdfModalOpen] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; error?: boolean } | null>(null);

  useEffect(() => {
    if (isOpen && version) {
      setIsLoadingReport(true);
      setFeedbackMsg(null);
      setReviewNotes('');
      getAdminVersionReport(version.id)
        .then((res) => {
          setReportData(res);
          setIsLoadingReport(false);
        })
        .catch(() => {
          setReportData(null);
          setIsLoadingReport(false);
        });
    }
  }, [isOpen, version]);

  if (!version) return null;

  const handleReviewAction = async (action: 'approve' | 'reject') => {
    setIsSubmittingReview(true);
    setFeedbackMsg(null);
    try {
      const res = await reviewVersion(version.id, action, reviewNotes);
      setFeedbackMsg({ text: res.message });
      setIsSubmittingReview(false);
      onVersionUpdated();
    } catch (err: any) {
      setIsSubmittingReview(false);
      setFeedbackMsg({ text: err.message || 'Error al registrar la revisión.', error: true });
    }
  };

  const report = reportData?.report;

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        title={`Detalle y Auditoría Documental: ${version.nombre}`}
        subtitle={`ID: ${version.id} • Estado actual: ${version.status}`}
        maxWidth="4xl"
      >
        <div className="space-y-6">
          {feedbackMsg && (
            <div
              className={`p-3 rounded-lg text-xs flex items-center gap-2 border ${
                feedbackMsg.error
                  ? 'bg-rose-50 border-rose-200 text-rose-800'
                  : 'bg-emerald-50 border-emerald-200 text-emerald-800'
              }`}
            >
              {feedbackMsg.error ? (
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
              ) : (
                <CheckCircle className="w-4 h-4 shrink-0 text-emerald-600" />
              )}
              <span>{feedbackMsg.text}</span>
            </div>
          )}

          {/* Resumen Superior de Metadatos */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs">
            <div>
              <span className="text-slate-400 block font-medium">Año y Acuerdo</span>
              <span className="font-semibold text-slate-800">
                {version.anio || 'N/A'} {version.numero_acuerdo ? `(${version.numero_acuerdo})` : ''}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Vigencia</span>
              <span className="font-semibold text-slate-800">{version.estado_vigencia || 'Sin definir'}</span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Chunks Indexados</span>
              <span className="font-semibold text-slate-800">{version.chunks_count} chunks</span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium">Estado</span>
              <div className="mt-0.5">
                <Badge status={version.status} />
              </div>
            </div>
          </div>

          {/* Mensaje de estado del backend */}
          {version.status_message && (
            <div className="p-3 bg-slate-100 rounded-lg text-xs text-slate-700 flex items-start gap-2">
              <Clock className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
              <div>
                <strong>Mensaje del procesador:</strong> {version.status_message}
              </div>
            </div>
          )}

          {/* Acción para abrir el PDF original */}
          <div className="flex items-center justify-between p-3.5 bg-uts-green-50/60 border border-uts-green-200 rounded-xl">
            <div className="flex items-center gap-2.5">
              <FileText className="w-5 h-5 text-uts-green-700" />
              <div>
                <h4 className="text-xs sm:text-sm font-semibold text-uts-green-950">
                  Documento PDF Original en Repositorio
                </h4>
                <p className="text-[11px] text-uts-green-800">
                  Permite contrastar los artículos y numeración extraídos con el facsímil institucional.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsPdfModalOpen(true)}
              leftIcon={<ExternalLink className="w-3.5 h-3.5" />}
            >
              Inspeccionar PDF
            </Button>
          </div>

          {/* Informe de Extracción y OCR */}
          <div>
            <h4 className="text-sm font-bold text-slate-800 mb-2 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-slate-600" />
              <span>Informe de Calidad de Ingestión y OCR</span>
            </h4>

            {isLoadingReport ? (
              <div className="p-6 text-center text-slate-400 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs">Cargando reporte de procesamiento...</span>
              </div>
            ) : report ? (
              <div className="space-y-4">
                {/* Métricas de extracción */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-white border border-slate-200 rounded-lg text-xs">
                    <span className="text-slate-400 block">Páginas Procesadas</span>
                    <span className="text-lg font-bold text-slate-800">{report.num_pages}</span>
                  </div>

                  <div className="p-3 bg-white border border-slate-200 rounded-lg text-xs">
                    <span className="text-slate-400 block">Métodos de Extracción</span>
                    <span className="font-semibold text-slate-700">
                      Texto: {report.extraction_methods?.text_layer || 0} • OCR: {report.extraction_methods?.ocr || 0}
                    </span>
                  </div>

                  <div className="p-3 bg-white border border-slate-200 rounded-lg text-xs">
                    <span className="text-slate-400 block">Confianza OCR Promedio</span>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-lg font-bold text-slate-800">
                        {report.ocr_confidence_mean !== null
                          ? `${report.ocr_confidence_mean.toFixed(1)}%`
                          : 'Capa vectorial'}
                      </span>
                      {report.ocr_confidence_mean !== null && report.ocr_confidence_mean < 75 && (
                        <span className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded font-semibold">
                          Bajo umbral
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Nota metodológica sobre OCR */}
                <p className="text-[11px] text-slate-400 italic">
                  * Nota técnica: La confianza OCR es un indicador heurístico de legibilidad óptica y no constituye garantía absoluta de exactitud textual según las directrices del proyecto.
                </p>

                {/* Anomalías detectadas */}
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                  <span className="font-semibold text-xs text-slate-700 block">
                    Anomalías Detectadas ({report.anomalies?.length || 0}):
                  </span>
                  {report.anomalies && report.anomalies.length > 0 ? (
                    <ul className="list-disc pl-4 text-xs text-amber-800 space-y-1">
                      {report.anomalies.map((ano, idx) => (
                        <li key={idx}>{ano}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="text-xs text-emerald-700 flex items-center gap-1.5">
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>Estructura secuencial íntegra sin saltos ni anomalías detectadas.</span>
                    </div>
                  )}
                </div>

                {/* Reparaciones automáticas aplicadas */}
                {report.repairs && report.repairs.length > 0 && (
                  <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                    <span className="font-semibold text-xs text-slate-700 block">
                      Reparaciones Estructurales Automáticas ({report.repairs.length}):
                    </span>
                    <ul className="list-disc pl-4 text-xs text-slate-600 space-y-1">
                      {report.repairs.map((rep, idx) => (
                        <li key={idx}>
                          <strong>{rep.tipo}:</strong> {rep.descripcion}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-4 bg-slate-50 rounded-lg text-xs text-slate-500">
                Esta versión aún no tiene un reporte detallado registrado.
              </div>
            )}
          </div>

          {/* Panel de Validación Humana y Aprobación */}
          <div className="pt-4 border-t border-slate-200 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Validación y Aprobación Administrativa
            </h4>
            <p className="text-xs text-slate-500">
              Revise que los capítulos, artículos y fechas correspondan a la normativa oficial antes de habilitar su activación en el chat público.
            </p>

            <textarea
              rows={2}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Notas de revisión humana (opcional, e.g. 'Verificado con el documento oficial firmado')..."
              className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-uts-green-600 focus:outline-none"
            />

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
              <div className="text-[11px] text-slate-400">
                La aprobación cambia el estado a <strong>PROCESADO</strong> y habilita la activación.
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="danger"
                  isLoading={isSubmittingReview}
                  onClick={() => handleReviewAction('reject')}
                  leftIcon={<ThumbsDown className="w-3.5 h-3.5" />}
                >
                  Marcar Error / Rechazar
                </Button>
                <Button
                  size="sm"
                  variant="primary"
                  isLoading={isSubmittingReview}
                  onClick={() => handleReviewAction('approve')}
                  leftIcon={<ThumbsUp className="w-3.5 h-3.5" />}
                >
                  Aprobar Revisión
                </Button>
              </div>
            </div>
          </div>
        </div>
      </Modal>

      {/* Visor de PDF */}
      <PdfModal
        isOpen={isPdfModalOpen}
        onClose={() => setIsPdfModalOpen(false)}
        versionId={version.id}
        documentName={version.nombre}
      />
    </>
  );
};
