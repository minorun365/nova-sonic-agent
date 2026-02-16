interface MicButtonProps {
  isRecording: boolean;
  isConnected: boolean;
  onToggle: () => void;
}

export function MicButton({ isRecording, isConnected, onToggle }: MicButtonProps) {
  return (
    <div className="relative">
      {/* パルスリング（録音中） */}
      {isRecording && (
        <div className="absolute inset-0 rounded-full bg-red-400 animate-pulse-ring" />
      )}
      <button
        onClick={onToggle}
        disabled={!isConnected}
        className={`
          relative w-20 h-20 rounded-full flex items-center justify-center
          text-white text-3xl shadow-lg transition-all
          ${isRecording
            ? 'bg-red-500 hover:bg-red-600 scale-110'
            : isConnected
              ? 'bg-indigo-600 hover:bg-indigo-700'
              : 'bg-gray-400 cursor-not-allowed'
          }
        `}
        aria-label={isRecording ? 'マイクをオフにする' : 'マイクをオンにする'}
      >
        {isRecording ? (
          // Stop icon
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
            <path fillRule="evenodd" d="M4.5 7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-9a3 3 0 0 1-3-3v-9Z" clipRule="evenodd" />
          </svg>
        ) : (
          // Mic icon
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
            <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
            <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
          </svg>
        )}
      </button>
    </div>
  );
}
