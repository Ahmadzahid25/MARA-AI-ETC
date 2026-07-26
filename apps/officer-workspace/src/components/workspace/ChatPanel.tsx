import { useRef, useEffect } from 'react';
import { Button, Icon, Input, Scrollable, Typography } from '@openhands/ui';
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
      <div className="flex items-center border-b border-slate-200 bg-white/50 dark:border-[#222328] dark:bg-[#131417]/50 backdrop-blur-sm px-6 py-3.5 shadow-sm">
        <Typography.H3 className="font-bold text-slate-900 dark:text-white">Workspace</Typography.H3>
      </div>

      <Scrollable className="flex-1 px-6 py-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {MOCK_MESSAGES.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </Scrollable>

      <div className="px-6 pb-6 pt-2">
        {/*
         * NOTE / SYSTEM GAP:
         * @openhands/ui currently does not export a dedicated "ChatInput" or "SearchBar" component,
         * nor does <Input /> support a pill-shaped (rounded-full) variant or interactive trailing button slots.
         * Per application convention, we note this design system gap here and compose the required pill-shaped chat bar
         * layout using the existing <Input /> and <Button /> primitives wrapped in a shared container.
         */}
        <div className="mx-auto max-w-3xl">
          <div className="chat-input-pill flex items-center rounded-full border border-slate-200 bg-white dark:border-[#2C2E34] dark:bg-[#18191C] px-3 py-1.5 focus-within:border-indigo-500 transition-all shadow-md dark:shadow-lg">
            <div className="flex items-center gap-2.5 pl-2 text-slate-400 dark:text-light-neutral-400">
              <button type="button" title="Attach file" className="hover:text-slate-700 dark:hover:text-light-neutral-200 transition-colors cursor-pointer flex items-center justify-center">
                <Icon icon="Plus" className="h-5 w-5" />
              </button>
              <button type="button" title="Voice input" className="hover:text-slate-700 dark:hover:text-light-neutral-200 transition-colors cursor-pointer flex items-center justify-center">
                <Icon icon="Mic" className="h-5 w-5" />
              </button>
            </div>
            <Input
              label=""
              placeholder="Describe your task — e.g. Assess the loan application from Ahmad bin Abdullah"
              className="flex-1"
              onKeyDown={handleKeyDown}
            />
            <Button
              variant="primary"
              className="!min-w-0 !w-10 !h-10 !p-0 !rounded-full !bg-red-600 hover:!bg-red-700 !border-red-600 dark:!bg-red-600 dark:hover:!bg-red-500 !text-white flex items-center justify-center shrink-0 cursor-pointer shadow-sm transition-all"
              title="Send message"
            >
              <Icon icon="ArrowUp" className="h-5 w-5 !text-white stroke-[1]" />
            </Button>
          </div>
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
        className={`max-w-[80%] rounded-xl px-4 py-3 shadow-sm ${
          isUser
            ? 'bg-indigo-600 text-white'
            : 'bg-white border border-slate-200 text-slate-800 dark:bg-[#18191C] dark:border-[#2C2E34] dark:text-slate-200'
        }`}
      >
        {!isUser && message.agent_name && (
          <p className="mb-1 text-xs font-semibold text-indigo-600 dark:text-indigo-400">
            {message.agent_name}
          </p>
        )}
        <Typography.Text
          fontSize="s"
          className={`whitespace-pre-wrap ${isUser ? 'text-white' : 'text-slate-800 dark:text-slate-200'}`}
        >
          {message.content}
        </Typography.Text>
        <p
          className={`mt-1.5 text-xs ${
            isUser ? 'text-indigo-200' : 'text-slate-400 dark:text-slate-500'
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
