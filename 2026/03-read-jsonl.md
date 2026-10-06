# 03｜JSON／JSONL 與巢狀結構：接手爬蟲課的輸出

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 03 節：JSON／JSONL 與巢狀結構。**
> 本節接爬蟲課第 16 節〈交給下游〉丟過來的球：讀它交付的 JSONL、攤平 API 的巢狀分頁 JSON，並且**一路保留四個來源欄位**。
> 本節不是 JSON 語法課，也不重教分頁爬取——那是爬蟲課第 03、05 節。這裡只處理「檔案已經在你手上之後」的事。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：讀一份 JSONL 而不讓 pandas 改寫它的內容；把「一頁一個物件、條文在裡面一層」的 API 回應攤平成一列一條；說出每一列從哪個網址來，並用兩個來源互相核對。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–6 分鐘 | 爬蟲課交了什麼過來 | 四個來源欄位各回答什麼問題 |
| 6–16 分鐘 | 一行 `read_json`，再存回去 | 21 列被改寫，沒有任何錯誤 |
| 16–22 分鐘 | 先決定型別，再讀 | `dtype=False`、`convert_dates=False`、來源檢查 |
| 22–30 分鐘 | API 的巢狀 JSON | `json_normalize` 的 `record_path`／`meta`，照 `next` 走完 |
| 30–35 分鐘 | 兩個來源互相核對 | `merge(validate=…)` ＋ 內容雜湊 |
| 35–50 分鐘 | Workshop：全量 749 條 | 每部法規條數與可回溯檢查 |

先修：本課第 02 節；爬蟲課第 05 節（分頁）、第 14 節（驗證）、第 16 節（交給下游）。環境同第 02 節。

## 一、爬蟲課交了什麼過來

爬蟲課第 16 節的最後，每一筆條文都帶了四個來源欄位：

| 欄位 | 回答的問題 | 例子 |
| --- | --- | --- |
| `source_url` | 這筆從哪裡來？使用者要怎麼回頭核對？ | `…/v1/laws/N0020012/articles/1.html` |
| `fetched_at` | 什麼時候抓的？會不會已經過時？ | `2026-10-05T04:05:23+00:00` |
| `content_hash` | 內容有沒有變？兩份資料是不是同一個版本？ | 內容的 SHA-256 |
| `source_version` | 是網站哪一版的結構？ | `v1` |

這四欄對做表格的人來說「沒用」——不能加總、不能分組，畫圖也用不到。所以它們最常在資料處理這一層被丟掉。**一旦丟掉，下游的 LLM 就沒辦法附出處，也沒有人能判斷這筆資料新不新。**

本節的檔案：

```text
data/03-crawl/N0020012.jsonl      爬蟲課交付的格式：一行一條，21 條
data/03-api/N0020012/page-1.json  練習站 v1 API 原始回應：第 1 頁，20 條
data/03-api/N0020012/page-2.json  第 2 頁，1 條
```

選「大量解僱勞工保護法」是因為它小（21 條）、剛好跨兩頁，而且條次全是數字——這一點等一下會出事。`03-api/` 的兩個檔案與練習站線上回應**位元組完全相同**（2026-10-05 比對）。

## 二、一行 `read_json`，再存回去

AI 最常給的寫法：

```python
df = pd.read_json("data/03-crawl/N0020012.jsonl", lines=True)
```

讀進來、什麼都不改、直接存回去，看看檔案變成什麼樣子（後面第四段有完整程式）：

```text
== 1. 一行 read_json，再存回去 ==
21 列；slug=int64, fetched_at=datetime64[us, UTC]
存回去後 21 列被改寫，欄位：['fetched_at', 'slug']
第 1 列 slug '1' → 1；fetched_at '2026-10-05T04:05:23+00:00' → 1791173123000
```

**什麼都沒改，21 列全被改寫了。**

- **`slug` 從字串變整數**。這部法規的條次剛好全是數字，pandas 就猜成 `int64`。同樣的程式拿去讀勞動基準法（有 `9-1`），`slug` 會是字串——**同一支程式，換一份檔案，型別就不同**，這是第 02 節的老問題換了個格式出現。
- **`fetched_at` 從 ISO 字串變成 `1791173123000`**。`read_json` 看到欄名結尾是 `_at`，會自動把它轉成日期；`to_json` 預設再把日期寫成「1970 年起算的毫秒數」。人看不懂、時區資訊不見了，爬蟲課第 16 節特地要求的「ISO 8601 帶時區」就這樣被拆掉。pandas 3.0 會對這個預設值發出 `Pandas4Warning`，**但只是警告，檔案照樣寫出去**。

> 自動轉日期的規則是「欄名看起來像日期」：結尾是 `_at`、`_time`，開頭是 `timestamp`，或欄名就是 `modified`、`date`、`datetime`。你的欄位叫 `fetched_at`，剛好中招；叫 `updated` 或 `created_date` 的則不會被轉（教師實測）。**同樣是時間欄，有的被轉、有的不被轉，只看名字**——這正是不該依賴它的理由。

`content_hash` 沒有被改——但下游拿 `slug=1` 去跟別人的 `slug="1"` 合併時會對不上，拿 `1791173123000` 去顯示「資料抓取時間」時沒有人看得懂。

## 三、先決定型別，再讀

做法跟第 02 節一樣：**不讓 pandas 猜**。

```python
pd.read_json(path, lines=True, dtype=False, convert_dates=False)
```

- `dtype=False`：不推斷型別，JSON 裡是字串就是字串。
- `convert_dates=False`：不要看欄名就轉日期。**兩個要一起寫**——只寫 `dtype=False`，pandas 2.x 仍會把 `fetched_at` 轉成日期（實測 2.3.3）。

讀完做一次來源檢查（`check_provenance()`）：四欄都在、沒有空值、`fetched_at` 帶時區、`content_hash` 跟內容算出來的一致。雜湊對不上代表**檔案在交付之後被改過**，不管是誰改的，都不該當作原始資料往下送。

## 四、API 的巢狀 JSON

練習站的 API 一次回一頁，條文放在裡面一層：

```json
{
 "version": 1, "pcode": "N0020012", "name": "大量解僱勞工保護法",
 "page": 1, "total_pages": 2, "total": 21, "next": "page-2.json",
 "articles": [
  {"slug": "1", "article_no": "第 1 條", "chapter": "", "section": "", "content": "為保障勞工工作權…"},
  …
 ]
}
```

直接 `read_json` 會得到一張「怪表」：20 列，每一列的 `pcode`、`page`、`total` 都一樣，`articles` 欄裝的是一整個 dict。

`json_normalize` 是為這種結構設計的：

- `record_path="articles"`：**一列是什麼**——是 `articles` 裡的每一個元素。
- `meta=["pcode", "name", "total"]`：外層要帶下來的欄位。沒寫 `meta`，攤平後只剩條文本身的五欄，**你不會知道它是哪部法規的**。

分頁要照 `next` 走到 `None` 為止，不能寫死「2 頁」（爬蟲課第 14 節的 AI 就是寫死 `range(1, 5)` 被抓到）。走完再核對 `total`：API 自己說有 21 條，攤平後就必須是 21 列。

**API 版本沒有 `source_url`**——API 回應裡本來就沒有這個欄位。`flatten_api()` 幫每一列補上「它是從哪個 API 網址來的」。這不是條文頁的網址，但它是**真的取得這筆資料的地方**；寫一個看起來比較漂亮、但其實沒去抓過的網址，才是錯的。

以下為完整 `03_read_jsonl.py`，只讀 `data/03-crawl/` 與 `data/03-api/`，不寫檔、不連線。

<!-- demo: 03_read_jsonl.py -->
```python
"""第 03 節：接手爬蟲課的 JSONL 與 API 的巢狀 JSON，而且不弄丟來源。"""

import hashlib
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
CRAWL = DATA / "03-crawl" / "N0020012.jsonl"
API = DATA / "03-api" / "N0020012"
API_URL = "https://4-learn.github.io/crawler-playground/v1/api/laws/N0020012/"
PROVENANCE = ["source_url", "fetched_at", "content_hash", "source_version"]


def read_jsonl(path):
    """讀爬蟲課交付的 JSONL：不讓 pandas 猜型別、不讓它改寫時間字串。"""
    df = pd.read_json(path, lines=True, dtype=False, convert_dates=False)
    check_provenance(df)
    return df


def check_provenance(df):
    missing = [c for c in PROVENANCE if c not in df.columns]
    if missing:
        raise ValueError(f"缺少來源欄位 {missing}")
    empty = [c for c in PROVENANCE if df[c].isna().any() or (df[c] == "").any()]
    if empty:
        raise ValueError(f"來源欄位有空值 {empty}")
    no_tz = ~df["fetched_at"].str.contains(r"(?:[+-]\d\d:\d\d|Z)$")
    if no_tz.any():
        raise ValueError(f"fetched_at 沒有時區 {int(no_tz.sum())} 筆，例如 {df.loc[no_tz, 'fetched_at'].iloc[0]!r}")
    actual = df["content"].map(lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest())
    bad = actual != df["content_hash"]
    if bad.any():
        raise ValueError(f"content_hash 與內容不符 {int(bad.sum())} 筆")


def flatten_api(folder, first="page-1.json"):
    """從第一頁開始照 next 走完，把每頁的 articles 攤平成一列一條。"""
    frames, name, seen = [], first, set()
    while name:
        if name in seen:
            raise ValueError(f"next 形成迴圈：{name}")
        seen.add(name)
        page = json.loads((Path(folder) / name).read_text(encoding="utf-8"))
        rows = pd.json_normalize(page, record_path="articles", meta=["pcode", "name", "total"])
        rows["source_url"] = API_URL + name   # 這一列是從哪個網址來的
        frames.append(rows)
        name = page["next"]
    df = pd.concat(frames, ignore_index=True).rename(columns={"name": "law_name"})
    expected = int(df["total"].iloc[0])
    if len(df) != expected:
        raise ValueError(f"API 說 total={expected}，實際攤平 {len(df)} 條")
    return df.drop(columns="total")


if __name__ == "__main__":
    print("== 1. 一行 read_json，再存回去 ==")
    naive = pd.read_json(CRAWL, lines=True)
    print(f"{len(naive)} 列；slug={naive['slug'].dtype}, fetched_at={naive['fetched_at'].dtype}")
    original = [json.loads(line) for line in CRAWL.read_text(encoding="utf-8").splitlines()]
    written = [json.loads(line) for line in naive.to_json(orient="records", lines=True, force_ascii=False).splitlines()]
    changed = sorted({k for o, w in zip(original, written) for k in o if o[k] != w[k]})
    print(f"存回去後 {sum(o != w for o, w in zip(original, written))} 列被改寫，欄位：{changed}")
    print(f"第 1 列 slug {original[0]['slug']!r} → {written[0]['slug']!r}；"
          f"fetched_at {original[0]['fetched_at']!r} → {written[0]['fetched_at']!r}")

    print("\n== 2. 先決定型別，再讀 ==")
    crawl = read_jsonl(CRAWL)
    print(f"{len(crawl)} 列；slug={crawl['slug'].dtype}；來源欄位齊全，content_hash 全數相符")
    print(f"fetched_at 原樣保留：{crawl['fetched_at'].iloc[0]}")

    print("\n== 3. API 的巢狀 JSON ==")
    page1 = pd.read_json(API / "page-1.json")
    print(f"read_json 直接讀第 1 頁：{page1.shape[0]} 列 × {page1.shape[1]} 欄；articles 欄裝的是 {type(page1['articles'].iloc[0]).__name__}")
    api = flatten_api(API)
    print(f"照 next 走完攤平：{len(api)} 列；欄位 {list(api.columns)}")

    print("\n== 4. 兩個來源互相核對 ==")
    api["content_hash"] = api["content"].map(lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest())
    both = crawl.merge(api, on=["pcode", "slug"], suffixes=("_crawl", "_api"), validate="one_to_one")
    same = (both["content_hash_crawl"] == both["content_hash_api"]).sum()
    print(f"以 (pcode, slug) 對上 {len(both)} 條；內容雜湊相同 {same} 條")
    print(both[["slug", "source_url_crawl", "source_url_api"]].tail(2).to_string(index=False))
```

執行（在本目錄下）：

```bash
python3 03_read_jsonl.py
```

第二段之後的輸出：

```text
== 2. 先決定型別，再讀 ==
21 列；slug=str；來源欄位齊全，content_hash 全數相符
fetched_at 原樣保留：2026-10-05T04:05:23+00:00

== 3. API 的巢狀 JSON ==
read_json 直接讀第 1 頁：20 列 × 8 欄；articles 欄裝的是 dict
照 next 走完攤平：21 列；欄位 ['slug', 'article_no', 'chapter', 'section', 'content', 'pcode', 'law_name', 'source_url']

== 4. 兩個來源互相核對 ==
以 (pcode, slug) 對上 21 條；內容雜湊相同 21 條
slug                                                               source_url_crawl                                                                source_url_api
  20 https://4-learn.github.io/crawler-playground/v1/laws/N0020012/articles/20.html https://4-learn.github.io/crawler-playground/v1/api/laws/N0020012/page-1.json
  21 https://4-learn.github.io/crawler-playground/v1/laws/N0020012/articles/21.html https://4-learn.github.io/crawler-playground/v1/api/laws/N0020012/page-2.json
```

執行第一段時，pandas 3.0 還會在輸出最前面印一行 `Pandas4Warning: The default 'epoch' date format is deprecated…`——這就是上一段說的「只是警告」。

讀它的方式：

- 第 3 段：`read_json` 讀第 1 頁得到 **20 列**，不是 21——它只讀了一頁，而且不會告訴你還有下一頁。
- 第 4 段：兩份資料各自來自網頁和 API，**21 條全部對上，雜湊全部相同**，這才證明「攤平沒有弄丟或弄錯任何一條」。
- `merge(..., validate="one_to_one")`：如果任一邊的 `(pcode, slug)` 有重複，`merge` 會直接報錯，而不是默默產生多出來的列。第 14 節會詳細談這件事。
- 第 21 條的兩個來源網址都留著：一個是條文頁，一個是 API 第 2 頁。兩個都是真的。

## 五、什麼時候用 JSONL，什麼時候用 JSON

| | JSON（一個大物件） | JSONL（一行一個物件） |
| --- | --- | --- |
| 例子 | API 一頁的回應 | 爬蟲課的交付檔 |
| 讀一半壞掉 | 整個檔案讀不了 | 只壞那一行，其他行還能用 |
| 增量追加 | 要重寫整個檔案 | 在檔尾加一行 |
| pandas 讀法 | 常需要 `json_normalize` | `read_json(lines=True)` |
| 適合 | 一次性的結構化回應 | 一筆一筆累積的紀錄 |

爬蟲課選 JSONL 當交付格式，理由正是右欄。本課後面的資料都是 JSONL。

## Workshop：全量 749 條

### 任務與時間

**35–43 分鐘：讀全量。** 用 `read_jsonl()` 讀 `data/articles.jsonl`（9 部法規、749 條），輸出「每部法規有幾條」：

```python
# Workshop 起手式，本節測試不涵蓋這段
df = read_jsonl(DATA / "articles.jsonl")
print(df.groupby("law_name", sort=False).size())
```

然後回答：**用一行 `pd.read_json(..., lines=True)` 讀全量，`slug` 是什麼型別？為什麼跟第 1 段的 21 條不同？**

**43–50 分鐘：證明每一列都能回溯。** 寫一個檢查：每一列的 `source_url` 結尾必須是 `/{pcode}/articles/{slug}.html`。至少用兩種方式弄壞資料，證明你的檢查會擋下來（例如把某一列的 `slug` 改掉、把 `source_url` 改成空字串）。

### 參考判讀

- 每部法規條數（教師實測）：勞動基準法 98、性別平等工作法 50、勞工退休金條例 69、職業安全衛生法 61、就業服務法 85、勞資爭議處理法 67、大量解僱勞工保護法 21、勞工職業災害保險及保護法 109、營造安全衛生設施標準 189，合計 749。
- 一行 `read_json` 讀全量，`slug` 是 **`str`**——因為其他法規有 `9-1` 這種條次，整欄沒辦法當整數。**這是最危險的情況**：你用全量測試時一切正常，上線後某天只處理一部條次全是數字的法規，`slug` 就變成整數，合併開始對不上。看起來「沒問題」，不代表你的寫法沒問題，可能只是這份資料剛好沒踩到。
- 回溯檢查可以寫成 `df.apply(lambda r: r.source_url.endswith(f"/{r.pcode}/articles/{r.slug}.html"), axis=1).all()`。教師實測 749 列全部通過。若你的檢查在 `slug` 被改掉時**沒有**失敗，代表它只檢查了「網址存在」，沒有檢查「網址指向的是這一條」。
- 請 AI 寫「把 JSONL 讀成 DataFrame 並計算每部法規條數」時，常見答案是一行 `read_json`，並在最後 `to_csv` 只輸出 `law_name` 與條數——條數是對的，但若它順手把整張表存回 JSON，`fetched_at` 就會變成毫秒數。檢查 AI 的版本有沒有改寫你沒要求它改的欄位。

### 驗收

- 能重現第 2–4 段輸出，並說明 21 列為什麼在一行 `read_json` ＋ `to_json` 之後全被改寫。
- 每部法規條數正確，合計 749。
- 回答「全量讀進來 `slug` 是 `str`，為什麼這反而危險」。
- 回溯檢查至少擋下兩種你自己做出來的壞資料。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，差別只有：字串欄 dtype 顯示為 `object`、日期解析度為 `ns` 而非 `us`、不印 `Pandas4Warning`。其餘逐字相同。

**資料**：`03-api/` 兩頁與練習站線上 `v1/api/laws/N0020012/page-{1,2}.json` 位元組相同（2026-10-05 以 `cmp` 比對）；`03-crawl/N0020012.jsonl` 是 `articles.jsonl` 的子集。皆由 `tools/build_fixtures.py` 產生，雜湊記於 `data/MANIFEST.json`。

**界線**：本節不處理多層巢狀（`record_path` 給 list、`meta` 給巢狀路徑）——練習站沒有這種結構，硬造一份範例只會教出「為了用 API 而用」。若學員專題遇到，指向 pandas 文件即可。本節**尚未實班試教**。

**舊教材**：舊版 `read_json`／`json_normalize` 皆 0 次；本節為新增。

**下一節**：第 04 節〈該在資料庫做，還是拉進 pandas？〉——同一份條文已在爬蟲課第 16 節寫進 MariaDB，下一節從資料表讀，並討論「這件事該在 SQL 做，還是在 pandas 做」。
