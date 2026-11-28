import React, { useState } from 'react';
import { User, Bot, Copy, Check, Clock, AlertTriangle, ShieldCheck, HelpCircle } from 'lucide-react';
import { ChatMessageItem } from '../../types';
import { CitationCard } from '../citations/CitationCard';
import { AbstentionAlert } from './AbstentionAlert';

interface ChatMessageProps {
  message: ChatMessageItem;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === 'user';
  const [copied, setCopied] = useState(false);
  const pendingParts = message.unanswered_parts?.filter(
    (part) => !message.text.toLocaleLowerCase().includes(part.toLocaleLowerCase())
  ) ?? [];

  const handleCopy = () => {
    navigator.clipboard.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end my-4">
        <div className="flex items-start gap-2.5 max-w-xl sm:max-w-2xl">
          <div className="bg-uts-green-700 text-white rounded-2xl rounded-tr-xs px-4 py-3 shadow-xs">
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {message.text}
            </p>
            <div className="text-[10px] text-uts-green-200 mt-1 text-right">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
          <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center shrink-0 mt-0.5">
            <User className="w-4 h-4" />
          </div>
        </div>
      </div>
    );
  }

  // Mensaje de Error Técnico
  if (message.error) {
    return (
      <div className="flex justify-start my-4">
        <div className="flex items-start gap-3 max-w-2xl w-full">
          <div className="w-8 h-8 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center shrink-0 mt-0.5">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <div className="bg-rose-50 border border-rose-200 rounded-2xl rounded-tl-xs p-4 flex-1 shadow-xs text-rose-900">
            <div className="font-semibold text-xs uppercase tracking-wider text-rose-800 mb-1">
              Error Técnico de Comunicación
            </div>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.text}
            </p>
            <div className="text-[10px] text-rose-600 mt-2">
              Compruebe la conectividad con el backend FastAPI o los servicios de soporte (Ollama / Qdrant).
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Mensaje del Asistente (Respuesta Sustentada o Abstención)
  return (
    <div className="flex justify-start my-4">
      <div className="flex items-start gap-3 max-w-3xl w-full">
        {/* Avatar Asistente */}
        <div className="w-8 h-8 rounded-full bg-uts-green-700 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
          <Bot className="w-4 h-4 text-uts-gold-400" />
        </div>

        {/* Tarjeta de Contenido */}
        <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-xs p-4 sm:p-5 flex-1 shadow-xs space-y-4">
          {/* Barra de metadatos de la respuesta */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5 text-xs text-slate-500">
            <div className="flex flex-wrap items-center gap-2">
              {message.version_id ? (
                <span className="inline-flex items-center gap-1 font-medium bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[11px] border border-slate-200">
                  <ShieldCheck className="w-3.5 h-3.5 text-uts-green-700" />
                  <span>Reglamento: {message.document_name || message.version_id}</span>
                </span>
              ) : message.response_type === 'greeting' ? (
                <span className="inline-flex items-center gap-1 font-medium bg-uts-green-50 text-uts-green-800 px-2 py-0.5 rounded text-[11px] border border-uts-green-200">
                  <span>Asistente UTS • Orientación Inicial</span>
                </span>
              ) : (
                <span className="text-slate-400 text-[11px]">Respuesta general</span>
              )}

              {message.clarification_needed && (
                <span className="inline-flex items-center gap-1 font-medium bg-blue-50 text-blue-800 px-2 py-0.5 rounded text-[11px] border border-blue-200">
                  <HelpCircle className="w-3.5 h-3.5 text-blue-600" />
                  <span>Orientación con Aclaración</span>
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 text-[11px] text-slate-400">
              {message.latency_ms !== undefined && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{(message.latency_ms / 1000).toFixed(2)}s</span>
                </span>
              )}
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-800 transition-colors p-1 rounded hover:bg-slate-50"
                title="Copiar respuesta"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copiado' : 'Copiar'}</span>
              </button>
            </div>
          </div>

          {/* Si hubo abstención */}
          {message.abstained ? (
            <AbstentionAlert
              reason={message.abstention_reason}
              messageText={message.text}
              outOfScope={message.response_type === 'out_of_scope'}
            />
          ) : (
            /* Texto generado por el LLM */
            <div className="text-slate-800 text-sm sm:text-base leading-relaxed whitespace-pre-wrap font-sans">
              {message.text}
            </div>
          )}

          {message.response_type === 'partial' && (pendingParts.length > 0 || message.clarification_question) ? (
            <div className="text-sm text-slate-600">
              <p className="font-semibold">Información pendiente</p>
              <ul className="list-disc pl-5">
                {pendingParts.map((part, index) => <li key={index}>{part}</li>)}
              </ul>
              {message.clarification_question && <p>{message.clarification_question}</p>}
            </div>
          ) : null}

          {/* Sección de Citas Normativas Deterministas */}
          {message.citations && message.citations.length > 0 && (
            <div className="pt-2 border-t border-slate-100 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-600 font-semibold uppercase tracking-wider">
                <span>Fundamento Normativo ({message.citations.length} referencias oficiales):</span>
              </div>
              <div className="space-y-2">
                {message.citations.map((citation, idx) => (
                  <CitationCard key={citation.chunk_id || idx} citation={citation} index={idx} />
                ))}
              </div>
            </div>
          )}

          {/* Descargo de Responsabilidad */}
          {message.disclaimer && (
            <div className="pt-2 text-[11px] text-slate-400 border-t border-slate-100 italic">
              {message.disclaimer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
