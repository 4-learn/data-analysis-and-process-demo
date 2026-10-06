# 04｜該在資料庫做，還是拉進 pandas？

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 04 節：該在資料庫做，還是拉進 pandas？**
> 本節把爬蟲課第 16 節寫進 `law_articles` 的 749 條條文，從資料庫讀進 pandas。同一題各用 SQL 與 pandas 做一次，比較結果、搬運量與安全性，並看清楚 `read_sql` 讀進來的型別是誰決定的。
> 本節不是 SQL 課，也不重教連線、參數化與資源清理——那是 MariaDB 課第 04–13 節。這裡只處理「查詢結果進 pandas」這一步，以及「這件事該由誰做」的判斷。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 範例程式碼

- [demo：04_sql_or_pandas.py](https://github.com/4-learn/data-analysis-and-process-demo/blob/master/2026/04_sql_or_pandas.py)（與本頁 Demo 逐字相同）
- 練習資料與環境說明：[2026/README](https://github.com/4-learn/data-analysis-and-process-demo/tree/master/2026)

## 學習目標與時間

完成後，你能：用 `pd.read_sql` 加參數讀一個查詢；同一題寫出 SQL 版與 pandas 版並證明結果相同；說出何時該先在資料庫篩選、何時該拉進來再處理；指出 `read_sql` 讀進來的空值、型別與佔位符在 SQLite 與 MariaDB 之間哪裡不一樣。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–5 分鐘 | 為什麼這節用 SQLite | 與 `law_articles` 同欄位、同唯一鍵的記憶體資料庫 |
| 5–12 分鐘 | 同一題，兩種做法 | 每部法規條數：9 列 vs 749 列，結果相同 |
| 12–19 分鐘 | 先篩再拉 vs 全拉再篩 | 15 列 vs 749 列，搬運量差 34 倍 |
| 19–26 分鐘 | 字串拼接 vs `params` | 惡意輸入 190 列 vs 0 列 |
| 26–32 分鐘 | `read_sql` 讀進來的型別 | `COUNT` 是 `int64`、`SUM` 變 `float64`、`NULL` 進 pandas 後被 `groupby` 丟掉 |
| 32–35 分鐘 | 換成 MariaDB 時要改什麼 | 佔位符、`UserWarning`、錯誤型別 |
| 35–50 分鐘 | Workshop：選邊，並抓 AI 的錯 | 一題兩解與選擇理由 |

先修：本課第 03 節；MariaDB 課第 09 節（`GROUP BY`、`NULL`）、第 10–13 節（連線、參數化、交易、錯誤處理）；爬蟲課第 16 節（`law_articles`）。環境同第 02 節，**不需要 MariaDB 與任何資料庫驅動**：`sqlite3` 是 Python 標準函式庫。

## 一、為什麼這節用 SQLite

爬蟲課第 16 節把條文寫進 MariaDB 的 `law_articles`：

```text
id, pcode, law_name, slug, article_no, chapter, content, source_url, content_hash, fetched_at, updated_at
UNIQUE KEY uk_article (pcode, slug)
```

不是每台教室 VM 都還開著那顆 MariaDB，也不能假設每個人的資料表內容一樣（有人只載了一部法規、有人補了 `source_version` 欄位）。所以本節的 Demo 用標準函式庫 `sqlite3`，**在記憶體裡**建一張欄位、`NOT NULL`、預設值與唯一鍵都相同的表，載入 `data/articles.jsonl` 的 749 條。不寫檔、不連線，每個人跑出來都一樣。

差別只在型別名稱：SQLite 雖然接受 `VARCHAR(16)`、`DATETIME` 這種寫法，但不檢查長度、也沒有真正的日期型別（實測 `VARCHAR(2)` 欄存得進 6 個字元），所以本節一律寫 `TEXT`。這個差別在第五段會回頭咬人一次。

```text
== 1. 建表、載入 ==
載入 749 列
同一批再載入一次 → IntegrityError: UNIQUE constraint failed: law_articles.pcode, law_articles.slug
之後仍是 749 列
articles.jsonl 有、資料表沒有的欄位：['source_version']
```

- **唯一鍵一樣在把關**：同一批再塞一次，整批被拒絕，表仍是 749 列。Demo 這三列本來就都重複，所以這一行本身證明不了原子性；教師另以「1 列新資料＋這 3 列重複」實測，`with con:` 讓新的那列也一起回滾，表仍是 749 列。這是 MariaDB 課第 12 節的交易原子性，換一顆資料庫一樣成立。
- **`source_version` 不在表裡**：爬蟲課第 16 節的 demo 表沒有這欄，是留給學生在 Workshop 補的。**從資料庫讀，你拿到的是「表上有的欄位」，不是「上游交付的欄位」**——第 03 節要你保留的四個來源欄位，在這裡只剩三個。

## 二、同一題，兩種做法

題目：每部法規有幾條？

```python
# 本節測試不涵蓋這段（節錄自下方 Demo 第二段）
# SQL 做：資料庫算好，只傳 9 列回來
pd.read_sql("SELECT pcode, law_name, COUNT(*) AS n FROM law_articles GROUP BY pcode, law_name ORDER BY pcode", con)

# pandas 做：先把 749 列拉回來，在 Python 裡算
pulled = pd.read_sql("SELECT pcode, law_name FROM law_articles", con)
pulled.groupby(["pcode", "law_name"]).size().reset_index(name="n")
```

```text
== 2. 同一題：每部法規幾條 ==
   pcode     law_name   n
N0020007      勞資爭議處理法  67
N0020012    大量解僱勞工保護法  21
N0030001        勞動基準法  98
N0030014      性別平等工作法  50
N0030020      勞工退休金條例  69
N0050031 勞工職業災害保險及保護法 109
N0060001      職業安全衛生法  61
N0060014   營造安全衛生設施標準 189
N0090001        就業服務法  85
SQL 傳回 9 列；pandas 先拉 749 列再算；兩者 equals：True
```

`equals` 是 `True`：值、欄名、順序、**型別**都一樣（`n` 兩邊都是 `int64`）。注意 SQL 版寫了 `ORDER BY pcode`；`groupby` 預設會依鍵排序，兩邊才剛好對得上。SQL 不寫 `ORDER BY`，**資料庫不保證回傳順序**——比較兩種做法時，先排序再比。

結果一樣，那差在哪？

| | 在資料庫做 | 拉進 pandas 做 |
| --- | --- | --- |
| 搬多少資料 | 只搬結果（9 列） | 搬原料（749 列），結果在本機算 |
| 誰能重現 | 任何能連資料庫、權限夠的人，一條 SQL | 要有同一份程式、同一版 pandas |
| 權限 | 帳號只需要 `SELECT` 那張表的權限；也可以只開一個彙總好的 view | 帳號要能讀明細 |
| 擅長 | 篩選、`JOIN`、`GROUP BY`、有索引的查詢 | 多步驟清理、跨來源合併（CSV＋JSONL＋查詢結果）、時間處理、驗證、序列化給 LLM |
| 資料庫看不到的 | — | 不在資料庫裡的東西：另一份 CSV、API 回應、事件檔 |

一個實用的切法：**能用一條 SQL 說清楚的篩選與彙總，在資料庫做；要跟資料庫以外的東西一起處理、或要一步一步驗證的，拉進 pandas。** 兩種都要能做，因為你常常需要用一邊驗證另一邊——Workshop 就是這樣做。

## 三、先篩再拉 vs 全拉再篩

LLM 組要「營造安全衛生設施標準裡提到『墜落』的條文」。AI 常見的寫法是先 `SELECT *` 拉回來，再用 pandas 篩：

```text
== 3. 先篩再拉 vs 全拉再篩 ==
全拉          749 列 × 11 欄  約 547,105 位元組
全拉再篩（結果）     15 列 ×  4 欄  約  16,211 位元組
先篩再拉         15 列 ×  4 欄  約  16,211 位元組
兩種做法結果 equals：True；全拉多搬了 34 倍
```

（「位元組」是每一格轉成文字後的 UTF-8 長度加總，用來比較搬運量的相對大小，不是網路封包的實際大小。）

- **答案相同**，`equals` 為 `True`。所以這不是對錯問題，是代價問題。
- **全拉多搬了 34 倍**。749 條是很小的表；換成第 01 節的事件表、或一年份的資料，這個倍數就是網路、記憶體與等待時間。
- `SELECT *` 還有一個不明顯的代價：**你拿到了你沒打算用的欄位**。`content_hash`、`updated_at` 進了 DataFrame，之後有人 `to_json` 交給 LLM，它們就跟著出去了（第 16 節的預算問題）。先篩再拉時，**欄位也一起篩**。

什麼時候「全拉」反而對？資料量小、而且你接下來要對同一份資料做很多種不同的切法（例如第 06 節的探索）——拉一次、在本機切十次，比對資料庫查十次合理。**判斷依據是「結果會被用幾次、資料有多大」，不是習慣。**

## 四、字串拼接 vs `params`

AI 最常給的「先篩再拉」長這樣：

```python
# 本節測試不涵蓋這段（錯誤示範；同一寫法即 Demo 的 naive_find()）
sql = f"SELECT pcode, slug, content FROM law_articles WHERE pcode = '{pcode}' AND content LIKE '%{keyword}%'"
pd.read_sql(sql, con)
```

正常輸入時完全正確。換三種輸入：

```text
== 4. 字串拼接 vs params ==
正常輸入    拼接 → 15 列                                    params → 15 列
惡意輸入    拼接 → 190 列                                   params → 0 列
帶引號的輸入  拼接 → DatabaseError（unrecognized token: "'"）  params → 0 列
```

- **惡意輸入** `N0060014' OR '1'='1`：拼進去之後 SQL 變成 `pcode = 'N0060014' OR '1'='1' AND content LIKE ...`，`AND` 先結合，於是**營造安全衛生設施標準 189 條全部**加上其他法規提到墜落的 1 條，回傳 190 列。**沒有任何錯誤**，你只會覺得「這次結果比較多」。
- **帶引號的輸入** `N0060014'`：SQL 語法壞掉，`read_sql` 拋 `pandas.errors.DatabaseError`。這是爬蟲課第 16 節說的「條文內容有單引號就壞掉」。
- **用 `params`**：值和 SQL 分開送，`N0060014' OR '1'='1` 只是一個「剛好很奇怪的 pcode」，找不到就是 0 列。這與爬蟲課第 16 節在 MariaDB 上的實測結果（`(0,)`）一致。

Demo 的 `find_articles()` 有三個細節，換到 MariaDB 一樣適用：

1. **`LIKE` 的 `%` 放在參數值裡**（`f"%{keyword}%"`），SQL 只寫 `LIKE ?`。不要寫 `LIKE '%?%'`——引號裡的 `?` 是普通字元，不是佔位符；實測在 SQLite 會直接報「需要 1 個參數、給了 2 個」。也不要用 `'%' || ? || '%'`：SQLite 的 `||` 是字串串接，**MariaDB 預設把 `||` 當成 `OR`**（除非開了 `PIPES_AS_CONCAT`），同一句 SQL 換一顆資料庫就變成另一個意思。
2. **欄名不能當參數**，只能從白名單挑（`COLUMNS`）。MariaDB 課第 11 節講過：參數只能放值，不能代替表名或欄名。
3. 參數化**不處理** `LIKE` 本身的萬用字元：使用者輸入 `%` 會變成「全部符合」（實測 `find_articles(con, "N0060014", "%")` 回 189 條）。如果關鍵字來自使用者，這是你要另外處理的事；本節只標出來，不展開。

## 五、`read_sql` 讀進來的型別

`read_json` 讀檔時是 pandas 在猜型別（第 03 節）；`read_sql` 不一樣，**型別大部分是資料庫驅動決定的**，pandas 只是把驅動交出來的 Python 值裝進欄位。

```text
== 5. read_sql 讀進來的型別 ==
law_name=str, n=int64, avg_len=float64, no_chapter=float64, fetched_at=str
    law_name   n    avg_len  no_chapter                fetched_at
  營造安全衛生設施標準 189 163.936508         NaN 2026-10-05T04:05:23+00:00
勞工職業災害保險及保護法 109 174.238532         NaN 2026-10-05T04:05:23+00:00
       勞動基準法  98 146.438776         NaN 2026-10-05T04:05:23+00:00
no_chapter 非空的只有：['大量解僱勞工保護法']
chapter 空字串 21 列；NULLIF 之後 NaN 21 列
groupby 預設 728 列；dropna=False 749 列
查無資料：0 列，pcode=object, n=object
```

逐欄看：

- **`COUNT(*)` → `int64`**。沒問題。
- **`SUM(CASE WHEN chapter = '' THEN 1 END)` → `float64`**。這欄本來是「沒有分章的條數」，是整數；但 9 部法規裡有 8 部算出來是 `NULL`（`SUM` 對全是 `NULL` 的組回 `NULL`，不是 0），pandas 只好把 `NULL` 變 `NaN`，整欄就變成浮點數。**跟第 02 節「空欄變 `float64`」是同一件事，只是這次是 SQL 造成的。** 要 0 就在 SQL 寫 `COALESCE(SUM(...), 0)` 或 `COUNT(CASE ...)`。
- **`fetched_at` → `str`**。SQLite 沒有日期型別，存什麼就讀回什麼。換到 MariaDB，`fetched_at` 是 `DATETIME`，驅動會交出 Python `datetime`，pandas 讀成 `datetime64`——而且**沒有時區**（MariaDB 的 `DATETIME` 不含時區資訊，依官方文件）。爬蟲課第 16 節要求的「ISO 8601 帶時區」，寫進 `DATETIME` 那一刻就沒了。這一點本節沒有在 MariaDB 上實測，見第六段。
- **空字串 vs `NULL`**：`chapter` 在表裡是 `NOT NULL DEFAULT ''`，大量解僱勞工保護法的 21 條是**空字串**，讀進來還是空字串。但只要有人在 SQL 裡寫了 `NULLIF(chapter, '')`（或者上游把空值存成 `NULL`），進 pandas 就變成 `NaN`，而 **`groupby` 預設把 `NaN` 那一組整個丟掉**：749 列變 728 列，沒有任何警告。`dropna=False` 才拿得回來。SQL 的 `GROUP BY` 會保留 `NULL` 那一組——**同一份資料，SQL 和 pandas 在這裡給的答案不一樣**。
- **查無資料**：參數查不到任何列時，`n` 是 `object` 而不是 `int64`——沒有任何一個值可以讓 pandas 推斷型別，SQLite 也不會告訴它「這欄應該是整數」。下游若寫 `df["n"].sum()` 不會出錯，但若拿去跟另一張表 `concat`，型別會被拖垮。**查無資料要當成一種要處理的結果，不是「空的就算了」。**

### 完整 Demo

以下為完整 `04_sql_or_pandas.py`，只讀 `data/articles.jsonl`，資料庫建在記憶體裡，不寫檔、不連線。

<!-- demo: 04_sql_or_pandas.py -->
```python
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
```

執行（在本目錄下）：

```bash
python3 04_sql_or_pandas.py
```

## 六、換成 MariaDB 時要改什麼

教室有 MariaDB 時，連線沿用 MariaDB 課第 10、13 節（受限帳號、設定檔不進版控、`closing()` 管理生命週期），本節不重教。**以下這段本節測試不涵蓋**，也沒有在本機的 MariaDB 上實際執行（本環境沒有 MariaDB 伺服器與 `mariadb` 驅動）；能驗證的部分已分別標出驗證方式。

```python
# 本節測試不涵蓋這段：需要 MariaDB 伺服器與 mariadb==1.1.14（MariaDB 課第 10 節）
import warnings
from contextlib import closing

import mariadb
import pandas as pd

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy", category=UserWarning)

SQL = ("SELECT pcode, slug, article_no, content FROM law_articles "
       "WHERE pcode = ? AND content LIKE ? ORDER BY id")

with closing(mariadb.connect(user=..., password=..., database=..., unix_socket=...)) as con:  # 依 MariaDB 課第 10 節的設定檔
    df = pd.read_sql(SQL, con, params=("N0060014", "%墜落%"))
```

與 SQLite 版的差異：

| 項目 | SQLite（本節 Demo） | MariaDB Connector/Python | 怎麼確認的 |
| --- | --- | --- | --- |
| 佔位符 | `?` | **`?`**（`paramstyle = 'qmark'`）；`%s` 也接受 | `mariadb` 1.1.14 原始碼 `mariadb/dbapi20.py` 寫 `paramstyle = 'qmark'`，`cursors.py` 另有 FORMAT／PYFORMAT 的處理；MariaDB 課第 11 節、爬蟲課第 16 節皆以 `?` 實測。sqlite3 用 `%s` 實測會報語法錯誤 |
| `read_sql` 會不會警告 | 不會 | **每次呼叫都發 `UserWarning`**：`pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.` | 讀 pandas 3.0.6 `pandas/io/sql.py` 的 `pandasSQL_builder()`：只有 `sqlite3.Connection`、SQLAlchemy、ADBC 不警告，其他 DBAPI 物件一律警告後**照 sqlite3 的方式執行**。另用一個不是 `sqlite3.Connection` 的假 DBAPI 物件實測，3.0.6 與 2.3.3 都發出、查詢結果正確 |
| 查詢失敗時的例外 | `pandas.errors.DatabaseError` | **pandas 3.0.6：驅動自己的例外原樣拋出**（例如 `mariadb.ProgrammingError`），pandas **不會**替你 `rollback`；2.3.3：包成 `pandas.errors.DatabaseError` 並呼叫一次 `con.rollback()` | 讀原始碼：3.0.6 的 `SQLiteDatabase.execute()` 只捕捉 `sqlite3.Error`，2.3.3 捕捉所有 `Exception`。用假 DBAPI 物件實測：3.0.6 拋原本的例外、`rollback` 0 次；2.3.3 拋 `DatabaseError`、`rollback` 1 次 |
| `DATETIME` 欄 | `TEXT`，讀回字串 | 驅動交出 `datetime`，pandas 讀成無時區的 `datetime64[us]`（2.3.3 是 `[ns]`） | pandas 這一半用假物件實測；**驅動會交出 `datetime` 未實測**（依 PEP 249 推論） |
| `AVG()`、`DECIMAL` 欄 | `float64` | 驅動交出 `Decimal`；`read_sql` 預設 `coerce_float=True` 會轉成 `float64`，設 `False` 則留在 `object` | pandas 這一半用假物件實測；驅動回 `Decimal` 未實測 |
| `LENGTH()` | 字元數（`'墜落'` → 2） | **位元組數**（utf8mb4 中文一字 3 位元組）；要字元數用 `CHAR_LENGTH()` | SQLite 實測；MariaDB 依官方文件，未實測 |
| `||` | 字串串接 | 預設是 `OR` | MariaDB 官方文件，未實測 |

三個實際影響：

1. **警告不是錯誤，但不要讓它淹掉別的警告。** 上面的 `filterwarnings` 只針對這一句訊息，不要寫成 `warnings.simplefilter("ignore")` 全關——第 03 節的 `Pandas4Warning` 你還要看得到。若教室環境裝了 SQLAlchemy，改傳 engine 就沒有這個警告；本課不要求安裝 SQLAlchemy。
2. **錯誤處理要接驅動的例外。** pandas 3 下，`except pd.errors.DatabaseError` **接不到** MariaDB 的查詢錯誤。沿用 MariaDB 課第 13 節：接 `mariadb.Error`，保留真正的錯誤，不用 `except: pass` 隱藏問題。只讀的查詢不需要 `rollback`，但若同一條連線前面還有未提交的寫入，pandas 3 不會替你處理。
3. **不想要警告、也不想依賴 pandas 對其他驅動的「未測試」行為**，就自己用 cursor 取：`cur.execute(SQL, params)` 後 `pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])`。這也是 MariaDB 課的寫法，型別一樣由驅動決定；但它**不會**像 `read_sql` 預設的 `coerce_float=True` 那樣把 `Decimal` 轉成 `float64`，`DECIMAL` 欄會留在 `object`（這個寫法本機以 sqlite3 實測，`Decimal` 以 sqlite3 自訂轉換器模擬）。

## Workshop：選邊，並抓 AI 的錯

### 任務與時間

**35–42 分鐘：一題兩解。** 題目：「每部法規最長的一條有幾個字？」

1. 用 SQL 寫一次（提示：`GROUP BY`、`MAX`、SQLite 的 `LENGTH`）。
2. 拉 `pcode, content` 進 pandas 再寫一次。
3. 用 `equals` 證明兩邊一樣；不一樣就找出原因。
4. 寫一句話：這題你會選哪一邊？如果資料庫是 MariaDB，SQL 版要改什麼？

**42–46 分鐘：`NULL` 這一組去哪了。** 在 SQL 和 pandas 各做一次「每部法規、每一章各幾條」，章名用 `NULLIF(chapter, '')`。比較兩邊的列數與總條數。

**46–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫：「寫一個函式 `search(con, pcode, keyword)`，從 `law_articles` 找某部法規裡含關鍵字的條文，回傳 DataFrame。」拿它的程式驗收：

1. 用 Demo 第四段的三種輸入各呼叫一次，結果是不是 15／0／0 列？
2. 它是先篩再拉，還是 `SELECT *` 全拉再篩？傳回幾欄？
3. `LIKE` 的 `%` 寫在哪裡？換到 MariaDB 還成不成立？
4. 傳入 `keyword="%"` 會回幾列？

### 參考判讀

- 一題兩解（教師實測）：SQL `SELECT pcode, MAX(LENGTH(content)) AS max_len FROM law_articles GROUP BY pcode ORDER BY pcode` 與 pandas `content.str.len()` 後 `groupby("pcode", as_index=False)["max_len"].max()`，`equals` 為 `True`，兩邊 `max_len` 都是 `int64`。最長的是 `N0060014` 的 935 字，與第 16 節「本資料最長一條 935 字」一致。
  - **換到 MariaDB 會出錯**：`LENGTH()` 在 MariaDB 是位元組數，中文條文會變成約 3 倍，`equals` 變 `False`。要改成 `CHAR_LENGTH()`。（MariaDB 依官方文件，未在本機實測。）這正是「用一邊驗證另一邊」抓得到的錯。
  - 選擇：這題兩邊都很短。資料在資料庫、只要結果，用 SQL；若接下來還要跟 CSV 合併或做驗證，拉進 pandas。理由說得出來就算對。
- `NULL` 這一組（教師實測）：SQL `GROUP BY pcode, chapter` 回 76 組、合計 749 條；pandas `groupby(["pcode", "chapter"])` 預設回 75 組、合計 728 條，`dropna=False` 才是 76 組、749 條。少掉的 21 條就是大量解僱勞工保護法——沒有分章，不是不存在。
- 抓 AI 的錯：
  - 字串拼接版：惡意輸入回 190 列、帶引號輸入拋 `DatabaseError`（Demo 第四段實測）。
  - 寫成 `LIKE '%?%'`：參數個數對不上，SQLite 報錯（教師實測）；如果它只傳一個參數，則 `'%?%'` 是在找含問號的條文，回 0 列——**不報錯，只是找不到**。
  - 寫成 `'%' || ? || '%'`：在 SQLite 正確，到 MariaDB 預設變成 `OR`（依官方文件）。
  - `keyword="%"`：參數化版本回 189 列（教師實測）。參數化擋住的是 SQL 注入，不是 `LIKE` 萬用字元。

### 驗收

- 能重現 Demo 五段輸出，並說明第二段為什麼要寫 `ORDER BY`。
- 一題兩解的 `equals` 為 `True`，並寫出 MariaDB 版要把 `LENGTH` 換成什麼、為什麼。
- 說出 `NULLIF` 之後 SQL 與 pandas 為什麼差 21 條，以及用哪個參數拿回來。
- AI 版本四項檢查都有結論；若它用了字串拼接，指出哪一個輸入會讓它多回資料而不報錯。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8（內建 SQLite 3.31.1），pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3（SQLite 3.31.1）執行，差別只有一行：第五段字串欄 dtype 顯示為 `object` 而非 `str`（`law_name=object, …, fetched_at=object`）。其餘逐字相同，包括「查無資料」那一行在兩版都是 `object`。

**pandas 版本差異（非 Demo 輸出，教師以假 DBAPI 物件與原始碼確認）**：非 sqlite3 連線的 `UserWarning` 在 3.0.6 與 2.3.3 訊息相同；查詢失敗時 3.0.6 拋驅動原本的例外、不 `rollback`，2.3.3 包成 `pandas.errors.DatabaseError` 並 `rollback` 一次。這會影響學生的 `except` 寫法，**若教室退回 pandas 2.3，第六段第 2 點要改寫**。

**MariaDB 部分的證據等級**：第六段的 MariaDB 程式碼**待驗證**——本環境沒有 MariaDB 伺服器、沒有 `mariadb` 驅動、也沒有 SQLAlchemy。`paramstyle = 'qmark'` 依 `mariadb-connector-python` v1.1.14 原始碼（2026-10-05 查閱）；`LENGTH` 為位元組數、`||` 預設為 `OR` 依 MariaDB 官方文件（2026-10-05 查閱）；`?` 佔位在 MariaDB 課第 11 節、爬蟲課第 16 節有實測紀錄。開課前應在教室 VM 上實跑一次第六段並補上實測輸出。

**資料**：資料表結構取自爬蟲課第 16 節 `law_articles`（欄位、`NOT NULL`、`DEFAULT ''`、`UNIQUE (pcode, slug)` 相同；型別改為 SQLite 的 `TEXT`／`INTEGER`）。內容為 `data/articles.jsonl` 749 條，取自爬蟲課練習站，可能經刻意修改，**不具法律效力**。`updated_at` 是載入當下的時間，每次執行都不同，所以 Demo 不印出它。

**界線**：本節不教 SQLAlchemy、連線池、`chunksize` 分批讀取、`to_sql` 寫回資料庫。位元組數是「每格轉文字後的 UTF-8 長度」，用來比較兩種做法的相對大小，不是網路傳輸量的實測。**`read_excel` 不納入本節**：課綱第 02 節把它移出、去處未定（04 或附錄）；本節主題是「該在哪一層做」，Excel 的日期序號、合併儲存格、多工作表跟這個判斷無關，**建議放附錄**。本節**尚未實班試教**。

**舊教材**：無對應舊講義（舊版宣告「本課不教 Database / SQL」，`read_sql` 全課 0 次）；本節為新增，**取代該宣告**。

**下一節**：第 05 節〈一筆事件 = 一列；欄位是 schema〉——前四節都在讀條文（文件）；從下一節開始換成第 01 節的工地事件，先建立「一列是什麼、一欄負責什麼」的心智模型。
