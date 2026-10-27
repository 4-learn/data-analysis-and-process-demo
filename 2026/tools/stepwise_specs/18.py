LESSON = "18-end-to-end.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "從 events.jsonl 到給 LLM 的摘要：一支可重跑、會擋壞資料的程式。"
GOALS = [
    ("0–8 分", "零、一", "說出 AI 一行版為什麼壞資料照樣產出摘要"),
    ("8–30 分", "二～四", "走一遍管線：讀取 → 清理 → 驗證 → 彙總 → 濃縮 → 序列化"),
    ("30–38 分", "五、六", "用指紋證明可重跑；故意餵壞資料，全部擋下"),
    ("38–50 分", "Workshop", "加兩道檢查"),
]
OVERVIEW = [
    'J[("events.jsonl")] --> R["1 read_events()<br/>02、03 節"]',
    'R --> C["2 clean()＋audit<br/>08、09 節"]',
    'C --> V["3 validate()<br/>09～11 節"]',
    'V --> W["4 weekly()<br/>11、12 節"]',
    'W --> S["5 condense()<br/>13、15 節"]',
    'S --> O["6 serialize()＋預算<br/>16 節"]',
    'O --> F(["摘要 JSONL"])',
    'R -.-> X(["PipelineError：整批擋下"])', 'V -.-> X', 'S -.-> X', 'O -.-> X',
    'style X fill:#fde2e1,stroke:#c0392b',
    'style F fill:#ddf3e4,stroke:#27ae60,stroke-width:3px',
]
OVERVIEW_DIR = "TD"
SECTIONS = [
    dict(title="零、準備：規格、例外、讀取", short="讀取",
         question="管線的第一步要擋下什麼？",
         steps=['A["read_json(dtype=False, convert_dates=False)"] --> B{"必要欄位都在？"}',
                'B -- 否 --> X(["✗ PipelineError"])', 'B -- 是 --> C{"有缺鍵（NaN）？<br/>confidence 除外"}',
                'C -- 有 --> X', 'C -- 沒有 --> D{"confidence 是數字？<br/>其他欄是字串？"}',
                'D -- 否 --> X', 'D -- 是 --> E(["✓ raw"])'],
         code=[(7, 58)],
         extra="""| 步驟 | 函式 | 失敗時 | 出處 |
| --- | --- | --- | --- |
| 1. 讀取 | `read_events()` | 拋例外 | 02、03 |
| 2. 清理 | `clean()` | 記進 audit | 08、09 |
| 3. 驗證 | `validate()` | 拋例外 | 09～11 |
| 4. 彙總 | `weekly()` | — | 11、12 |
| 5. 濃縮 | `condense()` | 追不回就拋例外 | 13、15 |
| 6. 序列化 | `serialize()` | 超過預算就拋例外 | 16 |""",
         points=["每一步都是前面某一節的東西；**這節把它們串起來**。",
                 "資料有問題就整批不給：`PipelineError` 繼承 `ValueError`。"]),
    dict(title="一、AI 的一行版：壞資料照樣產出摘要", short="AI 一行版",
         question="壞資料進去，AI 的一行版會發現嗎？",
         steps=['A["原始檔"] --> R["read_json() 一行<br/>groupby().nlargest()"]',
                'B["第 6 行少了時區"] --> R', 'C["第 6 行 event_type=no_vest"] --> R',
                'R --> D(["✗ 三份都照樣產出摘要"])'],
         code=[(195, 205), (209, 219)], out=[1],
         points=["`broken()`：在記憶體裡複製一份、弄壞某一行，不寫檔。",
                 "少了時區：`event_time` 從「日期」變「文字」，沒有錯誤訊息。"]),
    dict(title="二、清理與 audit", short="clean",
         question="哪些可以自動修？修了怎麼交代？",
         steps=['A["raw"] --> B["依到達時間排序"]', 'B --> C["除 ingested_at 外完全相同<br/>→ 重送，留最先到的"]',
                'C --> D["confidence > 1 → ÷100"]', 'D --> E(["✓ ev＋audit 紀錄"])'],
         code=[(61, 80), (221, 227)], out=[2],
         points=["只去掉「完全相同的重送」；內容不同的同一 `event_id` 交給驗證擋下。",
                 "先依到達時間排序：「留最先到的」才不看輸入順序。"]),
    dict(title="三、驗證通過，彙總成每人每週", short="validate＋weekly",
         question="哪些情況要整批擋下？",
         steps=['A["validate()"] --> B{"event_id 唯一？<br/>時間帶時區？<br/>event_type 在白名單？<br/>confidence 在 0–1？"}',
                'B -- 任一否 --> X(["✗ PipelineError"])', 'B -- 全是 --> C["加上 date・week・late・is_violation"]',
                'C --> D["weekly()<br/>未辨識記在 (未辨識) 名下"]', 'D --> E(["✓ 違規合計＝事件表違規數"])'],
         code=[(83, 123), (229, 236)], out=[3],
         points=["彙總後核對：違規合計要等於事件表的違規數。",
                 "名冊上沒有事件的人不在表上——這張表回答的是「誰違規」。"]),
    dict(title="四、濃縮、序列化、預算", short="condense＋serialize",
         question="摘要長什麼樣？超過預算怎麼辦？",
         steps=['A["condense()"] --> B["Top 3・未辨識・趨勢<br/>異常・資料註記"]',
                'B --> C{"每列的 key 查得到事件？"}', 'C -- 否 --> X(["✗ PipelineError"])',
                'C -- 是 --> D["serialize()<br/>JSONL，force_ascii=False"]',
                'D --> E{"估計 token > 1500？"}', 'E -- 是 --> X', 'E -- 否 --> F(["✓ 摘要 JSONL"])'],
         code=[(126, 176), (238, 242)], out=[4],
         points=["每列帶 `key`，`n` 必須等於查到的筆數（第 15 節）。",
                 "超過預算就停，不截斷：LLM 組要的是「整批不給」，不是「給一半」。"]),
    dict(title="五、重跑兩次，指紋相同", short="指紋",
         question="同一份資料重跑，結果一樣嗎？",
         steps=['A["run(path) 第 1 次"] --> F["fingerprint()"]', 'B["run(path) 第 2 次"] --> F',
                'C["輸入倒序"] --> F', 'F --> G(["✓ 三次指紋相同"])'],
         code=[(179, 192), (244, 247)], out=[5],
         points=["連輸入順序都不影響結果：清理時先依到達時間排序、排名同分依工號。"]),
    dict(title="六、故意餵壞資料：全部擋下", short="餵壞資料",
         question="六種壞資料＋預算不足，擋得下嗎？",
         steps=['A["少時區・未知類型・缺欄位<br/>同 id 不同內容・字串 confidence<br/>confidence 超出範圍"] --> R["run()"]',
                'B["預算 500"] --> R', 'R --> X(["✓ 7 種全部 PipelineError"])'],
         code=[(249, 268)], out=[6],
         points=["驗證要能證明自己有用：**故意弄壞，看它會不會擋**。"]),
]
