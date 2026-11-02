"""第 01 節 Workshop 課堂題：用本節的 estimate_tokens() 量「整份丟進去」有多長。
把 AI 給你的 prompt 存成 prompt.txt 放在同一個資料夾，再跑一次就會一起量。"""

from importlib import import_module
from pathlib import Path

demo = import_module("01_position")   # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    raw = demo.EVENTS.read_text(encoding="utf-8")
    print(f"整份 events.jsonl：估計 {demo.estimate_tokens(raw):,} token")
    prompt = Path(__file__).resolve().parent / "prompt.txt"
    if prompt.exists():
        print(f"prompt.txt：估計 {demo.estimate_tokens(prompt.read_text(encoding='utf-8')):,} token")
    else:
        print("（沒有 prompt.txt：把 AI 組出來的 prompt 存成這個檔名，再跑一次）")
