"""第 05 節 Workshop 課堂題：「每部法規最長的一條有幾個字？」SQL 算一次、pandas 算一次，再比對。"""

from importlib import import_module

import pandas as pd

demo = import_module("05_sql_or_pandas")   # 檔名以數字開頭，改用 import_module 匯入

if __name__ == "__main__":
    articles = pd.read_json(demo.DATA / "articles.jsonl", lines=True, dtype=False, convert_dates=False)
    con = demo.build_db(articles)

    in_sql = pd.read_sql("SELECT pcode, MAX(LENGTH(content)) AS n FROM law_articles "
                         "GROUP BY pcode ORDER BY pcode", con)

    pulled = pd.read_sql("SELECT pcode, content FROM law_articles", con)
    in_pandas = (pulled.assign(n=pulled["content"].str.len())
                 .groupby("pcode")["n"].max().reset_index())

    print(in_sql.to_string(index=False))
    print(f"兩邊 equals：{in_sql.equals(in_pandas)}")
