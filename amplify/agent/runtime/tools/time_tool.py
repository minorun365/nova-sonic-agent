"""現在時刻取得ツール"""

from datetime import datetime, timedelta, timezone

from strands import tool


@tool
def get_current_time() -> str:
    """現在の日本時間を取得します。

    Returns:
        現在の日本時間の文字列
    """
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    weekday_ja = ["月", "火", "水", "木", "金", "土", "日"]
    weekday = weekday_ja[now.weekday()]
    return f"{now.year}年{now.month}月{now.day}日({weekday}) {now.strftime('%H:%M')} JST"
