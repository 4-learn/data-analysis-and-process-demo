LESSON = "04-sql-or-pandas.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "同一份條文放在資料庫裡：哪些事在 SQL 做、哪些拉進 pandas 做。"
GOALS = [
    ("0–12 分", "零～二", "同一題寫 SQL 版與 pandas 版，證明結果相同"),
    ("12–19 分", "三", "說出先篩再拉、全拉再篩的代價"),
    ("19–26 分", "四", "用 `params`，不拼字串"),
    ("26–35 分", "五、MariaDB", "說出 `read_sql` 的型別由誰決定；換 MariaDB 改什麼"),
    ("35–50 分", "Workshop", "一題兩解、抓 AI 的錯"),
]
OVERVIEW = [
    'J[("articles.jsonl 749 條")] --> B["一 build_db()<br/>記憶體 SQLite"]',
    'B --> S1["二 SQL 算 vs pandas 算"] --> S2["三 先篩再拉"]',
    'B --> S3["四 params vs 拼接"] --> S4["五 read_sql 的型別"]',
    'S4 -.-> M["補充：換成 MariaDB"]',
]
OVERVIEW_DIR = "TD"
SECTIONS = [
    dict(title="零、準備：資料表與欄位白名單", short="準備",
         question="為什麼這節用 SQLite？",
         steps=['A["教室 MariaDB<br/>每人內容不一樣、不一定開著"]', 'B["SQLite 記憶體資料庫<br/>欄位・唯一鍵相同"] --> C(["✓ 每個人跑出來一樣"])',
                'A ~~~ B'],
         code=[(3, 28), (72, 74)],
         points=["型別一律 `TEXT`：SQLite 不檢查長度、沒有日期型別。",
                 "`INSERT` 裡拼的只有**欄名**（程式自己的常數），值一律是 `?`。"]),
    dict(title="一、建表、載入", short="建表",
         question="唯一鍵在 SQLite 也會把關嗎？",
         steps=['A["build_db()"] --> B{"9 欄都在？"}', 'B -- 否 --> X(["✗ ValueError"])',
                'B -- 是 --> C["connect(:memory:)・CREATE TABLE"] --> D["load()：with con 一批寫入"]',
                'D --> E["再載入同一批"] --> E1(["✓ IntegrityError，整批回滾，仍 749 列"])',
                'D --> G(["✗ source_version 不在表上"])'],
         code=[(31, 44), (76, 83)], out=[1],
         points=["從資料庫讀，拿到的是「**表上有的欄位**」，不是上游交付的欄位。"]),
    dict(title="二、同一題，兩種做法", short="SQL vs pandas",
         question="每部法規幾條：SQL 算和 pandas 算，結果一樣嗎？",
         steps=['A["SQL：GROUP BY ... ORDER BY"] --> A1["傳回 9 列"]',
                'B["pandas：拉 749 列 → groupby().size()"] --> B1["本機算出 9 列"]',
                'A1 --> C(["✓ equals：True"])', 'B1 --> C'],
         code=[(85, 91)], out=[2],
         extra="""| | 在資料庫做 | 拉進 pandas 做 |
| --- | --- | --- |
| 搬多少 | 只搬結果 | 搬原料 |
| 擅長 | 篩選、JOIN、GROUP BY | 多步驟清理、跨來源合併、驗證、序列化 |
| 看不到 | 資料庫以外的資料 | — |""",
         points=["比較兩種做法要先排序：SQL 不寫 `ORDER BY`，**順序不保證**。"]),
    dict(title="三、先篩再拉 vs 全拉再篩", short="先篩再拉",
         question="同樣的答案，搬了多少資料？",
         steps=['A["SELECT * 全拉 749 列"] --> B["pandas 篩"] --> B1(["✗ 搬了 34 倍"])',
                'C["find_articles()<br/>WHERE pcode = ? AND content LIKE ?"] --> C1(["✓ 只拉 15 列 4 欄"])',
                'B1 --> D(["equals：True"])', 'C1 --> D'],
         code=[(47, 54), (63, 65), (93, 100)], out=[3],
         points=["不是對錯，是**代價**：結果用幾次、資料多大，決定先篩還是全拉。"]),
    dict(title="四、字串拼接 vs `params`", short="params",
         question="AI 把值拼進 SQL，會怎樣？",
         steps=['A["naive_find()<br/>f-string 拼值"] --> A1(["✗ 惡意輸入：190 列，不報錯"])',
                'A --> A2(["✗ 帶引號：語法錯誤"])',
                'B["find_articles()<br/>值用 ?，欄名白名單"] --> B1(["✓ 惡意輸入：0 列"])'],
         code=[(57, 60), (102, 109)], out=[4],
         points=["`LIKE` 的 `%` 放在**值**裡；`'%' || ? || '%'` 到 MariaDB 會變成 `OR`。",
                 "參數化擋注入，不擋萬用字元：`keyword=\"%\"` 回 189 條。"]),
    dict(title="五、`read_sql` 讀進來的型別", short="型別",
         question="`read_sql` 的型別是誰決定的？",
         steps=['A["COUNT(*)"] --> A1(["int64"])', 'B["SUM(CASE ...)：8 部是 NULL"] --> B1(["✗ float64"])',
                'C["NULLIF(chapter, \'\')"] --> D["groupby()"] --> D1(["✗ NULL 組被丟：728 列"])',
                'D --> D2(["✓ dropna=False：749 列"])', 'E["查無資料"] --> E1(["object"])'],
         code=[(68, 69), (111, 124)], out=[5],
         points=["型別大部分由**資料庫驅動**決定，pandas 只是裝進欄位。",
                 "SQL `GROUP BY` 保留 NULL 組；pandas `groupby` 預設丟掉。"]),
]
MIDDLE_KEEP = ["七、換成 MariaDB 時要改什麼"]
MIDDLE_REPLACE = [
    ("## 七、換成 MariaDB 時要改什麼\n\n連線沿用 MariaDB 課第 10、13 節（受限帳號、設定檔不進版控、`closing()` 管理生命週期），本節不重教。\n",
     """## 補充：換成 MariaDB 時要改什麼

**問題：** 同一支程式改連教室的 MariaDB，哪些地方不一樣？

```mermaid
flowchart TD
    A["mariadb.connect()<br/>（MariaDB 課第 10 節）"] --> B["pd.read_sql(SQL, con, params=)<br/>寫法與 SQLite 版相同"]
    B --> C(["每次都發 UserWarning"])
    B --> D(["pandas 3：錯誤是 mariadb.ProgrammingError"])
    B --> E(["LENGTH 是位元組數、|| 是 OR"])
    classDef bad fill:#fde2e1,stroke:#c0392b
    class C,D,E bad
```
"""),
    ("""| 行 | 做什麼 |
| --- | --- |
| `warnings.filterwarnings(...)` | 只關掉 pandas 對非 sqlite3 連線的那一句警告，其他警告照常顯示 |
| `SQL = ...` | 與 SQLite 版相同；MariaDB 一樣用 `?` 佔位 |
| `closing(mariadb.connect(...))` | 離開 `with` 時一定關連線 |
| `pd.read_sql(SQL, con, params=...)` | 與 SQLite 版相同的呼叫方式 |

""", ""),
]
