import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { VoiceChat } from './components/VoiceChat/index.tsx';

const authComponents = {
  Header() {
    return (
      <div className="text-center py-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Voice Agent
        </h1>
        <p className="text-sm text-gray-500 mt-1">
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
    <div className="h-screen flex flex-col bg-white">
      <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 md:py-4">
        <div className="max-w-3xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-lg md:text-2xl font-bold text-gray-900">いっぱい喋れるNovaちゃん🐰</h1>
            <p className="text-xs md:text-sm text-gray-400">AgentCore + Strands + Amplifyで構築！</p>
          </div>
          <button
            onClick={signOut}
            className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 px-3 py-1 rounded-lg transition-colors text-xs"
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
