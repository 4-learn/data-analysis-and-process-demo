# 16｜序列化與 context 預算

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 16 節：序列化與 context 預算。**
> 本節把一批查到的條文交給 LLM。先量同一批資料用四種格式寫出來各多長，再用「先丟欄、再丟列」把它塞進預算，並且**記下丟了什麼**。
> 本節不是 tokenizer 課，也不呼叫任何 LLM。token 一律用**保守粗估**；真實計數與各模型的差異屬 LLM 課第 02 節。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 範例程式碼

- [demo：16_context_budget.py](https://github.com/4-learn/data-analysis-and-process-demo/blob/master/2026/16_context_budget.py)（與本頁 Demo 逐字相同）
- 練習資料與環境說明：[2026/README](https://github.com/4-learn/data-analysis-and-process-demo/tree/master/2026)

## 學習目標與時間

完成後，你能：說出同一份資料換格式為什麼長度可以差五倍；用 `to_json`／`to_csv`／`to_markdown` 產出 LLM 可讀的文字，並避開會讓表格結構壞掉的格式；在預算內做取捨，並交出「送出什麼、丟掉什麼」的紀錄。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–6 分鐘 | 為什麼不能把整張表丟進去 | 預算的三個去處 |
| 6–16 分鐘 | 同一批資料，四種格式 | 長度對照表 |
| 16–24 分鐘 | 格式的隱形成本與結構陷阱 | `force_ascii`、Markdown 斷列 |
| 24–35 分鐘 | 先丟欄、再丟列 | `fit_budget()` 與丟棄清單 |
| 35–50 分鐘 | Workshop：誰被丟掉了？ | 換排序後的比較與判讀 |

先修：本課第 03 節（JSONL）、第 15 節（濃縮）。環境同第 02 節：Python 3.11 以上、pandas 3.0；`to_markdown` 另需 `tabulate`。

## 一、為什麼不能把整張表丟進去

LLM 組要做「職安法規問答」。使用者問到「墜落」，檢索層在 749 條裡找到 16 條。你要把這 16 條交給模型當證據。

context 窗口不是全部給證據用的：

```text
context 窗口
├── 系統指示（角色、規則、輸出格式）
├── 使用者問題
├── 證據 ← 本節負責的部分
└── 保留給模型輸出
```

所以 LLM 組會給你一個數字：「證據最多 3,000 token。」你的工作是**讓這 3,000 token 裡裝的是最有用的東西，而且知道沒裝進去的是什麼**。

### 為什麼用粗估，不用 tiktoken？

`tiktoken` 是 OpenAI 的 tokenizer，換一個模型就不準；LLM 課第 02 節實測過，同一句中文在 `bge-small-zh-v1.5` 與 `Qwen2.5-0.5B-Instruct` 的 token 數可以差到 1.5 倍以上。在資料處理這一層，你通常還不知道下游會用哪個模型。

本節用**保守粗估**：非 ASCII 字元（中文、全形標點）與數字各算 1、其他 ASCII 算 0.5，再乘 1.2 的安全係數。拿它對照 LLM 課的實測 fixture（8 個案例 × 2 個模型）：

| 模型 | 粗估低於實測的案例 |
| --- | --- |
| `Qwen2.5-0.5B-Instruct` | 0 / 8 |
| `bge-small-zh-v1.5` | 2 / 8（`安全帽`、`頭盔`：短詞，bge 另加 `[CLS]`／`[SEP]` 兩個 token） |

意思是：**它在長文本上偏保守，在極短文本上可能低估。** 本節處理的是整段條文，風險可接受；但它是「預算規劃用的估計」，不是計費依據。真要精確，換成目標模型的 tokenizer——`fit_budget()` 的 `count` 參數就是留給你換的。

## 二、同一批資料，四種格式

以下為完整 `16_context_budget.py`，只讀 `data/articles.jsonl`，不寫檔、不連線。

<!-- demo: 16_context_budget.py -->
```python
"""第 16 節：同一批資料，用哪種格式、留哪些欄位與列，才放得進 context 預算。"""

import math
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data" / "articles.jsonl"
QUERY = "墜落"
BUDGET = 3000              # 估計 token 上限；實際值依模型而定
KEEP = ["law_name", "article_no", "content", "source_url"]   # LLM 需要的；source_url 用來附出處


def estimate_tokens(text):
    """保守粗估，不是計數：非 ASCII 字元與數字各算 1、其他 ASCII 算 0.5，再乘 1.2 安全係數。"""
    heavy = sum(1 for ch in text if not ch.isascii() or ch.isdigit())
    light = len(text) - heavy
    return math.ceil((heavy + light * 0.5) * 1.2)


def serialize(df, fmt):
    if fmt == "csv":
        return df.to_csv(index=False)
    if fmt == "jsonl-ascii":
        return df.to_json(orient="records", lines=True)
    if fmt == "jsonl":
        return df.to_json(orient="records", lines=True, force_ascii=False)
    if fmt == "markdown":
        return df.to_markdown(index=False)
    raise ValueError(f"未知格式：{fmt}")


def fit_budget(df, budget, columns, rank_by, count=estimate_tokens, fmt="jsonl"):
    """先丟欄、再丟列；條文不截斷。回傳 (要送出的文字, 留下的列, 被丟掉的列)。"""
    missing = [c for c in columns + [rank_by] if c not in df.columns]
    if missing:
        raise ValueError(f"缺少欄位 {missing}")
    ranked = df.sort_values([rank_by, "source_url"], ascending=[False, True])
    slim = ranked[columns]
    kept = len(slim)
    while kept > 0 and count(serialize(slim.head(kept), fmt)) > budget:
        kept -= 1
    if kept == 0:
        raise ValueError(f"預算 {budget} 連一條都放不下，請提高預算或改用摘要")
    return serialize(slim.head(kept), fmt), ranked.head(kept), ranked.iloc[kept:]


if __name__ == "__main__":
    articles = pd.read_json(DATA, lines=True, dtype=False, convert_dates=False)
    hits = articles[articles["content"].str.contains(QUERY, regex=False)].copy()
    hits["hits"] = hits["content"].str.count(QUERY)
    print(f"全部 {len(articles)} 條；含「{QUERY}」{len(hits)} 條\n")

    print("== 1. 同樣 16 列、全部欄位，四種格式 ==")
    for fmt in ("csv", "jsonl-ascii", "jsonl", "markdown"):
        text = serialize(hits.drop(columns="hits"), fmt)
        print(f"{fmt:12} 字元 {len(text):>6,}  估計 token {estimate_tokens(text):>6,}")

    print(f"\n== 2. 先丟欄：只留 {KEEP} ==")
    slim = serialize(hits[KEEP], "jsonl")
    print(f"jsonl        字元 {len(slim):>6,}  估計 token {estimate_tokens(slim):>6,}  （預算 {BUDGET:,}）")

    print("\n== 3. 再丟列：依「墜落」出現次數排序，整條保留或整條丟 ==")
    text, kept, dropped = fit_budget(hits, BUDGET, KEEP, rank_by="hits")
    print(f"送出 {len(kept)} 條，估計 token {estimate_tokens(text):,}：")
    print(kept[["law_name", "article_no", "hits"]].to_string(index=False))
    print(f"丟掉 {len(dropped)} 條（要留紀錄，不是默默消失）：")
    print(", ".join(dropped["law_name"].str[:4] + dropped["article_no"]))
```

執行（在本目錄下）：

```bash
python3 16_context_budget.py
```

第一段輸出：

```text
全部 749 條；含「墜落」16 條

== 1. 同樣 16 列、全部欄位，四種格式 ==
csv          字元  9,681  估計 token 10,294
jsonl-ascii  字元 42,549  估計 token 36,652
jsonl        字元 12,059  估計 token 11,721
markdown     字元 70,109  估計 token 46,551
```

**同樣 16 列、同樣 10 個欄位，最短和最長差了 7 倍。** 而且四種都超過 3,000 的預算三倍以上。

## 三、格式的隱形成本與結構陷阱

### `jsonl-ascii`：一個預設參數，長度變 3.5 倍

`to_json()` 預設 `force_ascii=True`，每個中文字都被寫成 `\u8077` 這樣的六個字元：

```text
{"pcode":"N0060001","law_name":"\u8077\u696d\u5b89\u5168\u885b\u751f\u6cd5", ...
```

對程式來說兩者等價（`json.loads` 讀回來一樣），但對 LLM 來說是三倍多的長度，而且模型要先「解碼」才看得懂。**給 LLM 的 JSON 一律 `force_ascii=False`。** 這是 AI 產生的程式碼最常漏掉的一個參數。

### `markdown`：最長，而且結構會壞

Markdown 表格最「好讀」，但看兩件事：

1. **補空白**。`to_markdown()` 會把每一欄補齊到最長那格的寬度。一個 900 字的條文欄，會讓每一列都補上幾百個空白。
2. **換行斷列**。16 條裡有 15 條的 `content` 含換行（`一、…\n二、…`）。實測 `to_markdown()` 輸出 **171 行**，而不是 16 列＋表頭兩行；多出來的行是被拆開的條文，**在那些行裡，`source_url` 那一格是空的**。模型看到的是「一段沒有出處的文字」。

> **Markdown 表格適合「短欄位」的摘要表**（第 15 節的十行濃縮結果），**不適合放長文本**。長文本用 JSONL：一行一筆，換行被寫成 `\n`，邊界不會壞。

### `csv`：最短，但不一定最好

CSV 最短，因為欄名只出現一次。代價是：模型要自己對「第 6 欄是什麼」，欄位一多就容易錯位；含逗號與換行的條文要靠引號包住，模型讀引號的可靠度不如讀 JSON 鍵值。

| 格式 | 長度 | 邊界可靠 | 欄名語意 | 適合 |
| --- | --- | --- | --- | --- |
| `jsonl`（`force_ascii=False`） | 中 | 高 | 每筆都有 | **長文本證據** |
| `csv` | 短 | 中（靠引號） | 只在表頭 | 欄位少、值短的表 |
| `markdown` | 長 | 低（遇換行會壞） | 只在表頭 | 短欄位摘要、給人看 |
| `jsonl-ascii` | 長 | 高 | 每筆都有 | 不要給 LLM |

## 四、先丟欄、再丟列，並記下丟了什麼

順序有理由：

1. **先丟欄**：`pcode`、`slug`、`content_hash`、`fetched_at`、`source_version` 是給程式用的，模型回答問題用不到。只留 `law_name`、`article_no`、`content`、`source_url`。**`source_url` 不能丟**——那是模型附出處、使用者回頭核對的唯一依據（爬蟲課第 16 節）。
2. **再丟列**：整條保留或整條丟，**不截斷條文**。截掉後半段的條文，可能剛好截掉「但書」，意思會整個反過來。
3. **都放不下就停**：連一條都放不下時 `fit_budget()` 會報錯，而不是硬塞半條進去。

```text
== 2. 先丟欄：只留 ['law_name', 'article_no', 'content', 'source_url'] ==
jsonl        字元  8,841  估計 token  9,007  （預算 3,000）

== 3. 再丟列：依「墜落」出現次數排序，整條保留或整條丟 ==
送出 4 條，估計 token 2,221：
  law_name article_no  hits
營造安全衛生設施標準     第 17 條     3
營造安全衛生設施標準     第 18 條     2
營造安全衛生設施標準     第 19 條     2
營造安全衛生設施標準     第 22 條     2
丟掉 12 條（要留紀錄，不是默默消失）：
職業安全第 6 條, 營造安全第 105 條, 營造安全第 131 條, 營造安全第 149-1 條, 營造安全第 162 條, 營造安全第 20 條, 營造安全第 24 條, 營造安全第 25 條, 營造安全第 42 條, 營造安全第 56 條, 營造安全第 59 條, 營造安全第 79 條
```

丟欄只省了約 23%（11,721 → 9,007），因為大部分長度在 `content` 本身。真正的取捨發生在丟列。

送出 4 條，估計 2,221 token。第 5 條放進去就超過 3,000，所以停在 4 條；剩下的 779 token 是放不下一整條的零頭，**不拿來塞半條**。

`fit_budget()` 的 `count` 是可替換的參數：預設用粗估；拿到目標模型的 tokenizer 時，傳 `count=lambda s: len(tok.encode(s))` 進去即可，其他程式不用動。

## Workshop：誰被丟掉了？

### 任務與時間

**35–40 分鐘：讀丟棄清單。** 看第三段輸出的「丟掉 12 條」。第一個被丟掉的是**職業安全衛生法第 6 條**。用下列程式印出它的內容：

```python
# Workshop 用，本節測試不涵蓋這段
import pandas as pd
df = pd.read_json("data/articles.jsonl", lines=True, dtype=False, convert_dates=False)
print(df.query("pcode == 'N0060001' and slug == '6'")["content"].iloc[0])
```

它規定雇主應有防止墜落等危害的設備與措施；而「營造安全衛生設施標準」第 1 條寫著「本標準依職業安全衛生法**第六條第三項**規定訂定之」。也就是說，被送出的 4 條細則，**母法依據正是被丟掉的這一條**。判斷：對「墜落」這個問題，丟掉它合理嗎？

**40–47 分鐘：換一種排序。** 依「墜落出現次數」排序，偏好的是**提到很多次**的條文，不是**最重要**的條文。改用下列任一種排序，各跑一次 `fit_budget()`，比較送出哪幾條：

1. **短的優先**：新增 `hits["length"] = hits["content"].str.len()`，以 `-length` 為 `rank_by`（越短越前面）。
2. **母法優先**：新增一個欄位，`職業安全衛生法` 為 1、其他為 0，以它排序。

**47–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫「把 DataFrame 轉成給 LLM 的 JSON，控制在 3,000 token 內」。檢查它的答案有沒有：`force_ascii=False`？丟掉的列有沒有紀錄？是不是用 `content.str[:200]` 這種截斷？

### 參考判讀

- **丟掉母法第 6 條不合理**，但這不是 `fit_budget()` 的錯，是**排序規則**的錯。`fit_budget()` 只負責「照你的順序裝到滿」；什麼最重要，要另外判斷。這也是為什麼丟棄清單一定要輸出——沒有清單，沒人會發現母法被丟了。
- 教師實測（2026-10-05，同上環境）：

  | 排序 | 送出 | 估計 token | 職安法第 6 條 |
  | --- | ---: | ---: | --- |
  | 墜落次數（本節預設） | 4 條 | 2,221 | 丟掉 |
  | 短的優先 | 9 條 | 2,986 | 丟掉 |
  | 母法優先 | 6 條 | 2,884 | **送出** |

- 「短的優先」能塞進更多條，但「多」不等於「好」：短條文常是定義或罰則，不一定回答得了問題；職安法第 6 條本身很長，在這個排序下一樣被丟。
- 「母法優先」是一種**領域規則**，要寫下規則來源（第 13 節的「可稽核規則」），不能只是你覺得。
- 用 `content.str[:200]` 截斷的版本「每條都放得進去」，看起來比較好，但會截掉但書與款項。若 AI 的版本這樣做，要求它改成整條取捨。
- 第三題若 AI 的 JSON 裡出現 `\u`，就是漏了 `force_ascii=False`。

### 驗收

- 能重現第一段的四個長度，並說出 `jsonl-ascii` 與 `markdown` 各自為什麼長。
- 能說出 Markdown 輸出為什麼是 171 行而不是 18 行，以及那些多出來的行少了什麼欄位。
- 兩種新排序都跑過，交一張表：排序方式、送出幾條、職安法第 6 條是否被送出、估計 token。
- AI 版本的三項檢查（`force_ascii`、丟棄紀錄、截斷）都有結論。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6、tabulate 0.10.0。本頁所有輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，輸出**逐字相同**。

> 版本陷阱（已處理）：若讀檔時沒寫 `convert_dates=False`，pandas 會把 `fetched_at` 轉成日期；pandas 2.x 寫回 JSON 時變成毫秒整數 `1791173123000`，3.0 寫回 ISO 字串。兩版長度因此不同。本節明確關掉日期轉換，讓輸出不依版本而變。

**token 數字的等級**：全部是**粗估**（`estimate_tokens()`），不是任何 tokenizer 的實測，也不是計費依據。粗估與真實 tokenizer 的對照，使用 LLM 課 `data/tokenizer-fixtures.json` 的教師實測（2026-10-05；本課複本在 `data/16-tokenizer/`）。

**界線**：本節不呼叫 LLM，不宣稱「哪種格式模型答得比較好」——那需要評測，屬 LLM 課第 07 節。本節只處理**長度**與**結構是否保留**這兩件可以直接驗證的事。本節**尚未實班試教**。

**舊教材**：舊版終點是 `df.to_dict()`，沒有序列化與預算概念（`to_json`／`to_markdown` 全課 0 次）；本節為新增。

**下一節**：第 17 節〈文字語料：切塊、多值與去識別〉——當單一條文就超過預算（本資料最長一條 935 字）時，就不能再「整條取捨」，要切塊。
