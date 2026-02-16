# Voice Agent - TODO

## 完了済み（Phase 1: フィジビリティ検証）

- [x] spec.md 作成（技術スタック・アーキテクチャ・フェーズ構成）
- [x] experiment/ に CLI 音声エージェント作成
- [x] Nova Sonic 接続テスト → 英語・日本語ともに動作確認
- [x] knowledge.md に学びを記録

## 完了済み（Phase 1 残り: 追加検証）

- [x] ツール使用テスト: `get_current_time` → 正常に呼び出し / `simple_calculator("3 * 5")` → 正常に呼び出し
- [x] 割り込み（barge-in）テスト: `BidiInterruptionEvent` (reason: user_speech) が発生し、応答が中断される
- [x] レイテンシ計測: 発話終了→最初の音声レスポンスまで平均 **2.5秒**（ツールなし）/ **5秒**（ツール使用時）

## 完了済み（Phase 2: コード実装）

- [x] Amplify Gen2 プロジェクト初期化（package.json, tsconfig, vite.config.ts）
- [x] Cognito 認証設定（`amplify/auth/resource.ts`）
- [x] CDK インフラ定義（`amplify/agent/resource.ts`, `amplify/backend.ts`）
- [x] バックエンド: WebSocket + BidiAgent ブリッジ（`agent.py`）
- [x] バックエンド: Nova Sonic 設定（`config.py`）, ツール（`tools/`）
- [x] バックエンド: Dockerfile, requirements.txt
- [x] AudioWorklet: マイク→PCM Int16（`pcm-capture-processor.js`）
- [x] AudioWorklet: PCM Int16→スピーカー（`pcm-playback-processor.js`）
- [x] hooks: useWebSocket, useAudioInput, useAudioOutput
- [x] UI: VoiceChat, MicButton, TranscriptView, ConnectionStatus
- [x] App.tsx + main.tsx（Authenticator 統合）
- [x] TypeScript ビルド成功確認
- [x] バックエンドテスト（pytest: 35テスト ALL PASSED）
- [x] フロントエンドテスト（vitest: 28テスト ALL PASSED）

## 完了済み（Phase 2: デプロイ・動作確認）

- [x] `npx ampx sandbox` で Amplify Sandbox デプロイ（Cognito + AgentCore Runtime 作成完了）
- [x] WebSocket 認証方式: JWT Bearer → **SigV4 presigned URL + Cognito Identity Pool** に変更・動作確認
- [x] IAM 権限設定: `bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream`
- [x] ブラウザからの音声対話が E2E で動作確認
- [x] トランスクリプト重複表示バグ修正（non-final → final の上書きロジック）

## Phase 2: 残タスク

- [ ] 割り込み・ツール使用のブラウザ動作確認
- [ ] レイテンシ計測（ブラウザ経由）
- [ ] エラーハンドリング改善
- [ ] 本番デプロイ（Amplify Console）

## 参考

- 仕様書: `docs/spec.md`
- ナレッジ: `docs/knowledge.md`
- ベースプロジェクト: https://github.com/minorun365/marp-agent
- AgentCore 双方向ストリーミングサンプル: https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/01-AgentCore-runtime/06-bi-directional-streaming
