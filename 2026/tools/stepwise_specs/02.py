LESSON = "02-read-files.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "三份不同來源的 CSV 讀成一張表。一行 `read_csv` 讓 pandas 猜型別，猜錯不會報錯。"
GOALS = [
    ("0–8 分", "一", "看出一行 `read_csv` 一份報錯、兩份「成功」"),
    ("8–18 分", "二", "說出「成功」的兩份錯在哪：型別漂移、1970"),
    ("18–35 分", "零、三", "先決定型別再讀；讀整個資料夾並驗證"),
    ("35–50 分", "Workshop", "第四份檔、抓 AI 的錯"),
]
OVERVIEW = [
    'A[("labor-standards.csv<br/>UTF-8＋BOM・98 條")] --> N["一 一行 read_csv"]',
    'B[("mass-layoff.csv<br/>UTF-8・21 條")] --> N',
    'C[("labor-disputes.csv<br/>Big5・67 條")] --> N',
    'N --> P["二 合起來：錯在下游"]',
    'A --> R["三 read_folder()<br/>先決定型別"]', 'B --> R', 'C --> R',
    'R --> T(["一張表 186 列"])',
    'style P fill:#fde2e1,stroke:#c0392b',
    'style R fill:#ddf3e4,stroke:#27ae60,stroke-width:3px',
]
OVERVIEW_DIR = "TD"
SECTIONS = [
    dict(title="零、準備：欄位與編碼白名單", short="準備",
         question="讀檔前先定好什麼？",
         steps=['A["REQUIRED：七個必要欄位"]', 'B["ENCODINGS：utf-8-sig → cp950<br/>只試這兩種"]',
                'C["detect_encoding()"] --> D{"整份檔解得開？"}', 'D -- 第一個成功 --> E(["✓ 用它"])',
                'D -- 都不行 --> X(["✗ ValueError：去問資料提供者"])', 'A ~~~ C'],
         code=[(3, 9), (22, 30)],
         extra="""| 檔案 | 誰匯出的 | 編碼 |
| --- | --- | --- |
| `labor-standards.csv` | 人資用 Excel 另存 | UTF-8，開頭有 BOM |
| `mass-layoff.csv` | 工程師用程式匯出 | UTF-8 |
| `labor-disputes.csv` | 十年前的舊系統 | Big5（cp950） |""",
         points=["白名單是**排除法**：不在名單就停，不用 `errors=\"replace\"` 把字換成 `�`。"]),
    dict(title="一、一行 `read_csv`：一份報錯，兩份「成功」", short="一行 read_csv",
         question="AI 給的 `pd.read_csv(path)`，三份讀起來怎樣？",
         steps=['A["naive_read()<br/>pd.read_csv(path)"] --> B["Big5 那份"] --> B1(["✓ UnicodeDecodeError：知道錯在哪"])',
                'A --> C["勞基法"] --> C1(["slug 是 str"])',
                'A --> D["大量解僱法"] --> D1(["✗ slug 是 int64<br/>chapter 是 float64"])'],
         code=[(12, 19), (58, 62)], out=[1],
         points=["**報錯的那份反而最安全。**",
                 "同一欄，pandas 依內容猜成不同型別，沒有任何錯誤訊息。"]),
    dict(title="二、「成功」的代價：錯在下游才爆", short="錯在下游",
         question="兩份「成功」的合起來會怎樣？",
         steps=['A["concat 兩份"] --> B["slug：字串 1 和整數 1 混在一欄"] --> B1(["✗ slug == 1 只找到一筆"])',
                'C["modified_date 20150701（整數）"] --> D["pd.to_datetime()"] --> D1(["✗ 1970-01-01，不報錯"])'],
         code=[(64, 69)], out=[2],
         extra="""| 錯誤 | 在哪裡爆 | 會報錯嗎 |
| --- | --- | --- |
| 編碼不對 | `read_csv` 當下 | 會 |
| `slug` 型別漂移 | 篩選、`merge`、去重 | 不會，只是少資料 |
| 空欄變 `float64` | 字串操作、匯出 | 有時會 |
| 日期被當整數 | 時間彙總 | 不會，變 1970 |""",
         points=["**型別是讀進來時決定的，不是之後才修的。**"]),
    dict(title="三、先決定型別，再讀", short="read_folder",
         question="正確的讀法？",
         steps=['A["read_export()"] --> B["detect_encoding()"] --> C["read_csv(dtype=str, keep_default_na=False)"]',
                'C --> D{"七欄都在？"}', 'D -- 否 --> X1(["✗ ValueError：缺哪欄"])',
                'D -- 是 --> E["to_datetime(format=%Y%m%d)"] --> G["加上 source_file・read_encoding"]',
                'H["read_folder()"] --> I["sorted(glob(*.csv))"] --> J["每份 read_export()"] --> K["concat"]',
                'K --> L{"(pcode, slug) 重複？"}', 'L -- 是 --> X2(["✗ ValueError"])', 'L -- 否 --> M(["✓ 186 列"])'],
         code=[(33, 54), (71, 75)], out=[3],
         extra="""| 規則 | 寫法 |
| --- | --- |
| 全部先當字串 | `dtype=str` |
| 空格保持空字串 | `keep_default_na=False` |
| 日期給明確格式 | `format="%Y%m%d"` |
| 編碼只試白名單 | `detect_encoding()` |
| 每列記下來源 | `source_file`、`read_encoding` |""",
         points=["`chapter` 空字串 21 筆＝大量解僱法沒有分章，**是事實，不是缺值**。",
                 "`glob` 不保證順序：一律 `sorted()`。"]),
]
MIDDLE_KEEP = []
APPEND_MIDDLE = """## 補充：為什麼不用自動偵測編碼套件？

| 做法 | 猜錯時 | 本節的選擇 |
| --- | --- | --- |
| `chardet`、`charset-normalizer` 自動猜 | Big5 與 GBK 容易互相誤判；讀出另一套中文字，**不報錯** | 不用 |
| 白名單（`detect_encoding()`） | 不在白名單就停下來問人 | ✅ 採用 |
"""
