import { useState, useCallback } from 'react';
import { ChatMessageItem } from '../types';
import { queryNormativa } from '../api/query';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [currentError, setCurrentError] = useState<string | null>(null);

  const sendMessage = useCallback(async (queryText: string) => {
    const clean = queryText.trim();
    if (!clean || isLoading) return;

    const userMessageId = `user_${Date.now()}`;
    const userMessage: ChatMessageItem = {
      id: userMessageId,
      sender: 'user',
      text: clean,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setCurrentError(null);

    try {
      const response = await queryNormativa(clean);

      const assistantMessage: ChatMessageItem = {
        id: `asst_${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        timestamp: new Date().toISOString(),
        version_id: response.version_id,
        document_name: response.document_name,
        citations: response.citations,
        abstained: response.abstained,
        abstention_reason: response.abstention_reason,
        disclaimer: response.disclaimer,
        latency_ms: response.latency_ms,
        response_type: response.response_type,
        clarification_needed: response.clarification_needed,
        clarification_question: response.clarification_question,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessageText =
        err.message || 'No fue posible obtener respuesta del motor RAG.';
      setCurrentError(errorMessageText);

      const errorMessage: ChatMessageItem = {
        id: `err_${Date.now()}`,
        sender: 'assistant',
        text: errorMessageText,
        timestamp: new Date().toISOString(),
        error: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setCurrentError(null);
  }, []);

  return {
    messages,
    isLoading,
    currentError,
    sendMessage,
    clearChat,
  };
}
