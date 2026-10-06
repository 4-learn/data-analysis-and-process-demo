# 由 run.sh 在容器內執行（host 名稱 da-mdb）；不要直接在本機跑。
import re, warnings, json
from contextlib import closing
import mariadb, pandas as pd
warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy", category=UserWarning)
src = open("04-sql-or-pandas.md", encoding="utf-8").read()
code = re.search(r"<!-- demo: [\w.]+ -->\n```python\n(.*?)\n```", src, re.S).group(1)
ns = {"__name__": "demo04", "__file__": "/w/x.py"}; exec(code, ns)
with closing(mariadb.connect(host="da-mdb", user="root", password="pw", database="crawler_course")) as con:
    print("find 墜落", len(ns["find_articles"](con, "N0060014", "墜落")))
    print("find %", len(ns["find_articles"](con, "N0060014", "%")))
    print("naive inject", len(ns["naive_find"](con, "N0060014' OR '1'='1", "墜落")))
    try:
        ns["naive_find"](con, "N0060014", "雇主'")
    except Exception as e:
        print("naive quote err", type(e).__module__ + "." + type(e).__name__)
    sql_b = pd.read_sql("SELECT pcode, MAX(LENGTH(content)) AS max_len FROM law_articles GROUP BY pcode ORDER BY pcode", con)
    sql_c = pd.read_sql("SELECT pcode, MAX(CHAR_LENGTH(content)) AS max_len FROM law_articles GROUP BY pcode ORDER BY pcode", con)
    raw = pd.read_sql("SELECT pcode, content FROM law_articles", con)
    pdv = raw.assign(max_len=raw["content"].str.len()).groupby("pcode", as_index=False)["max_len"].max()
    print("LENGTH equals", sql_b.equals(pdv), "max", sql_b.max_len.max(), "| CHAR_LENGTH equals", sql_c.equals(pdv), "max", sql_c.max_len.max(), "dtypes", sql_c.max_len.dtype, pdv.max_len.dtype)
    print("LIKE collation 墜落 vs ascii case:", len(pd.read_sql("SELECT id FROM law_articles WHERE content LIKE ?", con, params=("%LPG%",))), len(pd.read_sql("SELECT id FROM law_articles WHERE content LIKE ?", con, params=("%lpg%",))))
