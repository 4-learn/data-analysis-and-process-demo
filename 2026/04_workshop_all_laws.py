"""第 04 節 Workshop 課堂題：用本節的 read_jsonl() 讀全量 749 條，算每部法規幾條。"""

from importlib import import_module

demo = import_module("04_read_jsonl")      # 檔名以數字開頭，不能寫 import 04_read_jsonl，改用 import_module

if __name__ == "__main__":
    df = demo.read_jsonl(demo.DATA / "articles.jsonl")
    print(f"全部 {len(df)} 條；slug 的型別：{df['slug'].dtype}")
    print(df.groupby("law_name", sort=False).size().to_string())
