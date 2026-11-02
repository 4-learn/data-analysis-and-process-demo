"""第 18 節 Workshop 課堂題：每部法規的條文長度分布（條數、中位數、p95、最大值）。"""

from importlib import import_module

demo = import_module("18_text_corpus")   # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    df = demo.read_articles()
    length = df["content"].str.len()
    print(length.groupby(df["law_name"], sort=False).describe(percentiles=[0.5, 0.95]).round(0).to_string())
