LESSON = "01-position.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "這門課在 AI 系統的哪一層、手上有哪三種資料、什麼該交給 LLM。語法從第 02 節開始，本節只看輸出。"
GOALS = [
    ("0–6 分", "一", "指出哪些模組屬於資料處理層"),
    ("6–13 分", "二", "把資料分成事件、文件、文字三種"),
    ("13–22 分", "三", "說出「整份丟進去」與「最後 500 筆」錯在哪"),
    ("22–32 分", "四", "說出 list 管即時、pandas 管歷史"),
    ("32–35 分", "五", "兩行指令確認環境"),
    ("35–50 分", "Workshop", "範圍判斷表與資料流圖"),
]
LAYERS = """```mermaid
flowchart TD
    CAM["工地 AI 攝影機"] --> V
    subgraph OUT["不在本養成班範圍"]
        V["影像辨識<br/>這一幀畫面裡有什麼？<br/>工具：視覺模型"]
    end
    subgraph SYS["系統端，本課不做"]
        RT["即時告警<br/>現在要不要叫人過去？<br/>工具：if／規則、list／dict"]
    end
    subgraph UP["上游：爬蟲課、MariaDB 課"]
        ST["收集與存放<br/>資料從哪來、存在哪？<br/>工具：爬蟲、MariaDB"]
    end
    subgraph THIS["本課"]
        DA["整理、驗證、彙總、濃縮<br/>發生過什麼？有沒有模式？<br/>哪些該交給 LLM？<br/>工具：pandas"]
    end
    subgraph DOWN["下游：機器學習課、LLM 課"]
        ML["模型訓練<br/>能不能從過去學會預測？<br/>工具：scikit-learn 等"]
        LLM["解釋與回答<br/>怎麼說給人聽？<br/>工具：LLM"]
    end
    V -- "一筆一筆的事件" --> RT
    V -- "事件" --> ST
    ST -- "CSV、JSONL、查詢結果" --> DA
    DA --> ML
    DA -- "驗證過、放得進 context 的摘要" --> LLM
    style THIS fill:#fff3cd,stroke:#d39e00,stroke-width:3px
    style DA fill:#ffe08a,stroke:#d39e00,stroke-width:2px
```
"""
OVERVIEW = [
    'E[("events.jsonl<br/>2838 筆事件")] --> RT["四 即時層<br/>stream_alerts()<br/>list／deque"]',
    'E --> H["四 歷史層<br/>dedupe() → weekly_violations()"]',
    'H --> S(["每區每週摘要<br/>85 估計 token"])',
    'E --> X(["三 整份丟給 LLM<br/>72 萬估計 token"])',
    'style X fill:#fde2e1,stroke:#c0392b',
    'style S fill:#ddf3e4,stroke:#27ae60,stroke-width:3px',
]
OVERVIEW_DIR = "TD"
SECTIONS = [
    dict(title="一、本課在系統裡的哪一層", short="哪一層",
         question="從攝影機到 LLM，本課負責哪一段？",
         body=LAYERS + """
- 本課**不做**：即時推論、影像辨識、模型訓練、LLM 推論。
- 輸入是上游交來的 CSV、JSONL、查詢結果；輸出是**可回溯、驗證過、放得進 context** 的表與文字。
- pandas 是系統的**記憶體與語意層**：即時層只記得「現在」，pandas 記得「過去四週」。"""),
    dict(title="二、三種資料形態", short="三種形態",
         question="三個都是「一行一個 JSON」，差在哪？",
         steps=['A["事件 events.jsonl<br/>某時某地發生一件事"] --> A1(["先彙總才交出去"])',
                'B["文件 articles.jsonl<br/>一條有出處的條文"] --> B1(["整條附出處交出去"])',
                'C["文字 near-miss-reports.jsonl<br/>人寫的敘述"] --> C1(["先去識別才交出去"])'],
         code=[(3, 16), (47, 49), (81, 93)], out=[1],
         extra="""| 形態 | 一列是什麼 | 主要在哪幾節 |
| --- | --- | --- |
| **事件** | 某時、某地、某人發生某件事 | 05–15 |
| **文件** | 一條有出處、有版本的條文 | 03、04、09、16 |
| **文字** | 一段人寫的自由敘述 | 17 |""",
         points=["本課從不碰影像：`snapshot` 欄只是路徑字串，沒有附圖檔。"]),
    dict(title="三、AI 的第一個建議：整份丟進去", short="整份丟進去",
         question="把整份事件檔貼給 LLM，有多長？",
         steps=['A["整份 events.jsonl"] --> A1(["✗ 72 萬估計 token"])',
                'B["只留違規"] --> B1(["✗ 12 萬，而且有重送"])',
                'C["檔案最後 500 筆"] --> C1(["✗ W041 那 18 筆一筆都不在"])',
                'D["每區每週摘要 CSV"] --> D1(["✓ 85 估計 token"])'],
         body="""```python
# AI 常見寫法，本節測試不涵蓋這段
events = open("data/events/events.jsonl").read()
prompt = f"以下是工地事件紀錄：\\n{events}\\n請問最近有什麼異常？"
```""",
         code=[(18, 22), (76, 77), (112, 128)], out=[4],
         points=["「放不下就取最後 500 筆」最危險：檔案順序是**到達順序**，真正的異常剛好不在裡面。",
                 "**LLM 不該看到三萬筆事件；它該看到十行摘要。** 哪十行，第 15 節決定。"]),
    dict(title="四、list 管即時，pandas 管歷史", short="即時 vs 歷史",
         question="同一份檔案，兩種處理方式各看到什麼？",
         steps=['A["一筆一筆照到達順序"] --> B["stream_alerts()<br/>每人只記最近 10 分鐘"]',
                'B --> B1(["✓ W041 第 3 筆就告警"])', 'B --> B2(["✗ 看不到 W029、W044 的累積"])',
                'C["四週全部讀進來"] --> D["dedupe() → weekly_violations()"]',
                'D --> D1(["✓ 每區每週・反覆犯的人"])'],
         code=[(25, 44), (52, 73), (95, 110)], out=[2, 3],
         points=["即時層要快、只看現在，**不需要 pandas**。",
                 "「同一人反覆犯」是累積出來的，只有回頭看全部歷史才看得到。",
                 "`dedupe()` 只在「除了 `ingested_at` 完全相同」才去掉，內容不同就停（第 09 節）。"]),
    dict(title="五、課前環境檢核", short="環境檢核",
         question="上課前要確認什麼？",
         body="""```bash
python3 -c "import sys, pandas, numpy; print(sys.version.split()[0], pandas.__version__, numpy.__version__)"
python3 01_position.py | head -4
```

- 第一行：Python **3.11 以上**、pandas **3.0.x**（本課以 3.0.6 實測）。
- 第二行：印出第二段那四行。
- Python 是 3.10 的話裝不到 pandas 3，開課前依 `README.md` 處理。"""),
]
