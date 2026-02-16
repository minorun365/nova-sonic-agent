# Voice Agent - 仕様書

音声で会話できる AI エージェントのデモアプリ。Amazon Nova Sonic + Strands Agents + Bedrock AgentCore を活用し、リアルタイム音声対話とツール使用を実現する。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| 音声モデル | Amazon Nova Sonic (`amazon.nova-sonic-v1:0`) |
| エージェント SDK | Strands Agents (`BidiAgent`, 実験的機能) |
| ランタイム | Bedrock AgentCore Runtime（双方向ストリーミング対応） |
| フロントエンド | React + Vite + Tailwind CSS + Amplify UI |
| 認証 | Amazon Cognito（Amplify Gen2） |
| IaC | CDK（Amplify Gen2 経由） |
| 言語 | Python 3.12+（バックエンド）, TypeScript（フロント/CDK） |

## アーキテクチャ概要

```
[ブラウザ] ←WebSocket→ [AgentCore Runtime] ←双方向ストリーミング→ [Nova Sonic]
  (マイク/スピーカー)     (BidiAgent + ツール)                      (音声理解+生成)
```

- ユーザーのマイク入力をブラウザから WebSocket で AgentCore に送信
- AgentCore 上の Strands `BidiAgent` が Nova Sonic と双方向ストリーミングで通信
- Nova Sonic の音声レスポンスを WebSocket 経由でブラウザに返し、スピーカー再生
- 会話中にツール呼び出し（Web 検索など）も可能

---

## フェーズ構成

### Phase 1: フィジビリティ検証（experiment/） ✅ 完了

Nova Sonic + Strands BidiAgent の基本動作をローカル CLI で確認する。

#### 目的

- BidiAgent + Nova Sonic の音声対話が動くことを確認
- ツール使用（function calling）の動作確認
- 音声入出力（マイク/スピーカー）のハンドリング把握
- 日本語対応状況の確認 → **日本語で動作確認済み**

#### ディレクトリ構成

```
experiment/
├── .venv/                  # Python 仮想環境
├── cli_voice_agent.py      # CLIベースの音声対話エージェント（マイク/スピーカー）
├── test_connection.py      # 接続テスト（音声ファイル入力で自動テスト）
├── test_tools.py           # ツール使用テスト（get_current_time / simple_calculator）
├── test_bargein.py         # 割り込み（barge-in）テスト
├── test_latency.py         # レイテンシ計測テスト
└── requirements.txt
```

#### 実装内容

```python
# cli_voice_agent.py の実装
from strands.experimental.bidi import BidiAgent
from strands.experimental.bidi.io import BidiAudioIO, BidiTextIO
from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel
from strands.experimental.bidi.tools import stop_conversation

session = boto3.Session(profile_name="sandbox", region_name="us-east-1")

model = BidiNovaSonicModel(
    model_id="amazon.nova-sonic-v1:0",
    provider_config={
        "audio": {
            "input_sample_rate": 16000,
            "output_sample_rate": 16000,
            "voice": "tiffany",
        },
    },
    client_config={"boto_session": session},
)

agent = BidiAgent(
    model=model,
    tools=[stop_conversation, get_current_time, simple_calculator],
    system_prompt="あなたは親切な日本語の音声アシスタントです。...",
)

# マイク入力 → スピーカー出力で対話
audio_io = BidiAudioIO()
text_io = BidiTextIO()
await agent.run(inputs=[audio_io.input()], outputs=[audio_io.output(), text_io.output()])
```

#### 依存関係

```
strands-agents[bidi]
botocore[crt]
```

#### 検証結果（全項目完了）

- [x] `BidiAgent` + `BidiNovaSonicModel` で音声対話が成立するか → **OK**
- [x] ツール（calculator 等）を追加して function calling が動作するか → **OK**（`get_current_time`, `simple_calculator` 両方動作）
- [x] ユーザーの割り込み（barge-in）が正しく処理されるか → **OK**（`BidiInterruptionEvent` 発生を確認）
- [x] 対応言語の確認 → **日本語で動作確認済み**（後述）
- [x] レイテンシ（応答までの体感速度） → **約2.5秒**（ツールなし）/ **約5秒**（ツール使用時）
- [ ] マイク/スピーカーによるリアルタイム対話（手動テスト未実施だが、TTS 音声での自動テストは完了）

#### 注意事項

- Python 3.12 以上が必須（実験的 AWS SDK の依存）
- Nova Sonic の対応リージョン: `us-east-1`, `eu-north-1`, `ap-northeast-1`
- `strands-agents[bidi]` は実験的機能（API が変更される可能性あり）
- macOS では PyAudio のために `brew install portaudio` が必要

---

### Phase 2: 本番アプリ実装（ローカル動作確認済み）

Phase 1 の検証結果を踏まえ、Amplify + AgentCore でフルスタック音声対話 Web アプリを構築。

#### ディレクトリ構成

```
voice-agent/
├── amplify/
│   ├── backend.ts                      # CDK エントリ（auth + AgentCore）
│   ├── tsconfig.json
│   ├── auth/resource.ts                # Cognito メール認証
│   └── agent/
│       ├── resource.ts                 # AgentCore Runtime CDK定義
│       └── runtime/
│           ├── Dockerfile              # Python 3.13 slim（ARM64）
│           ├── requirements.txt        # strands-agents[bidi,otel], bedrock-agentcore
│           ├── agent.py                # @app.websocket + BidiAgent ブリッジ
│           ├── config.py               # Nova Sonic モデル設定・システムプロンプト
│           └── tools/
│               ├── __init__.py
│               ├── time_tool.py        # 現在時刻取得
│               └── calculator.py       # 計算機
├── src/
│   ├── main.tsx                        # Amplify 初期化
│   ├── App.tsx                         # Authenticator + VoiceChat
│   ├── index.css                       # Tailwind + カスタムCSS
│   ├── components/
│   │   └── VoiceChat/
│   │       ├── index.tsx               # メインコンポーネント（hooks統合）
│   │       ├── MicButton.tsx           # マイク ON/OFF ボタン
│   │       ├── TranscriptView.tsx      # トランスクリプト表示
│   │       ├── ConnectionStatus.tsx    # 接続状態インジケータ
│   │       └── types.ts               # 型定義
│   ├── hooks/
│   │   ├── useWebSocket.ts            # AgentCore WebSocket 接続 + 認証
│   │   ├── useAudioInput.ts           # マイク → PCM → base64 → 送信
│   │   └── useAudioOutput.ts          # 受信 → PCM → スピーカー再生
│   ├── audio/
│   │   ├── pcm-capture-processor.js   # AudioWorklet: マイク→Int16
│   │   └── pcm-playback-processor.js  # AudioWorklet: Int16→スピーカー
│   └── test/
│       ├── setup.ts                   # vitest セットアップ（モック）
│       └── mocks.ts                   # Amplify モック
├── experiment/                         # Phase 1（そのまま残存）
├── docs/
├── package.json
├── vite.config.ts
└── tsconfig*.json
```

#### バックエンド設計

AgentCore の `@app.websocket` デコレータで WebSocket ハンドラを実装。
`BidiAgent.run()` にカスタム `WebSocketBidiInput` / `WebSocketBidiOutput` を渡し、
ブラウザ ↔ BidiAgent ↔ Nova Sonic のブリッジを実現。

- コンテナはポート 8080 で `/ws` エンドポイントを提供
- WebSocket 接続先: `wss://bedrock-agentcore.{region}.amazonaws.com/runtimes/{runtimeArn}/ws?qualifier=DEFAULT`
- ARN は**エンコードしない**（公式サンプル準拠）
- 認証: IAM (SigV4) 事前署名 URL + Cognito Identity Pool

#### フロントエンド設計

- AudioWorklet で PCM 16kHz 16bit mono の音声キャプチャ・再生
- リングバッファによる低レイテンシ再生
- 割り込み時は `clearBuffer` でバッファクリア
- hooks で WebSocket・マイク・スピーカーをそれぞれ管理し、VoiceChat で統合

#### 認証フロー

1. Amplify UI `<Authenticator>` でメールログイン
2. `fetchAuthSession()` で Cognito Identity Pool の IAM 一時認証情報を取得
3. `@smithy/signature-v4` で SigV4 事前署名 URL を生成
4. 事前署名 URL で WebSocket 接続（認証情報がクエリパラメータに埋め込まれる）

**注意**: ブラウザの WebSocket API はカスタムヘッダーを設定できないため、JWT Bearer トークンは使用不可。IAM (SigV4) 認証を採用。

#### テスト

| レイヤー | フレームワーク | テスト数 |
|----------|-----------|---------|
| フロントエンド | vitest + @testing-library/react | 28 |
| バックエンド | pytest + pytest-asyncio | 35 |

---

## 言語対応について

Nova Sonic の公式対応言語に日本語は含まれていないが、実際にはある程度日本語でも動作するとの報告がある。

**方針**: まずは日本語で対話する前提で実装・検証を進める。

### Phase 1 検証結果（2026-02-16）

**日本語の音声対話: 動作確認済み** ✅

| 項目 | 結果 |
|------|------|
| 接続 | `BidiAgent` + `BidiNovaSonicModel` で Nova Sonic (`amazon.nova-sonic-v1:0`) に接続成功 |
| 英語音声入力 | "Hello, how are you today?" → 正しく認識・応答 |
| 日本語音声入力 | 「こんにちは、今日はいい天気ですね」→ 正しく認識・日本語で応答 |
| 日本語認識精度 | ユーザー発話はローマ字で認識される（`konnichiwa kyou wa ii tenki desu ne`） |
| 日本語応答品質 | 自然な日本語で応答（「こんにちは！今日は確かにいい天気ですね」） |
| 音声出力 | 英語: 198KB / 日本語: 398KB の音声データを生成 |
| テキストのみ入力 | 動作しない（Nova Sonic は音声入力の VAD でターン検出が必要） |

**補足:**
- Nova Sonic は Speech-to-Speech モデルのため、テキスト入力だけでは応答しない
- 音声の VAD（Voice Activity Detection）が「発話 → 無音」の遷移を検出してターンを切り替える
- `BidiTextIO` のテキストモードも、内部的にはテキスト入力イベントを送るが、VAD トリガーなしでは応答しない可能性がある（要追加検証）
- 日本語のユーザー発話はローマ字でトランスクリプトされるが、モデルの理解・応答は正確

---

## 参考リソース

### 公式ドキュメント

- [Strands Agents - BidiAgent](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/bidirectional-streaming/agent/)
- [Strands Agents - Nova Sonic](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/bidirectional-streaming/models/nova_sonic/)
- [Amazon Nova Sonic ユーザーガイド](https://docs.aws.amazon.com/nova/latest/userguide/speech.html)
- [AgentCore WebSocket Getting Started](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-websocket.html)

### AWS 公式サンプル

| リポジトリ | 内容 |
|-----------|------|
| [sample-aws-strands-nova-voice-assistant](https://github.com/aws-samples/sample-aws-strands-nova-voice-assistant) | マルチエージェント音声アシスタント |
| [sample-nova-sonic-speech2speech-webrtc](https://github.com/aws-samples/sample-nova-sonic-speech2speech-webrtc) | Nova 2 Sonic + WebRTC |
| [sample-sonic-cdk-agent](https://github.com/aws-samples/sample-sonic-cdk-agent) | CDK テンプレートでデプロイ |
| [sample-nova-sonic-agentic-chatbot](https://github.com/aws-samples/sample-nova-sonic-agentic-chatbot) | Next.js + FastAPI チャットボット |
| [amazon-bedrock-agentcore-samples (06-bi-directional-streaming)](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/01-AgentCore-runtime/06-bi-directional-streaming) | AgentCore 双方向ストリーミング チュートリアル |

### ベースプロジェクト

- [minorun365/marp-agent](https://github.com/minorun365/marp-agent) — Amplify + AgentCore + CDK の構成を参考にする
