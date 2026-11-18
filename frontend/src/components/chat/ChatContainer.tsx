import React, { useRef, useEffect } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import { ChatMessageItem, NormativeVersion } from '../../types';
import { ChatMessage } from './ChatMessage';
import { WelcomeBanner } from './WelcomeBanner';

interface ChatContainerProps {
  messages: ChatMessageItem[];
  isLoading: boolean;
  activeVersion: NormativeVersion | null;
  onSelectPrompt: (prompt: string) => void;
  versionChangedWarning?: string | null;
  onDismissVersionWarning?: () => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  isLoading,
  activeVersion,
  onSelectPrompt,
  versionChangedWarning,
  onDismissVersionWarning,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof bottomRef.current?.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* Advertencia si la versión normativa cambió durante la sesión */}
        {versionChangedWarning && (
          <div className="bg-blue-50 border border-blue-200 text-blue-900 rounded-xl p-3.5 flex items-center justify-between text-xs sm:text-sm shadow-xs animate-fadeIn">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-blue-600 shrink-0" />
              <span>{versionChangedWarning}</span>
            </div>
            {onDismissVersionWarning && (
              <button
                onClick={onDismissVersionWarning}
                className="text-xs text-blue-700 hover:text-blue-900 font-semibold underline ml-2"
              >
                Entendido
              </button>
            )}
          </div>
        )}

        {/* Estado inicial / Bienvenida */}
        {messages.length === 0 ? (
          <WelcomeBanner
            activeVersion={activeVersion}
            onSelectPrompt={onSelectPrompt}
          />
        ) : (
          messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
        )}

        {/* Indicador de carga mientras el LLM genera */}
        {isLoading && (
          <div className="flex justify-start my-4">
            <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-2xl rounded-tl-xs px-4 py-3 shadow-xs">
              <Loader2 className="w-5 h-5 text-uts-green-700 animate-spin" />
              <span className="text-xs text-slate-600 font-medium">
                Consultando normativa oficial y estructurando respuesta...
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};
