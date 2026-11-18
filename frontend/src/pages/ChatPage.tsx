import React, { useState } from 'react';
import { useActiveVersion } from '../hooks/useActiveVersion';
import { useChat } from '../hooks/useChat';
import { ChatContainer } from '../components/chat/ChatContainer';
import { ChatInput } from '../components/chat/ChatInput';

export const ChatPage: React.FC = () => {
  const {
    activeVersion,
    hasActiveVersion,
    versionChangedWarning,
    dismissWarning,
  } = useActiveVersion();

  const { messages, isLoading, sendMessage } = useChat();
  const [selectedPrompt, setSelectedPrompt] = useState<string>('');

  const handleSelectPrompt = (prompt: string) => {
    setSelectedPrompt(prompt);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-slate-50">
      <ChatContainer
        messages={messages}
        isLoading={isLoading}
        activeVersion={activeVersion}
        onSelectPrompt={handleSelectPrompt}
        versionChangedWarning={versionChangedWarning}
        onDismissVersionWarning={dismissWarning}
      />
      <ChatInput
        onSendMessage={sendMessage}
        isLoading={isLoading}
        hasActiveVersion={hasActiveVersion}
        activeVersionName={activeVersion?.nombre}
        initialValue={selectedPrompt}
        onClearInitialValue={() => setSelectedPrompt('')}
      />
    </div>
  );
};
