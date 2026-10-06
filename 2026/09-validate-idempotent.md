# 09｜資料驗證與冪等：壞資料要被擋下，重跑要一樣

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 09 節：資料驗證與冪等。**
> 本節把爬蟲課第 2 版練習站的增量交付，套到第 1 版的 749 條上。兩件事要同時成立：**壞資料必須讓流程停下來**；**同一批資料送兩次、甚至舊資料晚到，結果都不能變。**
> 本節不是 pytest 入門（爬蟲課第 14 節已教），也不是資料庫 upsert（爬蟲課第 16 節已教）。這裡處理的是**在 pandas 這一層**，這兩件事怎麼做、會在哪裡默默失敗。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：把欄位、格式、白名單、跨欄一致性、唯一性寫成一個「不過就停」的驗證；說明 `concat`＋`drop_duplicates` 為什麼不冪等；用業務鍵與時間戳寫出重跑結果相同的合併，並用指紋證明它；指出增量資料看不到什麼。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–5 分鐘 | 情境：第二次交付來了 | 增量檔 5 條 |
| 5–14 分鐘 | 天真的合併 | 754 → 759 列；`keep` 決定誰贏，而且會被舊資料翻盤 |
| 14–22 分鐘 | 驗證：不過就停 | `validate()`：一次列出所有問題 |
| 22–30 分鐘 | 冪等的合併 | `apply_batch()`：較新的勝出，三次指紋相同 |
| 30–35 分鐘 | 增量看不到的事 | 對帳找出被刪的條文 |
| 35–50 分鐘 | Workshop：寫成 pytest，並弄壞它 | 一組會擋下壞資料的測試 |

先修：本課第 03、08 節；爬蟲課第 14 節（pytest 驗證）、第 15 節（變動偵測）、第 16 節（upsert）。環境同第 02 節。

## 一、情境：第二次交付來了

上週你收到第 1 版全量：`data/articles.jsonl`，749 條。這週爬蟲組只送「有變的」過來：

```text
data/09-batches/v2-changes.jsonl   5 條：修改 4、新增 1，source_version=v2，fetched_at=2026-10-12
data/09-batches/v2-laws.json       練習站 v2 API 的法規總覽（每部法規現在有幾條）
```

這 5 條的內容與練習站線上第 2 版 API 逐條相同（2026-10-05 比對）。練習站第 2 版其實還**刪了一條**，但增量檔裡沒有它——增量檔的格式是「一行一條條文」，被刪的條文沒有內容可以寫。這件事第五段再處理。

你的任務：把 5 條套上去，得到「現在的條文」。而且這支程式會被排程每天跑，**同一批可能被重送，舊的全量也可能被誤送**。

## 二、天真的合併

AI 最常給的寫法：

```python
merged = pd.concat([v1, v2]).drop_duplicates(["pcode", "slug"])
```

拆開來看（後面第四段有完整程式）：

```text
== 1. 天真的合併：concat ＋ drop_duplicates ==
concat 一次 754 列，同一批再跑一次 759 列
keep='first'         750 列；含 v2 修正的條文 1 條
keep='last'          750 列；含 v2 修正的條文 5 條
keep='last' 後又重送 v1  750 列；含 v2 修正的條文 1 條
```

三個問題，**全部不會報錯**：

1. **只有 `concat` 不冪等**：同一批跑兩次，754 變 759。每跑一次多 5 列。
2. **`keep='first'`（預設值）讓舊資料贏**：750 列看起來對了（749＋新增 1），但 4 條修改全被丟掉，留下的是 v1 舊內容；唯一一條 v2 是新增的那條，因為它沒有舊版可以搶。**列數對，內容錯。**
3. **`keep='last'` 只是讓「後到的」贏，不是讓「新的」贏**：某天排程重送了上週的 v1 全量，4 條修改就被舊內容蓋回去。順序是由「哪個檔案先被處理」決定的，不是由資料本身決定的。

爬蟲課第 16 節的 `ON DUPLICATE KEY UPDATE` 也是「後寫的贏」。它在「每天抓最新、依序寫入」的前提下是對的；本節要處理的是**前提不成立**的時候。

## 三、驗證：不過就停

在合併之前，先確定送進來的資料可以用。`validate()` 檢查：

| 檢查 | 類型 | 擋下什麼 |
| --- | --- | --- |
| 欄位齊全 | schema | 上游改了欄名 |
| 必填欄位非空（`chapter` 除外） | 必填 | 漏抓、空字串 |
| `pcode` 為 `N`＋7 位數、`slug` 為 `數字` 或 `數字-數字` | 格式 | 型別漂移（`1.0`）、亂碼 |
| `article_no` 等於 `第 {slug} 條` | **跨欄一致** | 兩欄來自不同條文 |
| `source_version` 屬於 `{v1, v2}` | 白名單 | 來路不明的版本 |
| `fetched_at` 帶時區 | 格式 | 無法比較先後的時間 |
| `content_hash` 等於內容的 SHA-256 | **跨欄一致** | 內容被改過卻沒重算雜湊 |
| `(pcode, slug)` 不重複 | 唯一性 | 同一條送了兩次 |

**`chapter` 為什麼不是必填？** 第一版的 `validate()` 把它列為必填，結果第 1 版全量 749 條**驗證失敗**：「必填欄位有空值：21 筆，例如 N0020012/1」。大量解僱勞工保護法沒有分章，`chapter` 本來就是空的——第 02、08 節講過，**這是事實，不是缺值**。驗證規則寫錯，跟資料寫錯一樣會讓流程停下來；寫規則前要先看過資料。

三個設計：

- **失敗就拋例外，不是印 warning**。印 warning 的驗證，在排程裡等於沒有驗證——沒有人在凌晨三點看 log。
- **一次列出所有問題**。只報第一個，上游修一個、送一次、再被擋一次，一批要來回好幾輪。
- **報出例子**。「3 筆有問題」不夠，要說是哪一條，上游才查得到。

故意做一批壞資料：一條拿掉時區、一條改了內容沒重算雜湊、一條送兩次：

```text
== 2. 壞資料要被擋下 ==
ValidationError: fetched_at 沒有時區：1 筆，例如 N0030001/24；content_hash 與內容不符：1 筆，例如 N0030001/38；業務鍵重複：2 筆，例如 N0030001/86-1
```

三種問題一次報出，各附一個例子。「業務鍵重複：2 筆」是因為重複的兩列都被標出來（`keep=False`）：你不知道哪一列才是對的，就不該替上游選。

## 四、冪等的合併

**冪等**：同一個操作做一次和做很多次，結果一樣。

`apply_batch()` 的規則：

1. 先驗證這一批，不過就停。
2. 以業務鍵 `(pcode, slug)` 比對現有資料：
   - 現有沒有 → 新增。
   - 這一批的 `fetched_at` **比較新** → 更新。
   - 一樣新或比較舊 → 略過。
   - **一樣新但內容不同** → 停下來。同一時間點有兩種內容，程式無法判斷誰對，要人來看。
3. 合併後再驗證一次結果。

`fetched_at` 先轉成帶時區的時間再比較（`utc=True`），不是比字串——`2026-10-12T12:00:00+08:00` 和 `2026-10-12T04:00:00+00:00` 是同一刻，字串卻不同。

**怎麼證明結果一樣？** 列數一樣不夠（第二段的 `keep='first'` 列數也對）。`fingerprint()` 把整張表依業務鍵排序後序列化、算雜湊：**任何一格不同，指紋就不同**；列的順序不同，指紋相同。

以下為完整 `09_validate_idempotent.py`，只讀 `data/`，不寫檔、不連線。

<!-- demo: 09_validate_idempotent.py -->
```python
"""第 09 節：壞資料要被擋下，同一批資料重跑要一樣。"""

import hashlib
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
KEY = ["pcode", "slug"]                      # 業務鍵：一部法規的一條條文
COLUMNS = ["pcode", "law_name", "slug", "article_no", "chapter", "content",
           "source_url", "fetched_at", "content_hash", "source_version"]
REQUIRED = [c for c in COLUMNS if c != "chapter"]   # 沒分章的法規 chapter 就是空的：那是事實，不是缺值
VERSIONS = {"v1", "v2"}


class ValidationError(ValueError):
    """驗證失敗就讓流程停下來；不是印一行 warning 然後繼續。"""


def read_batch(path):
    return pd.read_json(path, lines=True, dtype=False, convert_dates=False)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate(df):
    """一次列出所有問題（而不是只報第一個），任何一項不過就拋 ValidationError。"""
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValidationError(f"缺少欄位 {missing}")
    checks = {
        "必填欄位有空值": df[REQUIRED].isna().any(axis=1) | (df[REQUIRED] == "").any(axis=1),
        "pcode 格式": ~df["pcode"].str.fullmatch(r"N\d{7}", na=False),
        "slug 格式": ~df["slug"].str.fullmatch(r"\d+(?:-\d+)?", na=False),
        "article_no 與 slug 不一致": df["article_no"] != "第 " + df["slug"] + " 條",
        "source_version 不在白名單": ~df["source_version"].isin(VERSIONS),
        "fetched_at 沒有時區": ~df["fetched_at"].str.contains(r"(?:[+-]\d\d:\d\d|Z)$", na=False),
        "content_hash 與內容不符": df["content"].fillna("").map(sha) != df["content_hash"],
        "業務鍵重複": df.duplicated(KEY, keep=False),
    }
    problems = []
    for rule, bad in checks.items():
        if bad.any():
            first = df.loc[bad, KEY].iloc[0]
            problems.append(f"{rule}：{int(bad.sum())} 筆，例如 {first['pcode']}/{first['slug']}")
    if problems:
        raise ValidationError("；".join(problems))
    return df


def fingerprint(df):
    """整張表的指紋：同樣內容（不論列的順序）得到同樣的值，用來證明重跑結果一致。"""
    text = df.sort_values(KEY)[COLUMNS].to_json(orient="records", lines=True, force_ascii=False)
    return sha(text)[:12]


def apply_batch(current, batch):
    """以業務鍵 upsert：較新的 fetched_at 勝出；較舊或相同的重送不改變任何東西。"""
    validate(batch)
    old = current.set_index(KEY)
    report = {"新增": 0, "更新": 0, "略過（不比現有新）": 0}
    for row in batch.itertuples(index=False):
        key = (row.pcode, row.slug)
        if key not in old.index:
            report["新增"] += 1
            continue
        mine = old.loc[key]
        t_new = pd.Timestamp(row.fetched_at)
        t_old = pd.Timestamp(mine["fetched_at"])
        if t_new == t_old and row.content_hash != mine["content_hash"]:
            raise ValidationError(f"{key[0]}/{key[1]} 同一時間點有兩種內容，無法判斷誰對")
        report["更新" if t_new > t_old else "略過（不比現有新）"] += 1
    combined = pd.concat([current, batch], ignore_index=True)
    combined["_t"] = pd.to_datetime(combined["fetched_at"], utc=True, format="ISO8601")
    result = (combined.sort_values(KEY + ["_t"], kind="stable")
              .drop_duplicates(KEY, keep="last")
              .drop(columns="_t")
              .sort_values(KEY, kind="stable")
              .reset_index(drop=True))
    return validate(result), report


def reconcile(current, summary_path):
    """增量檔裝不下「刪除」：拿來源的條文總數對帳，對不上的列出來交給人判斷。"""
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    expected = pd.Series({i["code"]: i["articles"] for i in summary["items"]}, name="來源條文數")
    actual = current.groupby("pcode").size().rename("本地條文數")
    table = pd.concat([expected, actual], axis=1).fillna(0).astype(int)
    return table[table["來源條文數"] != table["本地條文數"]]


if __name__ == "__main__":
    v1 = validate(read_batch(DATA / "articles.jsonl"))
    v2 = read_batch(DATA / "09-batches" / "v2-changes.jsonl")
    print(f"v1 全量 {len(v1)} 條（驗證通過）；v2 增量 {len(v2)} 條，指紋 {fingerprint(v1)}\n")

    print("== 1. 天真的合併：concat ＋ drop_duplicates ==")
    once = pd.concat([v1, v2], ignore_index=True)
    twice = pd.concat([once, v2], ignore_index=True)
    print(f"concat 一次 {len(once)} 列，同一批再跑一次 {len(twice)} 列")
    first = once.drop_duplicates(KEY, keep="first")
    last = once.drop_duplicates(KEY, keep="last")
    replay = pd.concat([last, v1], ignore_index=True).drop_duplicates(KEY, keep="last")
    for label, df in [("keep='first'", first), ("keep='last'", last), ("keep='last' 後又重送 v1", replay)]:
        print(f"{label:20} {len(df)} 列；含 v2 修正的條文 {int((df['source_version'] == 'v2').sum())} 條")

    print("\n== 2. 壞資料要被擋下 ==")
    bad = v2.copy()
    bad.loc[0, "fetched_at"] = "2026-10-12 12:00:00"         # 少了時區
    bad.loc[1, "content"] = bad.loc[1, "content"] + "。"     # 改了內容卻沒重算雜湊
    bad = pd.concat([bad, bad.tail(1)], ignore_index=True)   # 同一條送了兩次
    try:
        apply_batch(v1, bad)
    except ValidationError as exc:
        print("ValidationError:", exc)

    print("\n== 3. 套用增量，然後重跑 ==")
    cur, report = apply_batch(v1, v2)
    print(f"第 1 次：{len(cur)} 條，{report}，指紋 {fingerprint(cur)}")
    cur2, report = apply_batch(cur, v2)
    print(f"第 2 次：{len(cur2)} 條，{report}，指紋 {fingerprint(cur2)}")
    cur3, report = apply_batch(cur2, v1)
    print(f"重送 v1：{len(cur3)} 條，{report}，指紋 {fingerprint(cur3)}")

    print("\n== 4. 對帳：增量檔看不到的刪除 ==")
    print(reconcile(cur3, DATA / "09-batches" / "v2-laws.json").to_string())
```

執行（在本目錄下）：

```bash
python3 09_validate_idempotent.py
```

第三段輸出：

```text
== 3. 套用增量，然後重跑 ==
第 1 次：750 條，{'新增': 1, '更新': 4, '略過（不比現有新）': 0}，指紋 813624872431
第 2 次：750 條，{'新增': 0, '更新': 0, '略過（不比現有新）': 5}，指紋 813624872431
重送 v1：750 條，{'新增': 0, '更新': 0, '略過（不比現有新）': 749}，指紋 813624872431
```

讀它的方式：

- **三次指紋相同**。同一批重送、舊的全量晚到，結果都沒變。這才叫冪等，不是「列數沒變」。
- 第 1 次的「新增 1、更新 4」與爬蟲課第 15 節比對出來的變動一致。
- **報告跟結果一樣重要**。「略過 749」告訴你：有人重送了舊資料。結果雖然沒壞，但上游流程有問題，值得去問。
- 開頭印的 v1 指紋是 `2963bbb72b5f`，套用後是 `813624872431`：指紋變了，代表內容真的改了。

## 五、增量看不到的事

```text
== 4. 對帳：增量檔看不到的刪除 ==
          來源條文數  本地條文數
N0020012     20     21
```

練習站第 2 版刪了大量解僱勞工保護法第 21 條。增量檔只寫「有內容的條文」，刪除沒有內容可寫，所以 `apply_batch()` 不可能知道。三次指紋都相同，**冪等也沒有幫你發現它**——冪等保證的是「重跑不會變」，不保證「結果是對的」。

爬蟲課第 15 節能看到刪除，是因為它拿兩次**全量**互相比對。增量交付省了傳輸，代價是你需要另一個訊號。這裡用的是來源自己公布的條文數：只有大量解僱法對不上，差 1 條。

**對帳只告訴你「哪部法規少了」，不告訴你「少了哪一條」**，更不該自動刪除。要嘛請上游送「刪除清單」，要嘛對這部法規重抓一次全量。哪一種都要寫進交接規格裡，不是在 pandas 裡猜。

## Workshop：寫成 pytest，並弄壞它

### 任務與時間

**35–42 分鐘：寫成測試。** 建立 `test_my_batch.py`，用你自己的話寫出至少三個測試：

```python
# test_my_batch.py — Workshop 起手式，本節測試不涵蓋這段
import pandas as pd
import pytest
from my_pipeline import DATA, ValidationError, apply_batch, fingerprint, read_batch, validate
# 先把本節 Demo 存成 my_pipeline.py


def test_v1_is_valid():
    validate(read_batch(DATA / "articles.jsonl"))


def test_apply_twice_same_fingerprint():
    ...  # 套用 v2 兩次，指紋要相同


def test_missing_timezone_is_rejected():
    ...  # 用 pytest.raises(ValidationError)
```

**42–47 分鐘：弄壞它。** 為下列每一種壞資料寫一個測試，證明 `validate()` 會擋下。**至少一種要擋不下來**——找出 `validate()` 沒有涵蓋的漏洞，並說明它會造成什麼後果：

1. `slug` 寫成 `"1.0"`
2. `source_version` 寫成 `"V2"`
3. `article_no` 寫成 `"第 24 條"`，但 `slug` 是 `"38"`
4. 一條 v2 修改的 `fetched_at` 早於 v1（`2026-01-01T00:00:00+00:00`）
5. `content` 改成 `"（刪除）"`，同時重算 `content_hash`

**47–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫「把每天的增量 JSONL 合併到主表，重跑不能產生重複」。拿它的程式跑：同一批兩次、v2 後再送 v1。指紋一樣嗎？

### 參考判讀

- 1–3 會被擋下：分別違反「slug 格式」、「白名單」、「article_no 與 slug 不一致」。
- **4 不會被擋下，也不該被擋**：它是一筆合法的資料，只是比較舊。`apply_batch()` 會把它「略過」，報告裡看得到。若你的測試寫成 `pytest.raises`，這是測試寫錯，不是程式錯。
- **5 擋不下來**：`（刪除）` 是合法的條文內容——第 1 版就有 9 條本來就是 `（刪除）`。`validate()` 只檢查「格式與一致性」，不判斷「這條是不是剛被刪的」。後果：一條原本有內容的條文，在下游被當成「本來就沒有內容」，LLM 回答時不會引用它，也不會說它被刪了。這是第 08 節「判斷」的範圍，驗證做不到。
- 常見的 AI 版本是 `concat` ＋ `drop_duplicates(keep="last")`：同一批跑兩次指紋相同（它看起來通過了），但 v2 後再送 v1，4 條修改被蓋回去。**只測「同一批跑兩次」的冪等測試，抓不到這個錯**；要再測「舊資料晚到」。
- 若 AI 版本用 `fetched_at` 字串直接比大小：本資料的 `fetched_at` 都是 `+00:00`，字串比較剛好正確。混入 `+08:00` 的資料就會錯。看起來沒問題，可能只是這份資料剛好沒踩到——跟第 03 節一樣。

### 驗收

- 能重現第三段輸出，三次指紋都是 `813624872431`。
- 能解釋為什麼 `keep='first'` 的 750 列是錯的，而且說出被丟掉的是哪 4 條修改。
- `test_my_batch.py` 至少 3 個測試全部通過；故意弄壞的 5 種資料，每種都有測試，且正確判斷哪些該擋、哪些不該擋。
- AI 版本兩種重跑情境都試過，有結論。
- 能說出：冪等通過了，為什麼還是沒發現第 21 條被刪。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，**標準輸出逐字相同**（含三個指紋）。

**資料**：`09-batches/v2-changes.jsonl` 依練習站 `build.py` 的 `V2_MODIFY`／`V2_ADD` 產生，內容與線上 v2 API 逐條比對相同；`09-batches/v2-laws.json` 與線上 `v2/api/laws.json` 位元組相同（皆 2026-10-05 比對）。增量檔的 `fetched_at`（`2026-10-12T04:00:00+00:00`）是**模擬**的第二次交付時間，不是實際抓取時間；`source_url` 指向 v2 條文頁，該頁線上回 200。

**界線**：`apply_batch()` 用 `itertuples` 逐列判斷，是為了產生可讀的報告；全量 749 條重送一次約 0.15 秒（教師實測）。資料量大十倍以上時要改成向量化比對（`merge` 後比較欄位），那是第 14 節的工具。本節不處理「刪除」的自動套用，理由見第五段。本節**尚未實班試教**。

**舊教材**：改寫自 [資料驗證](https://hackmd.io/@yillkid/SJkQFjRNbe)。舊版三項檢查（欄位、型別、值域）全部保留並擴充；差別在舊版**驗證失敗只 `print`**，流程照樣往下走——本節改為拋例外。冪等、跨欄一致性、對帳為新增。

**下一節**：第 10 節〈事件發生時間 vs 資料到達時間〉——本節用 `fetched_at` 判斷新舊；但「事情什麼時候發生」和「資料什麼時候到」是兩回事。下一節回到工地事件：一台攝影機斷線、隔天補傳，以哪個時間彙總，當天的數字就差 20 筆。
