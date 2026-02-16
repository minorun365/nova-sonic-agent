"""CLI ベースの音声対話エージェント（Nova Sonic + Strands BidiAgent）

マイクとスピーカーを使ってリアルタイム音声対話を行う。
日本語での対話を試みる実験用スクリプト。

使い方:
    python cli_voice_agent.py [--region REGION] [--voice VOICE] [--text-only]
"""

import argparse
import asyncio

import boto3
from strands import tool
from strands.experimental.bidi import BidiAgent
from strands.experimental.bidi.io import BidiAudioIO, BidiTextIO
from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel
from strands.experimental.bidi.tools import stop_conversation

SYSTEM_PROMPT = """\
あなたは親切な日本語の音声アシスタントです。
ユーザーと自然な日本語で会話してください。
回答は簡潔に、話し言葉で応答してください。
ツールが必要な場合は積極的に使ってください。
ユーザーが「終了」「さようなら」「バイバイ」と言ったら、stop_conversation ツールを使って会話を終了してください。
"""


@tool
def get_current_time() -> str:
    """現在の日本時間を取得します。

    Returns:
        現在の日本時間の文字列
    """
    from datetime import datetime, timedelta, timezone

    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    weekday_ja = ["月", "火", "水", "木", "金", "土", "日"]
    weekday = weekday_ja[now.weekday()]
    return f"{now.year}年{now.month}月{now.day}日({weekday}) {now.strftime('%H:%M')} JST"


@tool
def simple_calculator(expression: str) -> str:
    """簡単な計算を行います。四則演算に対応しています。

    Args:
        expression: 計算式（例: "2 + 3", "10 * 5"）

    Returns:
        計算結果の文字列
    """
    allowed_chars = set("0123456789+-*/.() ")
    if not all(c in allowed_chars for c in expression):
        return "エラー: 許可されていない文字が含まれています"
    try:
        result = eval(expression)  # noqa: S307
        return f"{expression} = {result}"
    except Exception as e:
        return f"計算エラー: {e}"


async def run_voice_agent(region: str, voice: str, text_only: bool, profile: str | None = None) -> None:
    """音声エージェントを起動して対話を開始する。"""

    print(f"Nova Sonic 音声エージェントを起動します...")
    print(f"  リージョン: {region}")
    print(f"  音声: {voice}")
    print(f"  モード: {'テキスト' if text_only else '音声'}")
    if profile:
        print(f"  プロファイル: {profile}")
    print()

    session = boto3.Session(profile_name=profile, region_name=region)

    model = BidiNovaSonicModel(
        model_id="amazon.nova-sonic-v1:0",
        provider_config={
            "audio": {
                "input_sample_rate": 16000,
                "output_sample_rate": 16000,
                "voice": voice,
            },
        },
        client_config={
            "boto_session": session,
        },
    )

    agent = BidiAgent(
        model=model,
        tools=[stop_conversation, get_current_time, simple_calculator],
        system_prompt=SYSTEM_PROMPT,
    )

    if text_only:
        text_io = BidiTextIO()
        print("テキストモードで起動します。キーボードで入力してください。")
        print("「終了」と入力すると会話を終了します。")
        print("-" * 50)
        await agent.run(
            inputs=[text_io.input()],
            outputs=[text_io.output()],
        )
    else:
        audio_io = BidiAudioIO()
        text_io = BidiTextIO()
        print("音声モードで起動します。マイクに向かって話しかけてください。")
        print("「終了」「さようなら」「バイバイ」と言うと会話を終了します。")
        print("-" * 50)
        await agent.run(
            inputs=[audio_io.input()],
            outputs=[audio_io.output(), text_io.output()],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Nova Sonic 音声対話エージェント")
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS リージョン (default: us-east-1)",
    )
    parser.add_argument(
        "--voice",
        default="tiffany",
        help="音声 ID (default: tiffany, 他: matthew)",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="テキストのみモード（マイク/スピーカー不要）",
    )
    parser.add_argument(
        "--profile",
        default="sandbox",
        help="AWS プロファイル (default: sandbox)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_voice_agent(args.region, args.voice, args.text_only, args.profile))
    except KeyboardInterrupt:
        print("\n\n会話を終了しました。")


if __name__ == "__main__":
    main()
