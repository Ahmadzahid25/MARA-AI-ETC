import { useRef, useEffect } from 'react';
import { Button, Input, Scrollable, Typography } from '@openhands/ui';
import type { ChatMessage } from '../../types/workspace';
import { MOCK_MESSAGES } from '../../mocks/mock-data';

export function ChatPanel() {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [MOCK_MESSAGES.length]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center border-b bg-white px-6 py-3">
        <Typography.H3>Workspace</Typography.H3>
      </div>

      <Scrollable className="flex-1 px-6 py-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {MOCK_MESSAGES.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </Scrollable>

      <div className="border-t bg-white px-6 py-4">
        <div className="mx-auto flex max-w-3xl gap-3">
          <Input
            label=""
            placeholder="Describe your task — e.g. Assess the loan application from Ahmad bin Abdullah"
            className="flex-1"
            onKeyDown={handleKeyDown}
          />
          <Button variant="primary">Send</Button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        {!isUser && message.agent_name && (
          <p className="mb-1 text-xs font-medium text-gray-500">
            {message.agent_name}
          </p>
        )}
        <Typography.Text
          fontSize="s"
          className={`whitespace-pre-wrap ${isUser ? 'text-white' : 'text-gray-900'}`}
        >
          {message.content}
        </Typography.Text>
        <p
          className={`mt-1 text-xs ${
            isUser ? 'text-blue-200' : 'text-gray-400'
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString('en-MY', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  );
}
