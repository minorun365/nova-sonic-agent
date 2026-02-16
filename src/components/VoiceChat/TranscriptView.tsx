import { useRef, useEffect } from 'react';
import type { TranscriptEntry } from './types.ts';

interface TranscriptViewProps {
  entries: TranscriptEntry[];
  activeTool: string | null;
}

export function TranscriptView({ entries, activeTool }: TranscriptViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [entries, activeTool]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {entries.length === 0 && !activeTool && (
        <p className="text-center text-gray-300 mt-16">
          マイクボタンを押して話しかけてください
        </p>
      )}

      {entries.map((entry, i) => (
        <div
          key={i}
          className={`flex ${entry.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`
              max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed
              ${entry.role === 'user'
                ? 'bg-blue-500 text-white rounded-br-md'
                : 'bg-gray-100 text-gray-800 rounded-bl-md'
              }
              ${!entry.isFinal ? 'opacity-60' : ''}
            `}
          >
            {entry.text}
          </div>
        </div>
      ))}

      {activeTool && (
        <div className="flex justify-start">
          <div className="bg-gray-50 text-gray-500 border border-gray-200 px-4 py-2.5 rounded-2xl text-sm animate-pulse">
            {activeTool} を実行中...
          </div>
        </div>
      )}
    </div>
  );
}
