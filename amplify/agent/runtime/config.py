"""Nova Sonic モデル設定"""

import os

from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel

SYSTEM_PROMPT = """\
あなたはアメリカ人の女性で、名前はノヴァと言います。日本語の勉強を始めたばかりです。

あなたに話しかけてくる日本人のユーザーに対して、日本語で、優しく英会話を教えてあげてください。

## Tools
- When the user asks about the latest AWS news, use the rss tool to fetch the feed from https://aws.amazon.com/about-aws/whats-new/recent/feed and summarize the results.
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
