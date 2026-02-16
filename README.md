# Nova Sonic Agent

Amazon Nova Sonic を使った音声対話型の英会話練習アプリです。ブラウザのマイクから話しかけると、AI 英会話チューター「ノヴァ」がリアルタイムに音声で応答します。

簡単なTool Useを行なって、AWSのアップデート情報などを確認してもらうこともできます。

<img width="1177" height="906" alt="スクリーンショット 2026-02-16 23 50 23" src="https://github.com/user-attachments/assets/dfee5224-6a18-4d7c-8b2c-5b510508adfd" />

## アーキテクチャ

- **フロントエンド**: React + Tailwind CSS（Vite）
- **認証**: Amazon Cognito（Amplify Auth）
- **エージェント**: [Strands Agents](https://github.com/strands-agents/sdk-python) の BidiAgent + Amazon Nova Sonic
- **ホスティング**: [Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-core.html) Runtime（WebSocket）
- **デプロイ**: AWS Amplify Gen2（CDK）

ブラウザ → WebSocket（SigV4 認証）→ AgentCore Runtime → BidiAgent（Nova Sonic）

## 前提条件

- Node.js 18+
- Python 3.12+
- AWS CLI（SSO 認証設定済み）
- AWS アカウントで以下が利用可能であること:
  - Amazon Bedrock（Nova Sonic モデルアクセス有効化済み、us-east-1）
  - Bedrock AgentCore

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/minorun365/nova-sonic-agent.git
cd nova-sonic-agent

# フロントエンドの依存関係をインストール
npm install
```

## ローカル開発（Amplify Sandbox）

```bash
# Sandbox 環境をデプロイ（Cognito + AgentCore Runtime をプロビジョニング）
npm run sandbox

# 別ターミナルでフロントエンドを起動
npm run dev
```

Sandbox 起動時に `.env` にテストユーザー情報を設定しておくと、Cognito にテストユーザーが自動作成されます。

```
TEST_USER_EMAIL=your-email@example.com
TEST_USER_PASSWORD=YourPassword123!
```

## 本番デプロイ

Amplify Hosting でリポジトリを接続すると、push 時に自動デプロイされます。
