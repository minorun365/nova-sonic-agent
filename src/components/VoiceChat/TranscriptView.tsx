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
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      {entries.length === 0 && !activeTool && (
        <p className="text-center text-gray-400 mt-8">
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
              max-w-[80%] px-4 py-2 rounded-2xl text-sm
              ${entry.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-md'
                : 'bg-white text-gray-800 shadow-sm border rounded-bl-md'
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
          <div className="bg-amber-50 text-amber-700 border border-amber-200 px-4 py-2 rounded-2xl text-sm animate-pulse">
            {activeTool} を実行中...
          </div>
        </div>
      )}
    </div>
  );
}
