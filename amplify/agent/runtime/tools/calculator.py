"""簡易計算ツール"""

from strands import tool


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
