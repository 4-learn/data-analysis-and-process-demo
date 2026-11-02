# 由 run.sh 在容器內執行（host 名稱 da-mdb）；不要直接在本機跑。
"""04 第六段在真實 MariaDB 11.8 + mariadb 1.1.14 上的實測。"""
import json, sys, warnings, datetime
from contextlib import closing
import mariadb, pandas as pd

DDL = """CREATE TABLE IF NOT EXISTS law_articles (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, pcode VARCHAR(16) NOT NULL, law_name VARCHAR(100) NOT NULL,
  slug VARCHAR(16) NOT NULL, article_no VARCHAR(32) NOT NULL, chapter VARCHAR(200) NOT NULL DEFAULT '',
  content TEXT NOT NULL, source_url VARCHAR(500) NOT NULL, content_hash CHAR(64) NOT NULL,
  fetched_at DATETIME NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_article (pcode, slug)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
COLS = ["pcode","law_name","slug","article_no","chapter","content","source_url","content_hash","fetched_at"]
print("python", sys.version.split()[0], "pandas", pd.__version__, "mariadb", mariadb.__version__, "paramstyle", mariadb.paramstyle)
con0 = mariadb.connect(host="da-mdb", user="root", password="pw", database="crawler_course")
print("server", con0.server_info)
cur = con0.cursor(); cur.execute(DDL); cur.execute("DELETE FROM law_articles")
rows = [json.loads(l) for l in open("articles.jsonl", encoding="utf-8")]
def fix(r):
    d = dict(r); d["fetched_at"] = datetime.datetime.fromisoformat(r["fetched_at"]).astimezone(datetime.timezone.utc).replace(tzinfo=None); d["chapter"] = r.get("chapter") or ""
    return tuple(d[c] for c in COLS)
cur.executemany(f"INSERT INTO law_articles ({','.join(COLS)}) VALUES ({','.join('?'*len(COLS))})", [fix(r) for r in rows])
con0.commit(); cur.execute("SELECT COUNT(*) FROM law_articles"); print("loaded", cur.fetchone()[0]); con0.close()

SQL = ("SELECT pcode, slug, article_no, content FROM law_articles "
       "WHERE pcode = ? AND content LIKE ? ORDER BY id")
with closing(mariadb.connect(host="da-mdb", user="root", password="pw", database="crawler_course")) as con:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        df = pd.read_sql(SQL, con, params=("N0060014", "%墜落%"))
        df2 = pd.read_sql(SQL, con, params=("N0060014", "%墜落%"))
    print("rows", len(df), "warnings", [(x.category.__name__, str(x.message)[:60]) for x in w])
    # %s placeholder
    try:
        d3 = pd.read_sql(SQL.replace("?", "%s"), con, params=("N0060014", "%墜落%")); print("%s rows", len(d3))
    except Exception as e: print("%s err", type(e).__module__, type(e).__name__, str(e)[:80])
    warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy", category=UserWarning)
    t = pd.read_sql("SELECT fetched_at, AVG(CHAR_LENGTH(content)) AS avg_len, LENGTH('墜落') AS len_b, CHAR_LENGTH('墜落') AS len_c, 'a' || 'b' AS pipes FROM law_articles GROUP BY fetched_at LIMIT 1", con)
    print("dtypes", dict(t.dtypes.astype(str)))
    print("values", t.iloc[0].to_dict())
    t2 = pd.read_sql("SELECT AVG(CHAR_LENGTH(content)) AS avg_len FROM law_articles", con, coerce_float=False)
    print("coerce_float=False", t2["avg_len"].dtype, type(t2["avg_len"].iloc[0]).__name__)
    cur = con.cursor(); cur.execute("SELECT fetched_at, AVG(CHAR_LENGTH(content)) FROM law_articles GROUP BY fetched_at LIMIT 1"); r = cur.fetchone(); print("driver types", type(r[0]).__name__, type(r[1]).__name__); cur.close()
    try:
        pd.read_sql("SELECT no_such_col FROM law_articles", con)
    except Exception as e:
        print("error type", type(e).__module__ + "." + type(e).__name__, "| is pd DatabaseError:", isinstance(e, pd.errors.DatabaseError), "| is mariadb.Error:", isinstance(e, mariadb.Error))
    inj = "N0060014' OR '1'='1"
    print("inject concat", len(pd.read_sql(f"SELECT id FROM law_articles WHERE pcode = '{inj}'", con)),
          "params", len(pd.read_sql("SELECT id FROM law_articles WHERE pcode = ?", con, params=(inj,))))
