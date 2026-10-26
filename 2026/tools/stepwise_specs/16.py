LESSON = "16-context-budget.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "同一批資料，用哪種格式、留哪些欄與列，才放得進 context 預算。"
GOALS = [
    ("0–6 分", "零", "說出預算有哪幾個去處；為什麼用粗估"),
    ("6–24 分", "一", "比較四種格式的長度與陷阱"),
    ("24–35 分", "二、三", "先丟欄、再丟列，並交出丟棄清單"),
    ("35–50 分", "Workshop", "換排序，誰被丟掉了？"),
]
OVERVIEW = [
    'F[("articles.jsonl<br/>749 條")] --> H["含「墜落」16 條"]',
    'H --> A["一 四種格式<br/>serialize()"]',
    'H --> B["二 先丟欄<br/>只留 4 欄"]',
    'B --> C["三 再丟列<br/>fit_budget()"]',
    'C --> D(["送出的條文"])', 'C --> E(["丟棄清單"])',
]
OVERVIEW_DIR = "TD"
SECTIONS = [
    dict(title="零、準備：預算與粗估", short="準備",
         question="context 窗口裡，證據能用多少？",
         steps=['W["context 窗口"] --> S["系統指示・使用者問題"]', 'W --> E(["證據：本節負責<br/>預算 3,000"])',
                'W --> O["保留給模型輸出"]',
                'T["estimate_tokens()<br/>中文與數字算 1<br/>其他 0.5，× 1.2"]', 'S ~~~ T'],
         code=[(3, 18), (49, 52)], out=[0],
         extra="""| 模型 | 粗估低於實測 |
| --- | --- |
| `Qwen2.5-0.5B-Instruct` | 0 / 8 |
| `bge-small-zh-v1.5` | 2 / 8（短詞 `安全帽`、`頭盔`） |""",
         points=["不用 `tiktoken`：換模型就不準。粗估在長文本偏保守，是**規劃用的估計**，不是計費依據。"]),
    dict(title="一、同一批資料，四種格式", short="四種格式",
         question="同樣 16 條，換格式差多少？",
         steps=['A["16 條"] --> B["csv：10,294<br/>最短，靠引號分邊界"]',
                'A --> D["jsonl：11,721<br/>force_ascii=False"] --> D1(["✓ 長文本證據用它"])',
                'A --> C["jsonl-ascii：36,652"] --> C1(["✗ 中文變 \\uXXXX"])',
                'A --> E["markdown：46,551"] --> E1(["✗ 補空白、換行斷列"])'],
         code=[(21, 30), (54, 57)], out=[1],
         extra="""| 格式 | 長度 | 邊界 | 適合 |
| --- | --- | --- | --- |
| `jsonl`（`force_ascii=False`） | 中 | 可靠 | **長文本證據** |
| `csv` | 短 | 靠引號 | 欄位少、值短 |
| `markdown` | 長 | 遇換行會壞 | 短欄位摘要 |
| `jsonl-ascii` | 長 | 可靠 | 不要給 LLM |""",
         points=["Markdown 表格遇到條文裡的換行，16 列變成 171 行。"]),
    dict(title="二、先丟欄", short="丟欄",
         question="LLM 需要哪幾欄？",
         steps=['A["10 欄"] --> B["只留 law_name・article_no<br/>content・source_url"] --> C(["仍超過預算：要丟列"])'],
         code=[(59, 61)], out=[2],
         points=["`source_url` 要留：LLM 附出處用。"]),
    dict(title="三、再丟列：整條保留或整條丟", short="fit_budget",
         question="放不下時，丟哪幾條？",
         steps=['A["fit_budget()"] --> B{"欄位都在？"}', 'B -- 否 --> B1(["✗ ValueError"])',
                'B -- 是 --> C["依「墜落」出現次數排序"]', 'C --> D["從最後一條開始丟<br/>直到放得進預算"]',
                'D --> E{"一條都放不下？"}', 'E -- 是 --> E1(["✗ ValueError：提高預算或改用摘要"])',
                'E -- 否 --> G(["✓ 送出的文字・留下的・丟掉的"])'],
         code=[(33, 45), (63, 68)], out=[3],
         points=["條文**不截斷**：半條條文比沒有更危險。",
                 "丟掉的要留紀錄，不是默默消失。排序規則決定誰被丟——Workshop 會換排序試試。"]),
]
