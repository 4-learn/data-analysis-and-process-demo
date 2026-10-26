LESSON = "09-validate-idempotent.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "壞資料要被擋下；同一批資料重跑，結果要一樣。"
GOALS = [
    ("0–14 分", "零、一", "說明 `concat`＋`drop_duplicates` 為什麼不冪等"),
    ("14–22 分", "二", "寫一個「不過就停」、一次列出所有問題的驗證"),
    ("22–30 分", "三", "用指紋證明重跑結果一樣"),
    ("30–35 分", "四", "用對帳找出增量檔看不到的刪除"),
    ("35–50 分", "Workshop", "寫成 pytest，並弄壞它"),
]
OVERVIEW = [
    'V1[("v1 全量 749 條")] --> N["一 concat＋drop_duplicates"]',
    'V2[("v2 增量 5 條")] --> N',
    'V2 --> VA["二 validate()<br/>不過就停"]',
    'VA --> AP["三 apply_batch()<br/>較新的勝出"]',
    'V1 --> AP',
    'AP --> FP["fingerprint()<br/>重跑三次一樣"]',
    'AP --> RC["四 reconcile()<br/>對帳找刪除"]',
    'style N fill:#fde2e1,stroke:#c0392b',
    'style AP fill:#ddf3e4,stroke:#27ae60,stroke-width:3px',
]
SECTIONS = [
    dict(title="零、準備：規則與兩批資料", short="準備",
         question="這節的資料和規則是什麼？",
         steps=['K["KEY：(pcode, slug)<br/>REQUIRED：chapter 以外必填<br/>ValidationError：失敗就停"]',
                'D[("v1 articles.jsonl<br/>749 條")] --> E["validate()"] --> E1(["✓ 通過"])',
                'G[("v2-changes.jsonl<br/>5 條：修改 4、新增 1")] --> H["第一段起使用"]',
                'K ~~~ D'],
         code=[(3, 26), (96, 98)],
         points=["`chapter` 不是必填：沒分章的法規本來就是空的，那是事實不是缺值。",
                 "練習站第 2 版還**刪了一條**，但增量檔裡沒有——第四段再談。"]),
    dict(title="一、天真的合併", short="天真合併",
         question="`pd.concat([v1, v2]).drop_duplicates(KEY)` 錯在哪？",
         steps=['A["concat(v1, v2)"] --> A1(["✗ 再跑一次：754 → 759 列"])',
                'A --> B["keep=first（預設）"] --> B1(["✗ 舊資料贏：v2 修正丟掉"])',
                'A --> C["keep=last"] --> C1["後到的贏"] --> C2(["✗ 重送 v1 就被蓋回去"])'],
         code=[(100, 108)], out=[1],
         points=["三個問題**都不會報錯**。",
                 "`keep=\"last\"` 是「後到的贏」，不是「新的贏」。"]),
    dict(title="二、驗證：不過就停", short="validate",
         question="怎麼在合併之前擋下壞資料？",
         steps=['A["一批資料"] --> B{"欄位齊全？"}', 'B -- 否 --> B1(["✗ ValidationError"])',
                'B -- 是 --> C["8 項檢查<br/>必填・格式・白名單<br/>跨欄一致・唯一"]',
                'C --> D{"有任何一項不過？"}', 'D -- 有 --> D1(["✗ 一次列出全部問題<br/>各附一個例子"])',
                'D -- 沒有 --> E(["✓ 原樣回傳"])'],
         code=[(29, 51), (110, 118)], out=[2],
         extra="""| 檢查 | 擋下什麼 |
| --- | --- |
| 必填非空 | 漏抓、空字串 |
| `pcode`、`slug` 格式 | 型別漂移（`1.0`）、亂碼 |
| `article_no` ＝ `第 {slug} 條` | 兩欄來自不同條文 |
| `source_version` 白名單 | 來路不明的版本 |
| `fetched_at` 帶時區 | 無法比先後的時間 |
| `content_hash` ＝ 內容雜湊 | 改了內容沒重算 |
| `(pcode, slug)` 不重複 | 同一條送兩次 |""",
         points=["失敗就**拋例外**，不是印 warning。",
                 "一次列出全部、附例子，上游才不用來回好幾輪。"]),
    dict(title="三、冪等的合併", short="apply_batch",
         question="怎麼讓重送、舊資料晚到，結果都不變？",
         steps=['A["validate(batch)"] --> B{"這個 KEY 已經有了？"}',
                'B -- 沒有 --> C["新增"]', 'B -- 有 --> D{"fetched_at 比較新？<br/>（轉成時間再比）"}',
                'D -- 新 --> E["更新"]', 'D -- 舊或一樣 --> G["略過"]',
                'D -- 同時間不同內容 --> H(["✗ 停：無法判斷誰對"])',
                'C --> R["合併後再 validate()"]', 'E --> R', 'G --> R',
                'R --> FP(["✓ fingerprint() 三次相同"])'],
         code=[(54, 83), (120, 126)], out=[3],
         points=["**冪等**：做一次和做很多次，結果一樣。",
                 "證明它：列數一樣不夠，要**指紋**一樣。",
                 "「略過 749」是訊號：有人重送了舊資料。"]),
    dict(title="四、增量看不到的事", short="對帳",
         question="三次指紋都一樣，資料就對了嗎？",
         steps=['A["本地：每部法規幾條"] --> C{"一樣？"}', 'B[("來源 v2-laws.json<br/>每部法規幾條")] --> C',
                'C -- 不一樣 --> D(["✗ N0020012：來源 20、本地 21"])', 'D --> E["交給人判斷<br/>不自動刪"]'],
         code=[(86, 92), (128, 129)], out=[4],
         points=["增量檔只寫有內容的條文，**刪除寫不進去**。",
                 "對帳只說「哪部少了」，不說「少了哪條」；更不該自動刪。"]),
]
