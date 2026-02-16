# Voice Agent - ナレッジ

## Nova Sonic + Strands BidiAgent

### 基本

- Strands Agents の `BidiAgent` は実験的機能。`strands-agents[bidi]` でインストール
- Python 3.12+ 必須
- `from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel` で import
- モデル ID: `amazon.nova-sonic-v1:0`
- 対応リージョン: `us-east-1`, `eu-north-1`, `ap-northeast-1`（Nova 2 Sonic は `us-west-2` も追加）

### 音声入力の仕組み

- Nova Sonic は **Speech-to-Speech モデル**であり、テキスト入力だけでは応答を生成しない
- VAD（Voice Activity Detection）が「発話 → 無音」の遷移を検出してターンを切り替える
- テキスト入力イベント (`BidiTextInputEvent`) を送っても、音声ストリームがないと応答しない
- サイン波などの非音声オーディオも VAD に検出されない
- **実際の人間の音声**（または TTS 生成音声）を送る必要がある

### 日本語対応

- Nova Sonic v1 の公式対応言語に日本語は含まれない
- **しかし、実際には日本語の音声入力を認識し、日本語で応答できる**（2026-02-16 検証済み）
- ユーザー発話のトランスクリプトはローマ字（`konnichiwa kyou wa ii tenki desu ne`）
- アシスタントの応答テキスト・音声は自然な日本語

### BidiNovaSonicModel の初期化

#### client_config の注意点

`boto_session` と `region` は **同時に指定できない**。

```python
# NG: ValueError が発生する
model = BidiNovaSonicModel(
    model_id="amazon.nova-sonic-v1:0",
    client_config={
        "region": "us-east-1",
        "boto_session": session,  # region と併用不可
    },
)

# OK: boto_session にリージョンを含める
session = boto3.Session(profile_name="sandbox", region_name="us-east-1")
model = BidiNovaSonicModel(
    model_id="amazon.nova-sonic-v1:0",
    client_config={
        "boto_session": session,
    },
)

# OK: region のみ（デフォルトの認証情報チェーンを使用）
model = BidiNovaSonicModel(
    model_id="amazon.nova-sonic-v1:0",
    client_config={
        "region": "us-east-1",
    },
)
```

#### AWS SSO プロファイルを使う場合

`AWS_PROFILE` 環境変数だけでは BidiNovaSonicModel に渡らない場合がある。
明示的に `boto3.Session(profile_name=...)` を作成して `client_config["boto_session"]` に渡すのが確実。

```python
import boto3

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
    client_config={
        "boto_session": session,
    },
)
```

### BidiAgent の入出力インターフェース

- `BidiInput` / `BidiOutput` は Protocol（duck typing）
- 必要メソッド: `__call__`, `start(agent)`, `stop()`
- `__call__` は入力では `BidiInputEvent` を返す awaitable、出力では `BidiOutputEvent` を受け取る awaitable
- `run()` 内で `input_()` が繰り返し呼ばれる（ループ）
- 入力に async generator は使えない（`__call__` が awaitable を返す callable が必要）

### BidiAudioInputEvent

```python
BidiAudioInputEvent(
    audio=base64_encoded_string,
    format="pcm",
    sample_rate=16000,
    channels=1
)
```

- `audio`: base64 エンコードされた PCM 16bit LE データ
- `sample_rate` と `channels` は必須引数（省略すると TypeError）

### 受信イベント型

| イベント | 説明 |
|---------|------|
| `BidiConnectionStartEvent` | 接続確立 |
| `BidiUsageEvent` | トークン使用量（`inputTokens`, `outputTokens`, `totalTokens`） |
| `BidiResponseStartEvent` | レスポンス開始 |
| `BidiTranscriptStreamEvent` | テキストトランスクリプト（`role`, `text`, `is_final`） |
| `BidiAudioStreamEvent` | 音声出力データ（`audio`: base64） |
| `BidiResponseCompleteEvent` | レスポンス完了 |
| `BidiInterruptionEvent` | ユーザー割り込み検出（`reason`: `user_speech`） |
| `BidiConnectionCloseEvent` | 接続終了 |
| `BidiErrorEvent` | エラー |
| `ToolUseStreamEvent` | ツール呼び出し（`name`, `input`, `toolUseId`） |
| `ToolResultEvent` | ツール実行結果（`status`, `content`） |
| `ToolResultMessageEvent` | ツール結果のメッセージ化（`role: user` として注入） |

### テスト方法（マイクなし環境）

macOS の `say` + `ffmpeg` で音声ファイルを生成し、PCM 16bit 16kHz mono に変換して送信：

```bash
say -v Kyoko -o /tmp/speech.aiff "こんにちは"
ffmpeg -y -i /tmp/speech.aiff -f s16le -acodec pcm_s16le -ar 16000 -ac 1 /tmp/speech.pcm
```

送信後は 2-3 秒の無音チャンクを追加して VAD のターン検出をトリガーする。

### 依存関係

```
strands-agents[bidi]    # BidiAgent + Nova Sonic
botocore[crt]           # AWS SSO認証（aws login）に必須
```

macOS では PyAudio のために `brew install portaudio` が必要。

### ツール使用（Function Calling）

- BidiAgent + Nova Sonic の音声対話中にツール呼び出しが**正常に動作する**（2026-02-16 検証済み）
- `@tool` デコレータで定義したツールが `tools=` パラメータ経由で利用可能
- システムプロンプトで「ツールを積極的に使って」と指示すると呼び出し率が上がる

#### イベントフロー

ツール呼び出し時のイベント順序:
1. `BidiTranscriptStreamEvent` (user, is_final=True) — ユーザー発話の確定
2. `ToolUseStreamEvent` — ツール呼び出し（name, input）
3. `ToolResultEvent` — ツール実行結果（status, content）
4. `ToolResultMessageEvent` — ツール結果のメッセージ化
5. `BidiTranscriptStreamEvent` (assistant) — ツール結果を踏まえた応答テキスト
6. `BidiAudioStreamEvent` — 応答音声

#### 検証結果

| ツール | 質問（TTS） | 認識テキスト | ツール呼び出し | 応答 |
|--------|-----------|------------|-------------|------|
| `get_current_time` | 「今何時ですか？」 | `ima nanji desu ka` | ✅ `get_current_time()` | 「現在 2026年2月16日 (月) 15時24分です」 |
| `simple_calculator` | 「3かける5は何ですか？」 | `三かける五は何ですか` | ✅ `simple_calculator("3 * 5")` | 「三かける五は15です」 |

### 割り込み（Barge-in）

- エージェント応答中にユーザーが話しかけると **`BidiInterruptionEvent` (reason: `user_speech`)** が発生する（2026-02-16 検証済み）
- エージェントの音声出力は中断され、新しいユーザー発話が処理される
- 割り込み後、`stop_conversation` ツールが呼ばれて会話が正常終了することも確認

### レイテンシ（2026-02-16 計測、us-east-1）

シンプルな質問（「お元気ですか」、ツールなし）で3回計測した平均値:

| メトリクス | 平均 | 最小 | 最大 |
|-----------|------|------|------|
| ResponseStart（応答処理開始） | 2,348ms | 2,321ms | 2,364ms |
| 最初のトランスクリプト | 2,348ms | 2,321ms | 2,364ms |
| **最初の音声出力** | **2,533ms** | 2,509ms | 2,550ms |
| 確定トランスクリプト | 5,011ms | 4,950ms | 5,076ms |

- 発話終了（無音開始）から最初の音声レスポンスまで約 **2.5秒**
- ツール呼び出しを含む場合は約 **5秒**（ツール実行時間を含む）
- 3回の計測で値は安定しており、ばらつきは小さい

---

## Phase 2 実装で得たナレッジ

### BidiNovaSonicModel の公開属性

コンストラクタの引数名（`provider_config`, `client_config`）と、インスタンスの公開属性名は異なる。

```python
model = get_model()

# 公開属性
model.region          # "us-east-1"（client_config["region"] に対応）
model.model_id        # "amazon.nova-sonic-v1:0"
model.config          # dict: audio/inference/turn_detection を含む統合設定
model.config["audio"]["voice"]              # "tiffany"
model.config["audio"]["input_sample_rate"]  # 16000
model.config["audio"]["output_sample_rate"] # 16000

# ※ model.client_config, model.provider_config は存在しない
```

### AgentCore WebSocket サポート

- `BedrockAgentCoreApp` は `@app.websocket` デコレータをネイティブサポート
- デフォルトパス: `/ws`（ポート 8080）
- `@app.entrypoint`（HTTP SSE）とは別物。BidiAgent には `@app.websocket` を使う
- ヘルスチェック `/ping` は AgentCore が自動処理（明示的な実装不要）

```python
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.websocket
async def websocket_handler(websocket, context):
    await websocket.accept()
    # websocket は Starlette の WebSocket インターフェース
    # receive_json(), send_json(), close() 等が使える
```

### カスタム BidiInput / BidiOutput の実装パターン

BidiAgent の `run()` に渡すカスタム I/O。Protocol（duck typing）で `__call__`, `start`, `stop` を実装する。

```python
class WebSocketBidiInput:
    def __init__(self, websocket): self.websocket = websocket
    async def start(self, agent): pass
    async def stop(self): pass
    async def __call__(self):
        while True:  # 非audioメッセージをスキップするループが必要
            data = await self.websocket.receive_json()
            if data.get("type") == "audio":
                return BidiAudioInputEvent(
                    audio=data["audio"], format="pcm",
                    sample_rate=16000, channels=1
                )

class WebSocketBidiOutput:
    def __init__(self, websocket): self.websocket = websocket
    async def start(self, agent): pass
    async def stop(self): pass
    async def __call__(self, event):
        event_type = event.get("type", "")
        if event_type == "bidi_audio_stream":
            await self.websocket.send_json({"type": "audio", "audio": event["audio"]})
        elif event_type == "bidi_transcript_stream":
            await self.websocket.send_json({...})
        # ...
```

**注意点:**
- `__call__` の入力側は「次のチャンクが来るまでブロック」する設計（`await receive_json()`）
- WebSocket 切断時は `receive_json()` が例外を投げ、`run()` のループが終了する
- 出力イベントは TypedDict 形式（`event["type"]`, `event["audio"]` 等で dict アクセス）
- `ToolUseStreamEvent` の type 文字列は `"tool_use_stream"`（`"bidi_"` プレフィックスなし）

### WebSocket メッセージプロトコル

**ブラウザ → バックエンド:**
```json
{"type": "audio", "audio": "<base64 PCM 16kHz 16bit mono>"}
```

**バックエンド → ブラウザ:**
```json
{"type": "audio", "audio": "<base64>"}
{"type": "transcript", "role": "user|assistant", "text": "...", "is_final": true}
{"type": "interruption"}
{"type": "tool_use", "name": "get_current_time"}
{"type": "error", "message": "..."}
```

### WebSocket 認証（ブラウザからの接続）

ブラウザの WebSocket API はカスタムヘッダー (`Authorization`) を設定できないため、**SigV4 事前署名 URL** を使う。

#### 公式サンプルの方式（Python botocore で実績あり）

```
wss://bedrock-agentcore.{region}.amazonaws.com/runtimes/{runtime_arn}/ws?qualifier=DEFAULT
```
- ARN は **エンコードしない**（公式サンプル準拠）
- `qualifier=DEFAULT` は**必須**
- `botocore.auth.SigV4QueryAuth` で HTTPS 版 URL に署名 → `wss://` に変換

#### ブラウザ実装（@smithy/signature-v4）

```typescript
import { SignatureV4 } from '@smithy/signature-v4';
import { HttpRequest } from '@smithy/protocol-http';
import { Sha256 } from '@aws-crypto/sha256-js';

const session = await fetchAuthSession();
const credentials = session.credentials; // Cognito Identity Pool の IAM 認証情報

const signer = new SignatureV4({
  service: 'bedrock-agentcore', region,
  credentials, sha256: Sha256,
  // uriEscapePath: true (デフォルト) を使う → botocore と一致
});
const request = new HttpRequest({
  method: 'GET', protocol: 'https:', hostname, path, query: { qualifier: 'DEFAULT' },
  headers: { host: hostname },
});
const presigned = await signer.presign(request, { expiresIn: 300 });
// presigned.query から RFC 3986 形式でクエリ文字列を構築
```

#### 重要: JWT 認証は WebSocket に使えない

- `RuntimeAuthorizerConfiguration.usingJWT()` で設定した JWT 認証は HTTP invocations 用
- ブラウザの WebSocket API はカスタムヘッダーを設定できないので Bearer トークンを渡せない
- **解決策**: JWT 認証を削除し、IAM (SigV4) 認証に変更。Cognito Identity Pool の認証済みロールに権限付与

#### IAM 権限（WebSocket 用）

```typescript
// Cognito 認証済みロールに付与するポリシー
new iam.PolicyStatement({
  actions: ['bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream'],
  resources: [
    runtime.agentRuntimeArn,        // Runtime ARN 本体
    `${runtime.agentRuntimeArn}/*`, // サブリソース
  ],
})
```

**注意点:**
- アクション名は `bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream`（`bedrock-agentcore:*` では不十分）
- リソースは Runtime ARN そのもの + ワイルドカード（`/runtime-endpoint/DEFAULT` 等のサブリソースもカバー）
- `Amplify.getConfig()` は `custom` フィールドを返さない → `amplify_outputs.json` を直接 import して使う

### AudioWorklet 実装

#### マイク入力（pcm-capture-processor.js）
- `AudioContext({ sampleRate: 16000 })` で 16kHz に設定
- Float32 → Int16 変換: `s < 0 ? s * 0x8000 : s * 0x7FFF`
- `postMessage()` で ArrayBuffer を main thread に転送（Transferable で効率的）
- main thread で Int16 ArrayBuffer → base64 変換して WebSocket 送信

#### スピーカー出力（pcm-playback-processor.js）
- リングバッファ方式で低レイテンシ再生（最大 5 秒分 @ 16kHz）
- `postMessage('clearBuffer')` で割り込み時にバッファクリア
- Int16 → Float32 変換: `int16Data[i] / 32768`

#### base64 変換ユーティリティ
```typescript
// ArrayBuffer → base64
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

// base64 → ArrayBuffer
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}
```

### テスト構成

| レイヤー | フレームワーク | ファイル数 | テスト数 |
|----------|-----------|----------|---------|
| フロントエンド | vitest + @testing-library/react | 6 | 28 |
| バックエンド | pytest + pytest-asyncio | 3 | 35 |
| 合計 | | 9 | 63 |

**テスト環境のポイント:**
- jsdom に `scrollTo`, `AudioContext`, `AudioWorkletNode`, `MediaDevices` のモックが必要
- `@testing-library/react` の cleanup は vitest では自動実行されない → setup.ts で `afterEach(cleanup)` が必要
- WebSocket モックには `static OPEN = 1` 定数の定義が必要（`readyState === WebSocket.OPEN` の比較用）
- バックエンドの venv は `amplify/agent/runtime/.venv/` に独立して管理

### Dockerfile（AgentCore コンテナ）

- `strands-agents[bidi]` は PyAudio を依存に含む（BidiAudioIO 用）
- Python slim イメージには C コンパイラがないため、PyAudio のビルドに失敗する
- **解決策**: `portaudio19-dev` + `build-essential` を `apt-get install` で追加
- コンテナ内では WebSocket I/O を使うため PyAudio 自体は不要だが、`[bidi]` extra の依存として必要

### サンドボックスデプロイ

- `npx ampx sandbox --once --profile sandbox` で一発デプロイ
- Docker Desktop が起動していないとコンテナビルドが失敗する
- 初回デプロイ: Cognito + AgentCore Runtime 作成で約2分
- `amplify_outputs.json` が自動生成され、フロントエンドの設定に使われる

### トランスクリプトの重複表示バグと修正

Nova Sonic はストリーミング中に `isFinal=false` の部分トランスクリプトを送り、最後に `isFinal=true` の確定トランスクリプトを送る。

**バグ（修正前）:**
`isFinal=false` のときだけ直前エントリを上書きしていたため、`isFinal=true` が来ると新しいエントリとして追加され、同じ応答が吹き出しで2回表示された。

```typescript
// NG: isFinal=true のとき上書きロジックをスキップしてしまう
if (!isFinal) {
  // ...上書きロジック
}
return [...prev, { role, text, isFinal, timestamp }]; // 常に新規追加
```

**修正後:**
`isFinal` の値に関わらず、直前エントリが同じロールで `isFinal=false` なら上書き。

```typescript
// OK: 直前が non-final なら常に上書き（non-final→non-final も non-final→final も）
const lastIdx = prev.length - 1;
if (lastIdx >= 0 && prev[lastIdx].role === role && !prev[lastIdx].isFinal) {
  const updated = [...prev];
  updated[lastIdx] = { ...updated[lastIdx], text, isFinal };
  return updated;
}
return [...prev, { role, text, isFinal, timestamp }];
```
