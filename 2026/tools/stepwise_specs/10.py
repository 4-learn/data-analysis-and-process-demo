LESSON = "10-event-vs-ingest.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "事件什麼時候發生，和資料什麼時候到，是兩個時間。"
GOALS = [
    ("0–12 分", "一、二", "說出檔案順序不是發生順序；先去重"),
    ("12–24 分", "三", "說出兩種每日計數差在哪幾列、各回答什麼問題"),
    ("24–30 分", "四", "看出 UTC 日期不是台北日期"),
    ("30–35 分", "五", "分辨法規的 `modified_date` 與 `fetched_at`"),
    ("35–50 分", "Workshop", "兩種每日計數，差異列清單"),
]
OVERVIEW = [
    'F[("events.jsonl")] --> L["load_events()<br/>兩個時間都轉成台北時間"]',
    'L --> A["一 檔案順序≠發生順序"]',
    'L --> D["二 dedupe()<br/>先去重"]',
    'D --> E["三 daily(event／ingest)<br/>兩種每日計數"]',
    'D --> U["四 str[:10] 是 UTC 日期"]',
    'A2[("articles.jsonl<br/>02-exports")] --> M["五 modified_date<br/>vs fetched_at"]',
    'style U fill:#fde2e1,stroke:#c0392b',
]
OVERVIEW_DIR = "TD"

SECTIONS = [
    dict(title="零、準備：兩個時間都轉成台北時間", short="準備",
         question="一筆事件有哪兩個時間？",
         steps=['A["event_time<br/>+08:00 攝影機寫的"]', 'B["ingested_at<br/>+00:00 伺服器寫的"]',
                'A --> C{"都帶時區？"}', 'B --> C', 'C -- 否 --> C1(["✗ ValueError"])',
                'C -- 是 --> D["to_datetime(utc=True)<br/>.dt.tz_convert(Asia/Taipei)"]',
                'D --> E(["✓ event_ts、ingest_ts"])'],
         code=[(3, 25), (57, 58)],
         extra="""| 欄位 | 回答 | 誰寫的 |
| --- | --- | --- |
| `event_time` | 什麼時候**發生** | 攝影機（`+08:00`） |
| `ingested_at` | 什麼時候**到** | 伺服器（UTC） |""",
         points=["`dedupe()` 依 `event_id` 去重、留先到的（第 09 節）。"]),
    dict(title="一、檔案順序＝到達順序", short="檔案順序",
         question="檔案第一列是最早發生的事件嗎？",
         steps=['A["檔案順序"] --> B["依 ingested_at：排好了"]',
                'A --> C["依 event_time：沒排好"] --> D(["✗ 45 列比上一列更早發生"])',
                'E["延遲 = ingest_ts - event_ts"] --> G["中位數 10 秒"]',
                'E --> H(["cam-05 補傳：近 23 小時"])',
                'B ~~~ E'],
         code=[(60, 73)], out=[1],
         points=["平常延遲只有 10 秒，兩個時間幾乎一樣——**問題只在少數幾天**。",
                 "找最長延遲要先排除重送的第二份（只看第一次到達）。"]),
    dict(title="二、先去重", short="去重",
         question="補傳送了兩次，先處理什麼？",
         steps=['A["2838 列"] --> B["20 個 event_id 到兩次<br/>相隔 14 分鐘"]',
                'B --> C["dedupe()"] --> D(["✓ 2818 列"])', 'B --> E(["✗ 不去重：09-11 多算 20 列"])'],
         code=[(28, 31), (75, 81)], out=[2],
         points=["先依 `event_id` 去重，再談時間。"]),
    dict(title="三、以哪個時間彙總", short="兩種每日計數",
         question="09-10 到底幾筆？",
         steps=['A["2818 列"] --> B["daily(event)<br/>依發生日"] --> B1(["09-10：117 筆"])',
                'A --> C["daily(ingest)<br/>依到達日"] --> C1(["09-10：97 筆"])',
                'B1 --> D["差 20 列：全是 cam-05<br/>09-10 發生、09-11 才到"]', 'C1 --> D',
                'E["as_of(day, cutoff)"] --> E1["09-10 23:59 看：97"]', 'E --> E2["09-11 12:00 看：117"]'],
         code=[(34, 40), (83, 95)], out=[3],
         extra="""| 問題 | 用哪個時間 |
| --- | --- |
| 09-10 工地發生幾次違規？ | 發生日 |
| 09-11 伺服器處理多少資料？ | 到達日 |""",
         points=["依到達日，開挖區 09-10 違規是 0：**「0」是沒收到，不是沒發生**。",
                 "依發生日，同一個問題在不同時刻問，答案不同 → 報告要寫「截至何時」。"]),
    dict(title="四、`ingested_at` 直接取日期是 UTC", short="UTC 日期",
         question="`ingested_at.str[:10]` 當日期，錯在哪？",
         steps=['A["ingested_at：2026-08-30T23:04+00:00"] --> B["str[:10]"] --> C(["✗ 2026-08-30（週日）"])',
                'A --> D["換成台北時間"] --> E(["✓ 2026-08-31 07:04（週一）"])',
                'C --> G(["✗ 230 列算錯天<br/>停工的週日有 31 筆"])'],
         code=[(97, 105)], out=[4],
         points=["台北比 UTC 快 8 小時：早上 7 點的事件，UTC 是前一天 23 點。",
                 "最好認的破綻：**週日停工，卻有週日的資料**。"]),
    dict(title="五、法規：抓到的時間不是修正的時間", short="法規兩個時間",
         question="法規的 `fetched_at` 能回答「最近一次修正」嗎？",
         steps=['A["02-exports 的 modified_date"] --> B(["修正日：2015～2024"])',
                'C["articles.jsonl 的 fetched_at"] --> D(["抓到日：只有一種值"])',
                'B --> E["事件時間"]', 'D --> G["到達時間"]'],
         code=[(43, 53), (107, 114)], out=[5],
         points=["`fetched_at` 只能回答「我們手上的版本是什麼時候的」。",
                 "練習站條文可能經刻意修改，不具法律效力。"]),
]
