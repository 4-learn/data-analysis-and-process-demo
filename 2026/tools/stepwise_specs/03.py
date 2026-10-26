LESSON = "03-read-jsonl.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "接手爬蟲課的 JSONL 與 API 的巢狀 JSON，一路保留四個來源欄位。"
GOALS = [
    ("0–16 分", "零、一", "看出一行 `read_json` 再存回去，21 列被改寫"),
    ("16–22 分", "二", "讀 JSONL 不讓 pandas 猜，並檢查來源欄位"),
    ("22–30 分", "三", "照 `next` 走完分頁，攤平巢狀 JSON"),
    ("30–35 分", "四", "兩個來源互相核對"),
    ("35–50 分", "Workshop", "全量 749 條＋回溯檢查"),
]
OVERVIEW = [
    'W[("練習站")] --> J[("爬蟲課交付<br/>N0020012.jsonl 21 行")]',
    'W --> P[("API 分頁<br/>page-1・page-2")]',
    'J --> N["一 一行 read_json ✗"]',
    'J --> R["二 read_jsonl()<br/>＋來源檢查"]',
    'P --> F["三 flatten_api()<br/>照 next 走完"]',
    'R --> M["四 merge 核對<br/>21 條雜湊全同"]', 'F --> M',
    'style N fill:#fde2e1,stroke:#c0392b',
    'style M fill:#ddf3e4,stroke:#27ae60,stroke-width:3px',
]
OVERVIEW_DIR = "TD"
SECTIONS = [
    dict(title="零、準備：檔案與四個來源欄位", short="準備",
         question="爬蟲課交過來的每一筆，帶了什麼？",
         steps=['A["source_url：從哪裡來"]', 'B["fetched_at：什麼時候抓的"]',
                'C["content_hash：內容有沒有變"]', 'D["source_version：網站哪一版"]',
                'A ~~~ C', 'B ~~~ D'],
         code=[(3, 13)],
         points=["這四欄不能加總、不能分組，所以最常在這一層被丟掉。",
                 "**一旦丟掉，LLM 就無法附出處，也沒人能判斷資料新不新。**"]),
    dict(title="一、一行 `read_json`，再存回去", short="一行 read_json",
         question="讀進來、什麼都不改、存回去，檔案還一樣嗎？",
         steps=['A["read_json(lines=True)"] --> B["slug：字串 1 → int64"]',
                'A --> C["fetched_at：欄名結尾 _at → 自動轉日期"]',
                'B --> D["to_json()"]', 'C --> D', 'D --> E(["✗ 21 列全被改寫<br/>時間變成毫秒數"])'],
         code=[(58, 67)], out=[1],
         extra="""| 欄名 | 會被自動轉成日期嗎 |
| --- | --- |
| 結尾 `_at`、`_time`；開頭 `timestamp` | 會 |
| 就叫 `modified`、`date`、`datetime` | 會 |
| `updated`、`created_date`、`published` | 不會 |""",
         points=["同樣是時間欄，有的被轉、有的不被轉，**只看名字**。"]),
    dict(title="二、先決定型別，再讀", short="read_jsonl",
         question="正確的讀法？讀完要檢查什麼？",
         steps=['A["read_json(lines=True,<br/>dtype=False, convert_dates=False)"] --> B["check_provenance()"]',
                'B --> C{"四欄都在、不空、<br/>帶時區、雜湊相符？"}', 'C -- 否 --> X(["✗ ValueError"])',
                'C -- 是 --> D(["✓ 原樣保留"])'],
         code=[(16, 36), (69, 72)], out=[2],
         extra="""| 寫法 | `slug` | `fetched_at`（3.0.6） | `fetched_at`（2.3.3） |
| --- | --- | --- | --- |
| 只寫 `dtype=False` | `str` | `str` | `datetime64` ✗ |
| 只寫 `convert_dates=False` | `int64` ✗ | `str` | `object` |
| **兩個都寫** | `str` | `str` | `object` |""",
         points=["兩個參數要一起寫，才不依賴 pandas 版本。",
                 "雜湊對不上 = 檔案在交付後被改過，不該當原始資料往下送。"]),
    dict(title="三、API 的巢狀 JSON", short="flatten_api",
         question="一頁一個物件、條文在裡面一層，怎麼攤平？",
         steps=['A["read_json(page-1)"] --> A1(["✗ 20 列，articles 欄裝 dict<br/>不會告訴你還有下一頁"])',
                'B["flatten_api()"] --> C{"這頁走過了？"}', 'C -- 是 --> X(["✗ next 形成迴圈"])',
                'C -- 否 --> D["json_normalize(record_path, meta)<br/>補上 source_url"]',
                'D --> E{"next 是 None？"}', 'E -- 否 --> C', 'E -- 是 --> G{"列數 = total？"}',
                'G -- 否 --> X2(["✗ ValueError"])', 'G -- 是 --> H(["✓ 21 列"])'],
         code=[(39, 55), (74, 78)], out=[3],
         points=["`record_path`：一列是什麼；`meta`：外層要帶下來的欄位。",
                 "API 回應沒有 `source_url`：補上**真正取得這筆資料的網址**。"]),
    dict(title="四、兩個來源互相核對", short="核對",
         question="網頁抓的和 API 抓的，是同一份內容嗎？",
         steps=['A["crawl（JSONL）"] --> M["merge(on=(pcode, slug),<br/>validate=one_to_one)"]',
                'B["api（攤平後算雜湊）"] --> M', 'M --> C(["✓ 21 條對上，雜湊全同"])'],
         code=[(80, 85)], out=[4],
         points=["`validate=\"one_to_one\"`：任一邊鍵重複就報錯（第 14 節）。",
                 "第 21 條有兩個來源網址：條文頁與 API 第 2 頁，兩個都是真的。"]),
]
