# 17｜文字語料：切塊、多值與去識別

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 17 節：文字語料：切塊、多值與去識別。**
> 本節處理「一格裡面是一段長文字或一個 list」的資料：用條文長度的**分布**決定 chunk size、按換行切塊並保住回原文的座標；用 `explode` 攤開多值欄位並量它膨脹多少；把通報文字裡的人名與電話換掉，**再掃一次看還剩什麼**。
> 本節不是 RAG 課，不計算向量、不做檢索——那是 LLM 課第 16–23 節。這裡交出去的是：**有分布證據的切塊參數、攤平後可接回條文的引用、去識別後的殘留清單。**

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：用 `describe`／分位數說出一份語料「多長」，並據此提出 chunk size 與它要切幾條；說明為什麼按換行切比每 N 字一刀好、以及它仍會切壞什麼；用 `explode` 攤開 list 欄位並預測列數；做一次名冊比對＋regex 的去識別，並列出它**擋不到**的東西。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–8 分鐘 | 條文有多長？ | `describe`、分位數、最長五條 |
| 8–14 分鐘 | chunk size 從分布來 | 450 字：30 條要切 |
| 14–22 分鐘 | 怎麼切：一刀 vs 按換行 | 31 刀全切在一行中間；按換行仍有 19 塊看不到前文 |
| 22–28 分鐘 | 多值欄位：`explode` | 40 → 82 → 106 列；接回條文 |
| 28–35 分鐘 | 去識別與殘留 | 替換 67＋17 處；`reporter` 欄 42 列原封不動、名冊只掃到 40 列 |
| 35–50 分鐘 | Workshop：替你的法規挑 chunk size | 分布證據＋取捨 |

先修：本課第 03 節（JSONL）、第 14 節（`merge` 與 `validate`）、第 16 節（粗估 token）。環境同第 02 節。

## 一、條文有多長？

LLM 組要把 749 條法規做成 RAG 語料，問你：「chunk size 要設多少？」最常見的回答是「512 吧，大家都這樣設」。**這個數字跟你的資料一點關係都沒有。** 先看分布（後面第三段有完整程式）：

```text
== 1. 條文長度分布（字元） ==
count    749.0
mean     159.3
std      137.7
min        4.0
25%       57.0
50%      121.0
75%      215.0
max      935.0
分位數（進位）：p50 121、p90 326、p95 427、p99 665
  law_name article_no  chars
營造安全衛生設施標準     第 59 條    935
營造安全衛生設施標準     第 64 條    824
     就業服務法     第 40 條    778
營造安全衛生設施標準     第 23 條    764
   性別平等工作法     第 13 條    737
```

- **平均 159、中位數 121**：平均比中位數大，表示有一條長尾把平均拉高——61% 的條文短於平均（教師實測）。只報平均值會高估「典型條文」的長度。
- **最長 935 字**，是營造安全衛生設施標準第 59 條（鋼管施工架）。它裡面有一張用框線字元（`┌─┬`）畫的表格——這件事第三段會出事。
- **最短 4 字**：9 條是 `（刪除）`（第 09 節）。它們也會變成 chunk，檢索時可能被當成「相關條文」送給模型。要不要把它們留在語料裡，是你該問 LLM 組的問題，不是默默決定的事。

## 二、chunk size 從分布來

**chunk size 的意義是「多長以下的條文不切」**。設 p95，就是 95% 的條文整條成為一塊，5% 要切：

```text
== 2. chunk size 要多大？ ==
p90     326 字： 75 條（10.0%）超過、要切；一塊估計最多 392 token
p95     427 字： 37 條（4.9%）超過、要切；一塊估計最多 513 token
本節採用    450 字： 30 條（4.0%）超過、要切；一塊估計最多 540 token
p99     665 字：  8 條（1.1%）超過、要切；一塊估計最多 798 token
```

本節採用 **450 字**：比 p95 多一點、取整，749 條中 30 條（4.0%）要切。理由要寫得出來：

- 條文是**引用單位**。整條在同一塊裡，模型引用時才能說「依第 X 條」；被切開的條文，每一塊都只是一部分。所以要讓**絕大多數條文不被切**。
- 450 字約 540 token（第 16 節的保守粗估）。第 16 節的證據預算是 3,000 token，一次能放 5 塊以上。
- **再往上加不划算**：從 p95 加到 p99，要切的條文只從 37 降到 8，但每塊的上限從 513 變成 798 token——為了 29 條長條文，讓**每一次檢索**都帶著更大的塊。

這不是「正確答案」。如果下游用的 embedding 模型有更短的輸入上限，chunk size 要跟著它；那是 LLM 課第 16、18 節要決定的事。你交給他們的是**這張表**：每個候選值會切掉幾條。

## 三、怎麼切：一刀 vs 按換行

### 每 450 字一刀

AI 最常給的切法：

```python
chunks = [text[i:i + 450] for i in range(0, len(text), 450)]
```

```text
== 3. 切塊：直接每 450 字一刀 vs 依換行裝箱 ==
每 450 字一刀：780 塊；31 刀切在一行的中間
每一行一塊：2797 塊；中位數 36 字，最短 4 字（例如 '（刪除）'）
依換行裝箱 ≤450：780 塊，30 條被切成多塊；最長 447 字，每塊都接得回原文
     chunk_id article_no  chars              first
N0060014#59-1     第 59 條    423 雇主對於鋼管施工架之設置，應依下列規
N0060014#59-2     第 59 條    440 │                 
N0060014#59-3     第 59 條     70 前項內側以水平構件替換交叉拉桿之施工
第 2 塊以後共 31 塊：16 塊以款或目開頭（款 15、目 1），看不到前面的「應依下列規定辦理」；3 塊以「前項／第 N 項」開頭，看不到它指的那一項
表格被切成兩半的塊：['N0060014#59', 'N0060014#64']
```

讀它：

- **每 450 字一刀**：30 條長條文共被切了 31 刀，**31 刀全都落在一行的中間**——29 刀切在句子裡，另 2 刀切在第 59、64 條框線表格的某一行中間（教師實測）。「雇主應……但」與「……者，不在此限」被分到兩塊，各自檢索到時意思都不完整。
- **每一行一塊**：條文的「項」「款」以換行分隔，按換行切就不會切在句子中間。但會切出 2,797 塊，中位數 36 字——「一、使用國家標準 CNS 4750 型式之施工架」這一行**不知道自己在講什麼**，主詞在上一行的「雇主對於鋼管施工架之設置，應依下列規定辦理：」。
- **按換行裝箱（本節做法）**：依換行切開，再把相鄰的行裝進不超過 450 字的塊。短條文仍是一整塊；長條文在行與行之間切。780 塊，最長 447 字。

`chunk_articles()` 做完會**接回去核對**：同一條的所有塊用 `\n` 接起來，必須等於原文，否則直接報錯。每一塊帶 `pcode`、`slug`、`source_url` 和 `chunk_id`（`N0060014#59-2`）——這是 LLM 課第 18 節說的「回到原文的座標」，也是第 15 節「可回溯的鍵」的同一件事。

### 按換行也會切壞的兩件事

- **孤兒塊：看不到前文**：被切開的 30 條中，第 2 塊以後共 31 塊，其中 **19 塊離開前文就讀不懂**：
  - **16 塊以款或目開頭**——15 塊以「款」（`七、護欄前方二公尺內之樓…`）、1 塊以「目」（`（三）踏腳桁之一端…`）開頭。它看不到第 1 塊的「雇主對於……應依下列規定辦理」，主詞不見了。
  - **3 塊以「前項／前 N 項／第 N 項」開頭**：`前項內側以水平構件替換交叉拉桿之施工架…`、`前四項之型式驗證實施程序…`、`第一項醫療機構之認可條件…`。「前項」指的那一項在上一塊，這一塊單獨被檢索到時，模型不知道「前項」是什麼。
  - 其餘 12 塊以一般句子開頭（例如 `積欠工資墊償基金，由中央主管機關…`），或是表格框線（下一點）。本節的 regex 只認得塊的開頭；塊中間的指涉（例如 `雇主依前三項所為之適當措施…`、`加徵前項滯納金…`、塊內第二行的 `五、前二款…`）同樣指向別處，沒有算進來，所以 19 是**下限**。

  常見的補法是在每塊前面重複條文的第一行或標題，這會讓塊變長——是取捨，不是免費的。
- **表格被切成兩半**：第 59、64 條的框線表格在兩塊中間斷開：第 59 條第 2 塊開頭是一行 `│` 加空白，第 64 條第 2 塊開頭是一行 `├───┼` 框線。對 LLM 來說，那是一段看不懂的符號。表格要當成一個不可切的單位，或改寫成文字；本節不實作，只把它**找出來**（`┌` 和 `└` 數量不等的塊）。

## 四、多值欄位：`explode`

虛驚通報 `near-miss-reports.jsonl` 有兩個 list 欄位：`tags`（例如 `["墜落", "施工架", "安全帶"]`）和 `related_articles`（例如 `["N0060014#19", "N0060014#17"]`）。

```text
== 4. 多值欄位：explode 的列膨脹 ==
把 list 欄當字串：.str.split('#') 得到 40/40 個 NaN；tags.str.contains('墜落') 加總 = 0.0，沒有錯誤訊息
通報 40 筆 → explode tags 82 列 → 再 explode related_articles 106 列
「墜落」：explode 兩次後數到 16 列；實際是 8 筆通報
related_articles：42 個引用接回條文，全部對上；另有 6 筆通報是空 list（explode 後變 NaN）
related_articles  article_no
N0060014#11-1     第 11-1 條       7
N0060014#144      第 144 條       10
N0060014#17       第 17 條         8
N0060014#19       第 19 條         8
N0060014#24       第 24 條         9
```

- **把 list 欄當字串用，不會報錯**。`.str.split("#")` 對 list 回傳 NaN——40 筆全是；`.str.contains("墜落")` 也是全 NaN，加總起來是 `0.0`。AI 寫的程式如果這樣做，結果是「沒有任何通報提到墜落」，而且**沒有任何錯誤訊息**。pandas 2.3.3 與 3.0.6 行為相同（教師實測）。
- **`explode` 一欄，列數變成「list 元素總數」**：40 筆 → 82 列。再對另一欄 explode，會變成**兩個 list 的乘積**：106 列。第 14 節的 fan-out 又出現了：在 106 列上數「墜落」得到 16，實際只有 8 筆通報——一筆通報有 2 個引用，它的「墜落」標籤就被數了 2 次。**一次只 explode 一個欄位**，要回答「幾筆通報」就回到原表數。
- **空 list 變成 NaN**：6 筆通報沒有引用任何條文（滑倒），explode 後是一列 NaN，不是消失。`link_articles()` 先把它們數出來，再丟掉。
- **拆鍵、接回條文**：`'N0060014#19'` 用 `str.split("#", expand=True)` 拆成 `pcode`、`slug`，再 `merge(..., validate="many_to_one", indicator=True)` 接回 `articles.jsonl`。`slug` 是字串（第 03 節），`11-1` 不會出事。42 個引用全部對上；引用了不存在的條文會直接報錯。

## 五、去識別與殘留

通報是主管手寫的自由文字，裡面有人名、電話、工號（全部虛構）。這份文字如果要進 RAG 語料，至少要先去識別。

`deidentify()` 用兩種方法：

- **人名：拿名冊比對**。`workers.csv` 有 60 個名字，長的先比（避免短名字先換掉長名字的一部分），換成 `〔姓名〕`。
- **電話：regex**。`0900-873-763`、`0912345678`、`(02)2345-6789` 三種寫法都要抓。

為了測「名冊外的人」，Demo 在**記憶體中**加了兩筆假通報（X001、X002，不寫檔）。替換之後，**再用另一組規則掃一次**：

```text
== 5. 去識別：換掉了什麼、還剩什麼 ==
人名替換 67 處、電話替換 17 處
殘留掃描（列數）： {'text：名冊人名': 0, 'text：像電話的數字': 0, 'text：工號': 7, 'reporter：名冊人名': 40, 'reporter：像電話的數字': 0, 'reporter：工號': 0}
reporter 欄共 42 列：名冊掃描抓到 40 列，另 2 列不在名冊、掃不到：['陳志明']（X001、X002）
改用「姓氏＋兩字」regex 掃條文語料：誤判 85 處，例如 ['許可期', '許可及', '許可者']
R036：〔姓名〕（工號 W002）在鋼構組立進場時未戴安全帽，由警衛攔下。通報人：〔姓名〕（〔電話〕）。
X001：水電包商的張美華師傅在二樓開口旁作業未扣安全帶，聯絡電話〔電話〕。
X002：外部稽核發現開口護欄缺口，請洽 〔電話〕 安衛室。
```

人名換了 67 處、電話 17 處，看起來很徹底。殘留掃描卻說：

- **`reporter` 欄 42 列全部原封不動**——`deidentify()` 只處理了 `text` 欄。通報人是誰，原封不動留在旁邊。去識別要以**整列**為單位，不是只處理「看起來是自由文字」的那一欄。注意殘留掃描只報 40：42 列中 40 列是名冊上的人名，**另 2 列（X001、X002 的通報人「陳志明」）不在名冊，掃描掃不到**——這是下面「名冊外的人掃不到」的第二個實例，只是這次發生在掃描、不是替換。
- **工號還在 7 列**：`〔姓名〕（工號 W002）`。名字換掉了，但 `W002` 拿去對名冊就是李雅婷。**能指回一個人的不只名字。**
- **名冊外的人掃不到**：X001 的「張美華師傅」原封不動。她是水電包商，不在名冊上；名冊比對**只換得掉你已經知道的名字**。殘留掃描也是用名冊，所以 `text` 欄的掃描結果是 0；`reporter` 欄的「陳志明」同理，掃描只數到 40、不是 42。Demo 另外印出「reporter 不在名冊的列數」才讓這 2 列現形——**掃描說「沒有」，不代表真的沒有。**
- **那用 regex 抓「姓氏＋兩個字」呢？** 拿同一個 regex 掃條文語料，誤判 85 處（`許可期`、`許可及`…）；而且名冊的姓氏裡沒有「張」，張美華一樣抓不到。中文人名沒有可靠的 regex。

所以去識別的交付物不是「已去識別的檔案」，而是「**換掉了什麼、用什麼方法、已知殘留什麼**」的清單。最安全的做法仍是 MariaDB 課的原則：語料**一開始就用合成資料**。另外，**向量不等於匿名化**——把這段文字轉成 embedding，人名與工號的資訊仍可能被還原或比對出來，不能因為「存的是向量」就放寬資料使用限制。

以下為完整 `17_text_corpus.py`，只讀 `data/`，不寫檔、不連線。

<!-- demo: 17_text_corpus.py -->
```python
"""第 17 節：條文語料的長度分布與切塊、多值欄位的 explode、通報文字的去識別。"""

import math
import re
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
CHUNK = 450        # 字元；由第 2 段的分布決定（p95 ≈ 427，取整到 450）
PHONE = re.compile(r"\(?0\d{1,3}\)?[- ]?\d{3,4}-?\d{3,4}")
WORKER_ID = re.compile(r"W\d{3}")


def estimate_tokens(text):
    """沿用第 16 節的保守粗估：非 ASCII 字元與數字各算 1、其他 ASCII 算 0.5，再乘 1.2。"""
    heavy = sum(1 for ch in text if not ch.isascii() or ch.isdigit())
    return math.ceil((heavy + (len(text) - heavy) * 0.5) * 1.2)


def read_articles():
    return pd.read_json(DATA / "articles.jsonl", lines=True, dtype=False, convert_dates=False)


def pack_lines(text, size=CHUNK):
    """依換行（項、款）切開，再把相鄰的行裝進不超過 size 的塊；單一行超過 size 才會單獨成塊。"""
    chunks, cur = [], ""
    for line in text.split("\n"):
        candidate = line if not cur else cur + "\n" + line
        if len(candidate) <= size or not cur:
            cur = candidate
        else:
            chunks.append(cur)
            cur = line
    chunks.append(cur)
    return chunks


def chunk_articles(articles, size=CHUNK):
    """一列一塊；每塊帶回到原條文的座標（pcode、slug、序號）與 source_url。"""
    out = articles[["pcode", "law_name", "slug", "article_no", "source_url", "content"]].copy()
    out["chunk"] = out["content"].map(lambda t: pack_lines(t, size))
    out["n_chunks"] = out["chunk"].map(len)
    out = out.explode("chunk", ignore_index=True)
    out["chunk_no"] = out.groupby(["pcode", "slug"]).cumcount() + 1
    out["chunk_id"] = out["pcode"] + "#" + out["slug"] + "-" + out["chunk_no"].astype(str)
    rebuilt = out.groupby(["pcode", "slug"], sort=False)["chunk"].agg("\n".join)
    original = articles.set_index(["pcode", "slug"])["content"].loc[rebuilt.index]
    if not (rebuilt == original).all():
        raise ValueError("切塊後接不回原文")
    return out.drop(columns="content")


def link_articles(reports, articles):
    """related_articles 是 list：explode 成一列一個引用，拆成 pcode／slug 接回條文。空 list 會變成 NaN，先標出來。"""
    refs = reports[["report_id", "related_articles"]].explode("related_articles")
    no_ref = refs["related_articles"].isna()
    refs = refs[~no_ref].copy()
    bad = ~refs["related_articles"].str.fullmatch(r"N\d{7}#\d+(?:-\d+)?")
    if bad.any():
        raise ValueError(f"related_articles 格式不對：{refs.loc[bad, 'related_articles'].iloc[0]!r}")
    refs[["pcode", "slug"]] = refs["related_articles"].str.split("#", expand=True)
    linked = refs.merge(articles[["pcode", "slug", "law_name", "article_no"]], on=["pcode", "slug"],
                        how="left", validate="many_to_one", indicator=True)
    missing = linked["_merge"] != "both"
    if missing.any():
        raise ValueError(f"引用的條文不存在：{linked.loc[missing, 'related_articles'].iloc[0]!r}")
    return linked.drop(columns="_merge"), int(no_ref.sum())


def deidentify(reports, roster_names):
    """名冊比對換掉人名、regex 換掉電話；回傳新表，不改原表。"""
    names = sorted(set(roster_names), key=len, reverse=True)
    pattern = "|".join(map(re.escape, names))
    out = reports.copy()
    out["text"] = out["text"].str.replace(pattern, "〔姓名〕", regex=True).str.replace(PHONE, "〔電話〕", regex=True)
    return out


def residuals(df, columns, roster_names):
    """去識別之後再掃一次：還有幾列可能指回某個人。只掃得到「已知的樣子」，掃不到名冊外的人名。"""
    names = "|".join(map(re.escape, sorted(set(roster_names), key=len, reverse=True)))
    found = {}
    for col in columns:
        s = df[col].astype(str)
        found[f"{col}：名冊人名"] = int(s.str.contains(names).sum())
        found[f"{col}：像電話的數字"] = int(s.str.contains(r"\d{3,4}[- ]?\d{3,4}").sum())
        found[f"{col}：工號"] = int(s.str.contains(WORKER_ID).sum())
    return found


def mid_line_cuts(text, size=CHUNK):
    """每 size 字一刀時，有幾刀不是落在換行上。"""
    return sum(text[p - 1] != "\n" and text[p] != "\n" for p in range(size, len(text), size))


if __name__ == "__main__":
    articles = read_articles()
    length = articles["content"].str.len()

    print("== 1. 條文長度分布（字元） ==")
    print(length.describe().round(1).to_string())
    q = length.quantile([0.5, 0.9, 0.95, 0.99]).map(math.ceil)    # 無條件進位：p95=427 代表 95% 的條文 ≤427 字
    print("分位數（進位）：" + "、".join(f"p{round(p * 100)} {v}" for p, v in q.items()))
    longest = articles.assign(chars=length).nlargest(5, "chars")
    print(longest[["law_name", "article_no", "chars"]].to_string(index=False))

    print("\n== 2. chunk size 要多大？ ==")
    for label, size in [("p90", q[0.9]), ("p95", q[0.95]), ("本節採用", CHUNK), ("p99", q[0.99])]:
        over = int((length > size).sum())
        print(f"{label:6} {size:>4} 字：{over:>3} 條（{over / len(articles):.1%}）超過、要切；"
              f"一塊估計最多 {estimate_tokens('字' * size)} token")

    print("\n== 3. 切塊：直接每 450 字一刀 vs 依換行裝箱 ==")
    fixed = articles["content"].map(lambda t: [t[i:i + CHUNK] for i in range(0, len(t), CHUNK)]).explode()
    mid_line = int(articles["content"].map(mid_line_cuts).sum())
    print(f"每 {CHUNK} 字一刀：{len(fixed)} 塊；{mid_line} 刀切在一行的中間")
    lines = articles["content"].str.split("\n").explode()
    print(f"每一行一塊：{len(lines)} 塊；中位數 {lines.str.len().median():.0f} 字，"
          f"最短 {lines.str.len().min()} 字（例如 {lines[lines.str.len() == lines.str.len().min()].iloc[0]!r}）")
    chunks = chunk_articles(articles)
    size = chunks["chunk"].str.len()
    split = int((chunks.drop_duplicates(["pcode", "slug"])["n_chunks"] > 1).sum())
    print(f"依換行裝箱 ≤{CHUNK}：{len(chunks)} 塊，{split} 條被切成多塊；最長 {size.max()} 字，每塊都接得回原文")
    print(chunks.loc[chunks["pcode"].eq("N0060014") & chunks["slug"].eq("59"), ["chunk_id", "article_no"]]
          .assign(chars=size, first=chunks["chunk"].str[:18]).to_string(index=False))
    later = chunks[chunks["chunk_no"] > 1]
    kuan = later["chunk"].str.match(r"[一二三四五六七八九十]+、")          # 款：一、二、
    mu = later["chunk"].str.match(r"（[一二三四五六七八九十]+）")           # 目：（一）（二）
    xiang = later["chunk"].str.match(r"(?:前|第[一二三四五六七八九十]+)\S*項")  # 前項、前三項、第一項
    print(f"第 2 塊以後共 {len(later)} 塊：{int((kuan | mu).sum())} 塊以款或目開頭（款 {int(kuan.sum())}、目 {int(mu.sum())}），"
          f"看不到前面的「應依下列規定辦理」；{int(xiang.sum())} 塊以「前項／第 N 項」開頭，看不到它指的那一項")
    broken = chunks[chunks["chunk"].str.count("┌") != chunks["chunk"].str.count("└")]
    print(f"表格被切成兩半的塊：{sorted(set(broken['pcode'] + '#' + broken['slug']))}")

    print("\n== 4. 多值欄位：explode 的列膨脹 ==")
    reports = pd.read_json(DATA / "events" / "near-miss-reports.jsonl", lines=True, dtype=False, convert_dates=False)
    as_text = reports["related_articles"].str.split("#")
    print(f"把 list 欄當字串：.str.split('#') 得到 {int(as_text.isna().sum())}/{len(reports)} 個 NaN；"
          f"tags.str.contains('墜落') 加總 = {reports['tags'].str.contains('墜落').sum()}，沒有錯誤訊息")
    tags = reports.explode("tags")
    both = tags.explode("related_articles")
    print(f"通報 {len(reports)} 筆 → explode tags {len(tags)} 列 → 再 explode related_articles {len(both)} 列")
    print(f"「墜落」：explode 兩次後數到 {int((both['tags'] == '墜落').sum())} 列；實際是 {int(reports['tags'].map(lambda t: '墜落' in t).sum())} 筆通報")
    linked, no_ref = link_articles(reports, articles)
    print(f"related_articles：{len(linked)} 個引用接回條文，全部對上；另有 {no_ref} 筆通報是空 list（explode 後變 NaN）")
    print(linked.groupby(["related_articles", "article_no"]).size().rename("引用次數").to_string())

    print("\n== 5. 去識別：換掉了什麼、還剩什麼 ==")
    roster = pd.read_csv(DATA / "events" / "workers.csv", dtype=str, keep_default_na=False)
    extra = pd.DataFrame([  # 在記憶體中加兩筆名冊外的通報（不寫檔）
        {"report_id": "X001", "reporter": "陳志明", "text": "水電包商的張美華師傅在二樓開口旁作業未扣安全帶，聯絡電話0912345678。"},
        {"report_id": "X002", "reporter": "陳志明", "text": "外部稽核發現開口護欄缺口，請洽 (02)2345-6789 安衛室。"},
    ])
    sample = pd.concat([reports[["report_id", "reporter", "text"]], extra], ignore_index=True)
    clean = deidentify(sample, roster["name"])
    print(f"人名替換 {int(clean['text'].str.count('〔姓名〕').sum())} 處、電話替換 {int(clean['text'].str.count('〔電話〕').sum())} 處")
    print("殘留掃描（列數）：", residuals(clean, ["text", "reporter"], roster["name"]))
    outside = clean.loc[~clean["reporter"].isin(roster["name"]), "reporter"]
    print(f"reporter 欄共 {len(clean)} 列：名冊掃描抓到 {len(clean) - len(outside)} 列，另 {len(outside)} 列不在名冊、掃不到："
          f"{sorted(set(outside))}（{'、'.join(clean.loc[outside.index, 'report_id'])}）")
    guess = f"[{''.join(sorted(set(roster['name'].str[0])))}][\u4e00-\u9fff]{{2}}"   # 「名冊姓氏＋兩個字」
    hits = articles["content"].str.findall(guess).explode().dropna()
    print(f"改用「姓氏＋兩字」regex 掃條文語料：誤判 {len(hits)} 處，例如 {hits.value_counts().index[:3].tolist()}")
    for rid in ["R036", "X001", "X002"]:
        print(f"{rid}：{clean.loc[clean['report_id'] == rid, 'text'].iloc[0]}")
```

執行（在本目錄下）：

```bash
python3 17_text_corpus.py
```

## Workshop：替一部法規挑 chunk size

### 任務與時間

**35–42 分鐘：分法規看分布。** 全部 749 條的 p95 是 427，但每部法規不一樣。輸出每部法規的條數、中位數、p95、最大值：

```python
# Workshop 起手式，本節測試不涵蓋這段
from my_corpus import read_articles, chunk_articles   # 先把本節 Demo 存成 my_corpus.py
df = read_articles()
length = df["content"].str.len()
print(length.groupby(df["law_name"], sort=False).describe(percentiles=[0.5, 0.95]).round(0))
```

回答：如果 LLM 組只做「營造安全衛生設施標準」問答，450 還適合嗎？用分布證據說明。

**42–46 分鐘：換 chunk size 比較。** 用 `chunk_articles(df, size)` 分別跑 300、450、500，交一張表：總塊數、被切成多塊的條文數、以款或目開頭的孤兒塊數、以「前項／第 N 項」開頭的孤兒塊數、最長一塊幾字。

**46–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫「把通報文字去識別化」。拿它的版本跑 Demo 第 5 段的 `residuals()`，並檢查：(1) `reporter` 欄處理了沒？(2) 工號 `W002` 還在嗎？(3) 用 X001 的「張美華」測，它擋得住嗎？(4) 它是不是宣稱「已完成匿名化」？

### 參考判讀

- 分法規的 p95（教師實測）：營造安全衛生設施標準 **524**、就業服務法 501、職業安全衛生法 496、性別平等工作法 452、勞動基準法 429、大量解僱勞工保護法 407、勞工職業災害保險及保護法 392、勞資爭議處理法 314、勞工退休金條例 294。**營造標準的 p95 高於 450**——用全語料的 450 去切它，189 條中有 12 條（6.3%）會被切，比全語料的 4.0% 高。只做這部法規時，chunk size 應該依它自己的分布重訂。全語料的 p95 是「平均起來」的 p95，不是每一部法規的。
- 換 chunk size（教師實測）：

  | chunk size | 總塊數 | 被切成多塊的條文 | 款或目開頭（款＋目） | 前項／第 N 項開頭 | 最長一塊 |
  | ---: | ---: | ---: | ---: | ---: | ---: |
  | 300 | 860 | 91 | 50（40＋10） | 20 | 300 |
  | 450 | 780 | 30 | 16（15＋1） | 3 | 447 |
  | 500 | 773 | 24 | 12（10＋2） | 3 | 500 |

  從 450 到 500，被切的條文只少 6 條；從 450 降到 300，被切的條文變 3 倍、款或目開頭的孤兒塊變 3 倍、「前項」開頭的變 6 倍多（3 → 20）。這張表就是「分布證據」：說得出每個選項會切壞多少。
- AI 的去識別版本最常見的漏洞：只處理 `text` 欄、沒處理工號、用固定格式 regex 抓電話（只抓 `09xx-xxx-xxx`，漏掉 `0912345678` 或市話）、以及**宣稱「已匿名化」**。去識別只能說「已替換已知的 X 類資訊」，名冊外的人名本節已示範擋不到。
- 若 AI 建議「轉成向量存起來就安全了」：這違反 MariaDB 課與本課共同的原則——向量不等於匿名化。

### 驗收

- 能重現 Demo 第 1–2 段，並用分位數說明為什麼選 450、它會切幾條。
- 能說出按換行切仍會切壞的兩件事（孤兒塊、表格），以及各自影響幾塊（450 字：款或目開頭 16 塊＝款 15＋目 1、「前項／第 N 項」開頭 3 塊；表格 2 條）。
- 能預測 `explode` 後的列數（82、106），並解釋為什麼在 106 列上數「墜落」會得到 16 而不是 8。
- 去識別的交付包含殘留清單：至少列出 `reporter` 欄（42 列，其中 2 列名冊掃不到）、工號、名冊外人名三項。
- AI 版本的四項檢查都有結論。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁所有輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，標準輸出**逐字相同**（包括 list 欄位上 `.str.split`／`.str.contains` 回傳 NaN 的行為）。

**token 數字的等級**：「一塊估計最多 N token」是以第 16 節的**粗估**計算「全部是中文字的 N 字」，不是 tokenizer 實測。

**資料**：`articles.jsonl` 條文取自爬蟲課練習站，可能經刻意修改，**不具法律效力**。`near-miss-reports.jsonl`、`workers.csv` 為 `tools/build_events.py` 產生的**合成資料**，人名、電話、工號全部虛構。Demo 第 5 段的 X001、X002 在記憶體中建立，不寫入任何檔案；「張美華」「(02)2345-6789」「0912345678」同為虛構。

**界線**：

- 本節的「字元數」是 Python `len()`，框線表格的全形空白與符號也算。chunk size 用字元不用 token，是因為下游模型未定；換成真實 tokenizer 時，分布的形狀會相同但數字會變。
- 本節不實作「表格不可切」與「孤兒塊補主詞」，只量出影響範圍，交給 LLM 課第 18 節決定。孤兒塊只用**開頭**判斷（款、目、「前項／第 N 項」），句中的「前二款」「依前條」沒算，19 是下限。
- 去識別只示範**替換**（`〔姓名〕`），不示範假名化（同一人換成同一代號）。假名化保留了「同一人出現幾次」的資訊，也就保留了被重新識別的風險，要另外評估。
- 不計算任何向量；「向量不等於匿名化」沿用 MariaDB 課原則，本節未實測。
- 本節**尚未實班試教**。

**舊教材**：無。本節為新增（課綱「新增待撰」）；舊版 `explode` 與文字長度統計皆 0 次。

**下一節**：第 18 節〈從 JSONL 到 LLM 可讀摘要〉——把第 02–17 節的關卡串成一支可重跑的程式：讀取、清理、驗證、彙總、濃縮、序列化，並故意餵壞資料證明會被擋下。
