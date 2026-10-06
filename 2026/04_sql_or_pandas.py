"""第 04 節：同一份條文放在資料庫裡，哪些事該在 SQL 做，哪些該拉進 pandas 做。"""

import sqlite3
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"

# 欄位與唯一鍵同爬蟲課第 16 節的 law_articles；型別改成 SQLite 的寫法（SQLite 沒有 VARCHAR 長度、DATETIME）
SCHEMA = """
CREATE TABLE law_articles (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  pcode        TEXT NOT NULL,
  law_name     TEXT NOT NULL,
  slug         TEXT NOT NULL,
  article_no   TEXT NOT NULL,
  chapter      TEXT NOT NULL DEFAULT '',
  content      TEXT NOT NULL,
  source_url   TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  fetched_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (pcode, slug)
)"""
COLUMNS = ["pcode", "law_name", "slug", "article_no", "chapter", "content",
           "source_url", "content_hash", "fetched_at"]
INSERT = f"INSERT INTO law_articles ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})"


def build_db(articles):
    """在記憶體建一個與爬蟲課第 16 節同欄位的資料庫，載入條文。"""
    missing = [c for c in COLUMNS if c not in articles.columns]
    if missing:
        raise ValueError(f"缺少欄位 {missing}")
    con = sqlite3.connect(":memory:")
    con.execute(SCHEMA)
    load(con, articles)
    return con


def load(con, articles):
    with con:   # 一批一起成功或一起失敗
        con.executemany(INSERT, articles[COLUMNS].itertuples(index=False, name=None))


def find_articles(con, pcode, keyword, columns=("pcode", "slug", "article_no", "content")):
    """先篩再拉：值一律用 ? 佔位；欄名不能當參數，只能從白名單挑。"""
    bad = [c for c in columns if c not in COLUMNS]
    if bad:
        raise ValueError(f"不允許的欄位 {bad}")
    sql = (f"SELECT {', '.join(columns)} FROM law_articles "
           "WHERE pcode = ? AND content LIKE ? ORDER BY id")
    return pd.read_sql(sql, con, params=(pcode, f"%{keyword}%"))


def naive_find(con, pcode, keyword):
    """AI 常給的寫法：把值拼進 SQL 字串。"""
    sql = f"SELECT pcode, slug, content FROM law_articles WHERE pcode = '{pcode}' AND content LIKE '%{keyword}%'"
    return pd.read_sql(sql, con)


def transfer_bytes(df):
    """從資料庫拉過來的資料量：每一格轉成文字後的 UTF-8 位元組數加總（粗略，但不受 pandas 版本影響）。"""
    return sum(len(str(v).encode("utf-8")) for row in df.itertuples(index=False) for v in row)


def describe(df):
    return ", ".join(f"{c}={df[c].dtype}" for c in df.columns)


if __name__ == "__main__":
    articles = pd.read_json(DATA / "articles.jsonl", lines=True, dtype=False, convert_dates=False)
    con = build_db(articles)

    print("== 1. 建表、載入 ==")
    print(f"載入 {pd.read_sql('SELECT COUNT(*) AS n FROM law_articles', con)['n'].iloc[0]} 列")
    try:
        load(con, articles.head(3))
    except sqlite3.IntegrityError as exc:
        print(f"同一批再載入一次 → IntegrityError: {exc}")
    print(f"之後仍是 {pd.read_sql('SELECT COUNT(*) AS n FROM law_articles', con)['n'].iloc[0]} 列")
    print(f"articles.jsonl 有、資料表沒有的欄位：{[c for c in articles.columns if c not in COLUMNS]}")

    print("\n== 2. 同一題：每部法規幾條 ==")
    in_sql = pd.read_sql("SELECT pcode, law_name, COUNT(*) AS n FROM law_articles "
                         "GROUP BY pcode, law_name ORDER BY pcode", con)
    pulled = pd.read_sql("SELECT pcode, law_name FROM law_articles", con)
    in_pandas = pulled.groupby(["pcode", "law_name"]).size().reset_index(name="n")
    print(in_sql.to_string(index=False))
    print(f"SQL 傳回 {len(in_sql)} 列；pandas 先拉 {len(pulled)} 列再算；兩者 equals：{in_sql.equals(in_pandas)}")

    print("\n== 3. 先篩再拉 vs 全拉再篩 ==")
    everything = pd.read_sql("SELECT * FROM law_articles", con)
    after = everything[(everything["pcode"] == "N0060014") & everything["content"].str.contains("墜落", regex=False)]
    after = after[["pcode", "slug", "article_no", "content"]].reset_index(drop=True)
    before = find_articles(con, "N0060014", "墜落")
    for label, df in [("全拉", everything), ("全拉再篩（結果）", after), ("先篩再拉", before)]:
        print(f"{label:10} {len(df):>4} 列 × {df.shape[1]:>2} 欄  約 {transfer_bytes(df):>7,} 位元組")
    print(f"兩種做法結果 equals：{after.equals(before)}；全拉多搬了 {transfer_bytes(everything) / transfer_bytes(before):.0f} 倍")

    print("\n== 4. 字串拼接 vs params ==")
    for label, pcode in [("正常輸入", "N0060014"), ("惡意輸入", "N0060014' OR '1'='1"), ("帶引號的輸入", "N0060014'")]:
        try:
            naive = f"{len(naive_find(con, pcode, '墜落'))} 列"
        except Exception as exc:
            naive = f"{type(exc).__name__}（{exc.__cause__}）"
        safe = len(find_articles(con, pcode, "墜落"))
        print(f"{label:6}  拼接 → {naive:38}  params → {safe} 列")

    print("\n== 5. read_sql 讀進來的型別 ==")
    stats = pd.read_sql(
        "SELECT law_name, COUNT(*) AS n, AVG(LENGTH(content)) AS avg_len, "
        "SUM(CASE WHEN chapter = '' THEN 1 END) AS no_chapter, MAX(fetched_at) AS fetched_at "
        "FROM law_articles GROUP BY law_name ORDER BY n DESC", con)
    print(describe(stats))
    print(stats.head(3).to_string(index=False))
    print(f"no_chapter 非空的只有：{stats.loc[stats['no_chapter'].notna(), 'law_name'].tolist()}")
    chap = pd.read_sql("SELECT chapter, NULLIF(chapter, '') AS chapter_or_null FROM law_articles", con)
    print(f"chapter 空字串 {(chap['chapter'] == '').sum()} 列；NULLIF 之後 NaN {chap['chapter_or_null'].isna().sum()} 列")
    print(f"groupby 預設 {int(chap.groupby('chapter_or_null').size().sum())} 列；dropna=False {int(chap.groupby('chapter_or_null', dropna=False).size().sum())} 列")
    empty = pd.read_sql("SELECT pcode, COUNT(*) AS n FROM law_articles WHERE pcode = ? GROUP BY pcode", con, params=("N9999999",))
    print(f"查無資料：{len(empty)} 列，{describe(empty)}")
    con.close()
