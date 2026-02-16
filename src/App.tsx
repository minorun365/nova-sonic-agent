import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { VoiceChat } from './components/VoiceChat/index.tsx';

const authComponents = {
  Header() {
    return (
      <div className="text-center py-4">
        <h1 className="text-2xl font-bold text-white">
          Voice Agent
        </h1>
        <p className="text-sm text-white/80 mt-1">
          Nova Sonic 音声対話エージェント
        </p>
      </div>
    );
  },
};

function App() {
  return (
    <Authenticator components={authComponents}>
      {({ signOut }) => <MainApp signOut={signOut} />}
    </Authenticator>
  );
}

function MainApp({ signOut }: { signOut?: () => void }) {
  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <header className="bg-gradient-to-r from-indigo-900 to-blue-500 text-white px-4 md:px-6 py-3 md:py-4 shadow-md">
        <div className="max-w-3xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-lg md:text-2xl font-bold">Voice Agent</h1>
            <p className="text-xs md:text-sm text-white/50">Nova Sonic + AgentCore</p>
          </div>
          <button
            onClick={signOut}
            className="bg-white/20 text-white px-3 py-1 rounded hover:bg-white/30 transition-colors text-xs"
          >
            ログアウト
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-hidden">
        <VoiceChat />
      </main>
    </div>
  );
}

export default App;
