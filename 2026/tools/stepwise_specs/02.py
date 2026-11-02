LESSON = "02-pandas-intro.md"
KEEP_AFTER = "Workshop"
SUBTITLE = "本課所有程式都建在 DataFrame 上。這一節只做六件事：建一張表、讀一個檔、取欄、取列、算一算、存回去。"
GOALS = [
    ("0–8 分", "零、一", "說出 DataFrame 的三個部分：欄、列、index"),
    ("8–16 分", "二", "讀一個 CSV，用 `shape`、`head()` 看它長什麼樣"),
    ("16–28 分", "三、四", "取一欄、取幾欄、用條件取列"),
    ("28–35 分", "五、六", "計數、加一欄、排序、分組、存成 CSV"),
    ("35–50 分", "Workshop", "課堂題：照著改；延伸題：自己組一張表"),
]
OVERVIEW = [
    'L["一 list of dict"] --> DF["DataFrame"]',
    'F[("workers.csv 名冊")] --> R["二 read_roster()"] --> DF',
    'DF --> C["三 取欄<br/>df[欄]"]',
    'DF --> W["四 取列<br/>df[條件]"]',
    'DF --> S["五 計數・加欄・排序"]',
    'S --> G["六 groupby → to_csv"]',
    'G --> O[("output/roster_by_contractor.csv")]',
]
OVERVIEW_DIR = "TD"
SECTIONS = [
    dict(title="零、準備：匯入 pandas、找到檔案", short="準備",
         question="程式開頭要寫什麼？",
         steps=['A["import pandas as pd<br/>大家都這樣縮寫"]', 'B["DATA：程式所在資料夾的 data/"]',
                'C["read_roster()<br/>讀名冊，每格先當字串"]', 'A ~~~ B ~~~ C'],
         code=[(3, 14)],
         points=["`Path(__file__)`：從哪個資料夾執行都找得到檔案。",
                 "`dtype=str, keep_default_na=False` 先照抄，第 03 節說明為什麼。"]),
    dict(title="一、從 list of dict 建一張表", short="建表",
         question="DataFrame 長什麼樣？",
         steps=['A["list：三個 dict<br/>每個 dict 是一列"] --> B["pd.DataFrame(rows)"]',
                'B --> C["欄名 columns<br/>來自 dict 的 key"]', 'B --> D["index<br/>自動編 0、1、2"]',
                'B --> E["shape<br/>(列數, 欄數)"]'],
         code=[(18, 27)], out=[1],
         extra="""| index（列標籤） | worker_id | name | zone | violations |
| --- | --- | --- | --- | --- |
| **0** | W001 | 蔡靜宜 | Z3 | 2 |
| **1** | W002 | 李雅婷 | Z2 | 0 |
| **2** | W003 | 王志豪 | Z1 | 5 |

最上面一列是**欄名**（columns），最左邊粗體是 **index**；中間每一格才是資料。""",
         points=["一個 dict 一列，dict 的 key 變成欄名。",
                 "最左邊的 0、1、2 是 **index**（列的標籤），不是資料。"]),
    dict(title="二、讀一個 CSV，先看長相", short="讀檔",
         question="讀進來之後，先看什麼？",
         steps=['A[("workers.csv")] --> B["read_roster()"]', 'B --> C["shape：61 列 × 7 欄"]',
                'B --> D["head(3)：前 3 列"]', 'B --> E["nunique()：不同值幾個"]',
                'E --> F(["60 ≠ 61：有人出現兩次"])'],
         code=[(29, 33)], out=[2],
         points=["拿到一份檔，先看 **shape** 和 **head()**，不要直接開始算。",
                 "列數不一定等於人數：W023 換了承攬商，名冊有兩列。"]),
    dict(title="三、取一欄、取幾欄", short="取欄",
         question="`df[\"欄\"]` 和 `df[[\"欄\", \"欄\"]]` 差在哪？",
         steps=['A["roster"] --> B["roster[\'name\']<br/>一個中括號"] --> B1(["Series：一欄"])',
                'A --> C["roster[[\'worker_id\', \'contractor\']]<br/>兩個中括號（裡面是 list）"] --> C1(["DataFrame：61 × 2"])'],
         code=[(35, 39)], out=[3],
         points=["一個欄名 → **Series**；一個欄名的 list → **DataFrame**。"]),
    dict(title="四、取列：條件篩選", short="取列",
         question="怎麼只留下 Z4 的人？",
         steps=['A["roster[\'home_zone\'] == \'Z4\'"] --> B["一欄 True／False<br/>（布林遮罩）"]',
                'B --> C["roster[遮罩]"] --> D(["只留 True 的 9 列"])',
                'E["(條件一) & (條件二)"] --> F(["兩個都成立：8 列"])',
                'G["iloc[0]：第 0 個位置<br/>loc[0, 欄]：標籤 0 那列的某欄"]'],
         code=[(41, 48)], out=[4],
         points=["比較會得到一欄 True／False，把它放進中括號就是篩選。",
                 "兩個條件：用 `&`（且）、`|`（或），**每個條件各自加括號**（第 08 節說明原因）。",
                 "`iloc` 看位置、`loc` 看標籤；篩選後兩者會不一樣（第 08 節）。"]),
    dict(title="五、數一數、加一欄、排序", short="計數排序",
         question="每個承攬商幾人？誰的違規最多？",
         steps=['A["roster[\'contractor\']"] --> B["value_counts()"] --> B1(["每個值出現幾次"])',
                'C["small[\'violations\'] > 3"] --> D["small[\'over_3\'] = ...<br/>整欄一次算，加成新欄"]',
                'D --> E["sort_values(\'violations\', ascending=False)"] --> E1(["由大到小"])'],
         code=[(50, 53)], out=[5],
         points=["`df[\"新欄\"] = 整欄的運算`：一次算完整欄，不用寫迴圈。",
                 "丙土木 21 列裡，有一列是 W023 換過來之後的紀錄。"]),
    dict(title="六、分組計數，存成檔案", short="分組存檔",
         question="每個承攬商、每個區域各幾人？存成檔案給別人用。",
         steps=['A["roster.groupby([承攬商, 區域])"] --> B[".size()：每組幾列"]',
                'B --> C[".reset_index(name=人數)<br/>變回一般的表"]',
                'C --> D["to_csv(output/..., index=False)"] --> E[("output/roster_by_contractor.csv")]',
                'E --> F["read_csv 讀回來核對"] --> G(["✓ 7 列，人數合計 61"])'],
         code=[(55, 62)], out=[6],
         points=["`groupby(...).size()` 的結果 index 是分組鍵；`reset_index(name=...)` 把它變回欄位。",
                 "`to_csv(index=False)`：不要把 0、1、2 也寫進檔案。",
                 "存完讀回來核對一次：**寫出去的東西要能讀回來**。"]),
]
DEMO_SUMMARY = "建表、讀 CSV、取欄、取列、計數排序、分組存檔"
DEMO_NOTES = ["這支程式會寫一個檔：`output/roster_by_contractor.csv`；其他都只讀 `data/`。"]
