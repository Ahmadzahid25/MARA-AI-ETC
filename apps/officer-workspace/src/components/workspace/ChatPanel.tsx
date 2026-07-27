import { useRef, useEffect, useState } from 'react';
import { Icon, Scrollable, Typography } from '@openhands/ui';
import type { ChatMessage } from '../../types/workspace';
import { UI, WORKSPACE } from '../../constants';

interface ChatPanelProps {
  onSend?: (text: string) => Promise<string | void> | void;
  uploading?: boolean;
  onFileAttach?: () => void;
}

export function ChatPanel({ onSend, uploading, onFileAttach }: ChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const [inputValue, setInputValue] = useState('');

  async function handleSend() {
    if (!inputValue.trim() || uploading) return;

    const text = inputValue;
    setInputValue('');

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    const response = await onSend?.(text);
    if (response) {
      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now()}-resp`,
        role: 'assistant',
        content: response,
        timestamp: new Date().toISOString(),
        agent_name: 'Planner Agent',
      };
      setMessages((prev) => [...prev, assistantMsg]);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center border-b border-slate-200 bg-white/50 dark:border-[#222328] dark:bg-[#131417]/50 backdrop-blur-sm px-6 py-3.5 shadow-sm">
        <Typography.H3 className="font-bold text-slate-900 dark:text-white">{WORKSPACE.CHAT_HEADING}</Typography.H3>
      </div>

      <Scrollable className="flex-1 px-6 py-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </Scrollable>

      <div className="px-6 pb-6 pt-2">
        <div className="mx-auto max-w-3xl w-full">
          <div className="flex items-center w-full rounded-full bg-white dark:bg-[#18191C] border border-gray-200 dark:border-gray-800 shadow-sm px-4 py-3 h-[58px] focus-within:border-indigo-500 focus-within:shadow-md transition-all">
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                title={WORKSPACE.FILE_ATTACH_TITLE}
                onClick={onFileAttach}
                className="w-9 h-9 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-all cursor-pointer shrink-0"
              >
                <Icon icon="Plus" className="w-5 h-5" />
              </button>
              <button
                type="button"
                title={WORKSPACE.VOICE_INPUT_TITLE}
                className="w-9 h-9 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-all cursor-pointer shrink-0"
              >
                <Icon icon="Mic" className="w-5 h-5" />
              </button>
            </div>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={WORKSPACE.CHAT_PLACEHOLDER}
              className="flex-1 min-w-0 bg-transparent border-0 outline-none focus:outline-none focus:ring-0 text-slate-900 dark:text-slate-100 text-sm font-normal placeholder:text-gray-400 dark:placeholder:text-gray-500 px-3"
              onKeyDown={handleKeyDown}
            />
            <button
              type="button"
                title={WORKSPACE.SEND_MESSAGE_TITLE}
              onClick={handleSend}
              disabled={uploading}
              className="w-[42px] h-[42px] rounded-full text-white flex items-center justify-center shrink-0 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow transition-all ml-1"
              style={{ backgroundColor: UI.BRAND_ORANGE }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = UI.BRAND_ORANGE_HOVER)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = UI.BRAND_ORANGE)}
            >
              <Icon icon="ArrowUp" className="w-5 h-5 text-white stroke-[2]" />
            </button>
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
          {new Date(message.timestamp).toLocaleTimeString(UI.LOCALE, UI.DATE_FORMAT_OPTIONS)}
        </p>
      </div>
    </div>
  );
}
