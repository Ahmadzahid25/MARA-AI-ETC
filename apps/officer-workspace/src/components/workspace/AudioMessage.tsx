import { useRef, useState } from 'react';
import { Typography } from '@openhands/ui';
import type { ChatMessage } from '../../types/workspace';

interface AudioMessageProps {
  message: ChatMessage;
}

export function AudioMessage({ message }: AudioMessageProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);

  function togglePlay() {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setPlaying(!playing);
  }

  return (
    <div className="flex items-center gap-3 rounded-lg bg-slate-50 p-3 dark:bg-[#222328]">
      <button
        type="button"
        onClick={togglePlay}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white hover:bg-indigo-700 transition-colors cursor-pointer"
      >
        {playing ? (
          <svg className="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
            <rect x="3" y="2" width="4" height="12" rx="1" />
            <rect x="9" y="2" width="4" height="12" rx="1" />
          </svg>
        ) : (
          <svg className="ml-0.5 h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
            <path d="M4 2 L14 8 L4 14 Z" />
          </svg>
        )}
      </button>
      <div className="min-w-0 flex-1">
        <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
          <div className="h-full w-0 rounded-full bg-indigo-500" />
        </div>
      </div>
      <Typography.Text fontSize="xs" className="shrink-0 text-slate-400 dark:text-slate-500">
        {message.audio_duration ? `${message.audio_duration}s` : 'audio'}
      </Typography.Text>
      <audio
        ref={audioRef}
        src={message.audio_url}
        onEnded={() => setPlaying(false)}
        className="hidden"
      />
    </div>
  );
}
