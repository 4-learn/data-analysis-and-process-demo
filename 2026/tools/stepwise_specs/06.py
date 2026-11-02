LESSON = "06-event-row.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "一筆事件 = 一列；一批事件一次變一張表。不是 DataFrame API 導覽，也不是 list／dict 複習。"
DEMO_SUMMARY = "一事件一表、迴圈 concat、一次建表、Series 與 index"
GOALS = [
    ("0–5 分", "一", "說出二維 list 為什麼沒有欄名"),
    ("5–21 分", "二、三", "指出兩種錯寫法為什麼之後沒辦法 `groupby`"),
    ("21–27 分", "四", "一次把 list of dict 變成表並計數"),
    ("27–35 分", "五、六", "`groupby` 後 `reset_index(name=)`；`set_index` 前先查唯一"),
    ("35–50 分", "Workshop", "前 500 筆每區違規次數"),
]
OVERVIEW = [
    'F[("events.jsonl")] --> R["load_records()<br/>list of dict"]',
    'R --> S2["一事件一表 ✗"]',
    'R --> S3["迴圈裡 concat ✗"]',
    'R --> S4["build_table() ✓<br/>一次一張表"]',
    'S4 --> S5["groupby"]',
    'S4 --> S6["先查唯一<br/>再 set_index"]',
    'style S2 fill:#fde2e1,stroke:#c0392b',
    'style S3 fill:#fde2e1,stroke:#c0392b',
    'style S4 fill:#d4edda,stroke:#27ae60,stroke-width:3px',
]
OVERVIEW_DIR = "LR"
SECTIONS = [
    dict(title="零、準備：讀進 list of dict", short="讀檔",
         steps=['A["read_text()<br/>整個檔案一個字串"] --> B["splitlines()<br/>一行一個事件"]',
                'B --> C["lines[:n]<br/>取前 n 行"] --> D["json.loads()<br/>每行變 dict"]',
                'D --> E(["✓ list of dict（200 筆）"])'],
         code=[(3, 11), (14, 17), (50, 50)],
         points=["`SCHEMA`：12 個欄位，後面 `build_table()` 用它當契約。"]),
    dict(title="一、容器不是語意", short="容器",
         question="二維 list 和 list of dict，交給 pandas 差在哪？",
         steps=['A["前 3 筆"] --> B["二維 list"] --> C["pd.DataFrame()"] --> D(["✗ 欄名 0, 1, 2"])',
                'A --> E["list of dict"] --> F["pd.DataFrame()"] --> G(["✓ 欄名 event_id…"])'],
         code=[(52, 56)], out=[1],
         points=["二維 list 沒有欄名，只能叫 `0, 1, 2`。**欄名就是 schema。**"]),
    dict(title="二、一事件一表 （錯）", short="一事件一表",
         question="每個事件包成一個 DataFrame，錯在哪？",
         steps=['A["200 筆"] --> B["每筆 pd.DataFrame()<br/>200 張 1 列的表"]',
                'B --> C(["✗ 各自猜型別<br/>15 張是 object"])',
                'B --> D(["✗ 沒有 groupby<br/>只能寫迴圈數"])',
                'B --> E["事後 pd.concat()"] --> F(["✗ 仍是 object"])'],
         code=[(58, 61), (62, 67)], out=[2],
         points=["型別一列一列猜：15 張表是 `object`。", "沒有 `groupby`，只能自己寫迴圈數。"]),
    dict(title="三、迴圈裡 `concat` （錯）", short="迴圈 concat",
         question="AI 最常給的累積寫法，表對嗎？",
         steps=['A["df = 空表"] --> B{"還有下一筆？"}',
                'B -- 有 --> C["pd.concat([df, 一列])<br/>產生新表、全部複製"] --> D["copied += len(df)"] --> B',
                'B -- 沒有 --> E(["✗ 複製 20100 列<br/>index 全是 0<br/>confidence 是 object"])'],
         code=[(30, 37), (69, 75)], out=[3],
         extra="""| 現象 | 後果 |
| --- | --- |
| 複製 20100 列 | 越來越慢（200 筆慢 100 倍以上） |
| index 全是 `0` | `loc[0]` 拿到 200 列 |
| `confidence` 是 `object` | 不能當數字算 |"""),
    dict(title="四、`build_table()` （對）", short="build_table",
         question="正確做法？先收進 list，**最後一次**轉成表。",
         steps=['A{"每一筆欄位<br/>剛好是 SCHEMA？"} -- 否 --> B(["✗ ValueError<br/>缺少／多出哪欄"])',
                'A -- 是 --> C["pd.DataFrame(records, columns=SCHEMA)<br/>一次轉成一張表"]',
                'C --> D["groupby(event_type).size()"] --> E(["✓ float64、可以計數"])'],
         code=[(20, 27), (77, 81)], out=[4],
         points=["同樣 15 個 `null`，一次轉換 → `float64`，缺值是 `NaN`。"]),
    dict(title="五、`groupby` 的結果", short="groupby",
         question="一欄、一列、`groupby` 結果，各是什麼？",
         steps=['A["df"] --> B["df[欄]<br/>一欄 Series，float64"]',
                'A --> C["df.iloc[0]<br/>一列 Series，object"]',
                'A --> D["groupby([zone, event_type]).size()"] --> E["Series<br/>鍵在 index"]',
                'E --> F(["✗ by[event_type]<br/>KeyError"])',
                'E --> G(["✓ reset_index(name=次數)<br/>變回欄位"])'],
         code=[(83, 85), (86, 93)], out=[5],
         points=["型別屬於**欄**，不屬於列。", "`groupby` 的鍵在 index 裡 → 先 `reset_index(name=...)`。"]),
    dict(title="六、`set_index` 前先查唯一", short="先查唯一",
         question="`event_id` 可以直接當 index 嗎？",
         steps=['A["全部 2838 筆"] --> B["duplicated(keep=False)"] --> C{"有重複？"}',
                'C -- 有 --> D(["✗ ValueError<br/>20 個 id 共 40 列"])',
                'C -- 沒有 --> E(["✓ set_index(event_id)"])'],
         code=[(95, 101), (40, 46), (102, 105)], out=[6],
         points=["補傳送了兩次，20 個 id 重複；`set_index` **不會報錯**。", "`loc[id]` 有時一列、有時兩列。"]),
]
