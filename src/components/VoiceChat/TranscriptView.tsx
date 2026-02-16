import { useRef, useEffect } from 'react';
import type { TranscriptEntry } from './types.ts';

interface TranscriptViewProps {
  entries: TranscriptEntry[];
  isAssistantSpeaking: boolean;
  activeTool: string | null;
}

export function TranscriptView({ entries, isAssistantSpeaking, activeTool }: TranscriptViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [entries, isAssistantSpeaking, activeTool]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {entries.length === 0 && !isAssistantSpeaking && !activeTool && (
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

      {/* アシスタント話し中インジケーター */}
      {isAssistantSpeaking && (
        <div className="flex justify-start">
          <div className="px-4 py-3 rounded-2xl rounded-bl-md bg-gray-100 flex items-center gap-1">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      )}

      {activeTool && (
        <div className="flex justify-start">
          <div className="bg-gray-50 text-gray-500 border border-gray-200 px-4 py-2.5 rounded-2xl text-sm animate-pulse">
            {activeTool}ツールを利用中…
          </div>
        </div>
      )}
    </div>
  );
}
