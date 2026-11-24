import React, { useState, useRef, useEffect } from 'react';
import { Send, CornerDownLeft, AlertCircle } from 'lucide-react';
import { Button } from '../ui/Button';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  hasActiveVersion: boolean;
  activeVersionName?: string;
  initialValue?: string;
  onClearInitialValue?: () => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading,
  hasActiveVersion,
  activeVersionName,
  initialValue = '',
  onClearInitialValue,
}) => {
  const [text, setText] = useState(initialValue);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (initialValue) {
      setText(initialValue);
      if (onClearInitialValue) {
        onClearInitialValue();
      }
      textareaRef.current?.focus();
    }
  }, [initialValue, onClearInitialValue]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const clean = text.trim();
    if (!clean || isLoading || !hasActiveVersion) return;
    onSendMessage(clean);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    // Auto resize height
    const target = e.target;
    target.style.height = 'auto';
    target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
  };

  return (
    <div className="bg-white border-t border-slate-200 p-3 sm:p-4 shadow-lg sticky bottom-0 z-20">
      <div className="max-w-4xl mx-auto">
        {!hasActiveVersion ? (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs sm:text-sm flex items-center gap-2 mb-2">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              Consultas deshabilitadas: no hay un reglamento activo en este momento.
            </span>
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="relative flex items-end gap-2 bg-slate-50 border border-slate-300 rounded-xl p-1.5 focus-within:ring-2 focus-within:ring-uts-green-600 focus-within:border-uts-green-600 focus-within:bg-white transition-all shadow-inner">
          <textarea
            ref={textareaRef}
            rows={1}
            disabled={!hasActiveVersion || isLoading}
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={
              hasActiveVersion
                ? `Pregunte sobre el reglamento (${activeVersionName || 'activo'})...`
                : 'Active un reglamento para consultar...'
            }
            className="flex-1 bg-transparent border-0 resize-none py-2 px-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-0 max-h-40 min-h-[42px] leading-relaxed disabled:opacity-50"
            aria-label="Campo de pregunta sobre el reglamento"
          />

          <div className="flex items-center gap-1 shrink-0 pb-1 pr-1">
            <Button
              type="submit"
              disabled={!text.trim() || isLoading || !hasActiveVersion}
              isLoading={isLoading}
              size="sm"
              className="rounded-lg h-9 w-9 p-0 flex items-center justify-center"
              aria-label="Enviar pregunta"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </form>

        <div className="flex items-center text-[11px] text-slate-400 mt-2 px-1">
          <div className="flex items-center gap-1 hidden sm:flex">
            <CornerDownLeft className="w-3 h-3 text-slate-400" />
            <span>Presione <strong>Enter</strong> para enviar, <strong>Shift + Enter</strong> para salto de línea</span>
          </div>
        </div>
      </div>
    </div>
  );
};
