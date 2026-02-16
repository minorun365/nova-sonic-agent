"""Nova Sonic モデル設定"""

import os

from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel

SYSTEM_PROMPT = """\
あなたは親切な日本語の音声アシスタントです。
ユーザーと自然な日本語で会話してください。
回答は簡潔に、話し言葉で応答してください。
ツールが必要な場合は積極的に使ってください。
ユーザーが「終了」「さようなら」「バイバイ」と言ったら、stop_conversation ツールを使って会話を終了してください。
"""


def get_model() -> BidiNovaSonicModel:
    region = os.environ.get("NOVA_SONIC_REGION", "us-east-1")
    voice = os.environ.get("NOVA_SONIC_VOICE", "tiffany")

    return BidiNovaSonicModel(
        model_id="amazon.nova-sonic-v1:0",
        provider_config={
            "audio": {
                "input_sample_rate": 16000,
                "output_sample_rate": 16000,
                "voice": voice,
            },
        },
        client_config={
            "region": region,
        },
    )
