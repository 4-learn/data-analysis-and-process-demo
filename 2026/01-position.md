# 01｜這門課在 AI 系統中的位置

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 01 節：這門課在 AI 系統中的位置。**
> 本節用一個合成工地的四週 AI 攝影機事件，回答三個問題：資料處理這一層負責什麼、不負責什麼；手上的資料是**事件、文件還是文字**；以及 LLM 該看到多少資料——**2,838 筆事件估計 72 萬 token，一張每區每週的違規表 85 token**。
> 本節不是 pandas 語法課，也不是安裝課。程式只是用來量出「該送什麼、不該送什麼」的證據；語法從第 02 節開始。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：指出一份系統模組清單裡哪些屬於資料處理層；把手上的資料分成事件、文件、文字三種形態，並說出各自接下來會怎麼被處理；用數字說明為什麼原始事件不該整份進 LLM 的 context。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–6 分鐘 | 本課在系統裡的哪一層 | 做什麼、不做什麼 |
| 6–13 分鐘 | 三種資料形態 | 事件／文件／文字各一份檔案 |
| 13–22 分鐘 | AI 的第一個建議：整份丟進去 | 727,156 vs 85 估計 token；「最後 500 筆」漏掉真正的異常 |
| 22–32 分鐘 | list 管即時，pandas 管歷史 | 同一份檔案，兩種處理方式各看到什麼 |
| 32–35 分鐘 | 課前環境檢核 | 兩行指令確認版本 |
| 35–50 分鐘 | Workshop：模組清單、資料流圖、抓 AI 的錯 | 範圍判斷表與資料流圖 |

先修：Linux 終端操作、Python 基礎；已上過 MariaDB 與爬蟲課。環境見第五段。

## 一、本課在系統裡的哪一層

情境：一個工地裝了 8 支 AI 攝影機。攝影機上的模型判斷「這個人有沒有戴安全帽、有沒有扣安全帶、有沒有跨越警示線」，每判斷一次就送出一筆**事件**。主管希望每週一早上問 LLM：「上週哪裡最危險？」

從攝影機到 LLM，中間有好幾層：

| 層 | 回答的問題 | 工具 | 屬於哪門課 |
| --- | --- | --- | --- |
| 影像辨識 | 這一幀畫面裡有什麼？ | 視覺模型 | 不在本養成班範圍 |
| 即時告警 | **現在**要不要叫人過去？ | `if`／規則、list／dict | 系統端，本課不做 |
| 收集與存放 | 資料從哪來、存在哪？ | 爬蟲、MariaDB | 爬蟲課、MariaDB 課（上游） |
| **整理、驗證、彙總、濃縮** | **發生過什麼？有沒有模式？哪些該交給 LLM？** | **pandas** | **本課** |
| 模型訓練 | 能不能從過去學會預測？ | scikit-learn 等 | 機器學習課（下游） |
| 解釋與回答 | 怎麼說給人聽？ | LLM | LLM 課（下游） |

本課**不做**：即時推論、影像辨識、模型訓練、LLM 推論與對話生成。本課的輸入是上游交來的 CSV、JSONL 與資料庫查詢結果；輸出是**可回溯、驗證過、放得進 context** 的表格與文字。

> 舊版講義寫「本課不教 Database / SQL」。這班學生已經上過 MariaDB，那句話不再成立：第 04 節會直接用 SQL，並討論「這件事該在資料庫做，還是拉進 pandas 做」。

pandas 在這裡的角色，用舊講義的一句話最準確：**它是系統的記憶體與語意層。** 即時層只記得「現在」；pandas 讓系統記得「過去四週」，而且每一欄都有名字、每一列都說得出是什麼事。

## 二、三種資料形態

同一個工地，`data/` 裡有三種長得都像「一行一個 JSON」的檔案，但它們是三種不同的東西：

```text
== 1. 同一個工地，三種資料形態 ==
事件 events.jsonl            2,838 列 × 12 欄；一列＝某時某地發生一件事，4 種 event_type
文件 articles.jsonl            749 列 × 10 欄；一列＝一條條文，content 平均 159 字、最長 935 字
文字 near-miss-reports.jsonl    40 列 ×  7 欄；一列＝一段人寫的敘述，15 段含手機號碼
```

| 形態 | 本課的檔案 | 一列是什麼 | 價值在哪 | 接下來怎麼處理 | 主要在哪幾節 |
| --- | --- | --- | --- | --- | --- |
| **事件** | `events/events.jsonl` | 某時、某地、某人發生某件事 | **累積之後**才有意義：單一筆「沒扣安全帶」說不出什麼，同一人一下午 18 筆才是 | 去重、對時間、**彙總**成行為與趨勢 | 05–15 |
| **文件** | `articles.jsonl` | 一條有出處、有版本的條文 | **單筆**就有意義，而且要能回溯到來源 | 保留來源欄位、**整條**取捨，不彙總 | 03、04、09、16 |
| **文字** | `events/near-miss-reports.jsonl` | 一段人寫的自由敘述 | 有事件表沒有的細節（「下雨後樓梯口濕滑」） | **切塊、去識別**（人名、電話），不能直接彙總 | 17 |

分辨它們的理由很實際：**事件要先彙總才交出去；文件要整條附出處交出去；文字要先去識別才交出去。** 把條文拿去 `groupby` 算平均、把事件一筆一筆當證據送給 LLM、把含電話的通報原樣丟進 prompt，都是把形態認錯了。

還有一組常被混在一起的詞，舊講義〈事件 ≠ 影像 ≠ 陣列〉講得好，原樣保留：

| 層級 | 長什麼樣子 | 回答的問題 |
| --- | --- | --- |
| 影像 | `(高, 寬, 3)` 的像素 | 畫面長怎樣？——模型的世界 |
| 陣列（list、ndarray） | `[[...], [...]]` | 資料怎麼存？——容器，不帶語意 |
| **事件** | `{event_time, zone, worker_id, event_type, ...}` | **發生了什麼事？**——本課的世界 |

本課從不碰影像。`events.jsonl` 每一列的 `snapshot` 欄只是一個路徑字串（`snapshots/cam-05/...jpg`），本資料**沒有附任何圖檔**。

## 三、AI 的第一個建議：整份丟進去

你請 AI 幫忙做「每週一問 LLM 上週哪裡最危險」，最常見的第一版是：

```python
# AI 常見寫法，本節測試不涵蓋這段
events = open("data/events/events.jsonl").read()
prompt = f"以下是工地事件紀錄：\n{events}\n請問最近有什麼異常？"
```

先量它有多長（token 用第 16 節的保守粗估：非 ASCII 與數字算 1、其他 ASCII 算 0.5，乘 1.2 後無條件進位；這是**估計值**，不是任何模型的實際計數）：

```text
== 4. 什麼該進 context ==
整份 events.jsonl  2,838 列  字元   982,666  估計 token   727,156
只留違規（未去重）          498 列  字元   168,605  估計 token   127,376
檔案最後 500 筆         500 列  字元   162,216  估計 token   121,419
每區每週違規摘要 CSV         4 列  字元        89  估計 token        85
整份事件是摘要表的 8,555 倍
檔案最後 500 筆含 W041 09-22 14 時那 18 筆中的 0 筆；其 event_time 範圍 2026-09-22T15:16 ～ 2026-09-26T16:55
```

四件事：

1. **整份 72 萬估計 token。** 這只是**一個工地、四週**。課綱說的「三萬筆」，以這份資料每週約 700 筆等比推算，大約是同一工地十個月的量（推算，不是實測）。不管模型的 context 多大，第 16 節會看到 LLM 組給證據的預算通常是「幾千」這個等級。
2. **「只留違規」還是 12 萬。** 篩掉 `ppe_ok` 只砍掉八成，而且這 498 列**裡面有重送的**（去重後是 496，下一段會看到）。篩選不是濃縮。
3. **「放不下就取最後 500 筆」是最危險的修法。** AI 被告知超過長度時，常改成取檔尾。這份檔案的順序是**到達順序**，最後 500 筆從 09-22 15:16 開始——**整份資料裡唯一真正的異常（W041 在 09-22 14:02 起連續 18 筆未扣安全帶）剛好一筆都不在裡面**。LLM 會很有自信地回答「最近沒有明顯異常」，而且你無從發現，因為它沒看到的東西不會出現在回答裡。
4. **一張 4 列的摘要表 85 估計 token**，是整份的八千多分之一。它不是「少給一點」，而是**換一種東西給**：不是事件，是已經算好的行為。

**LLM 不該看到三萬筆事件；它該看到十行摘要。** 但「哪十行」要由這一層決定，而且要決定得對——第 15 節專門處理這件事。

## 四、list 管即時，pandas 管歷史

這句是舊講義的核心，本課保留。同一份 `events.jsonl`，用兩種方式處理：

- **即時層（list／dict）**：一筆一筆照到達順序讀，每個人只記住「最近 10 分鐘的未扣安全帶」，第 3 筆就告警。它不需要 pandas，也**不該**用 pandas——它要的是快、而且只看現在。
- **歷史層（pandas）**：把四週全部讀進來，去掉重送、轉成當地時間、依區域與週彙總。

```text
== 2. list 管即時：一筆到、判斷一筆 ==
依到達順序逐筆處理 2,838 筆；記憶體中最多同時保留 4 筆
告警 16 次，對象 ['W041']；第一次 2026-09-22T14:08:38+08:00 cam-07

== 3. pandas 管歷史：每區每週違規 ==
2,838 列 → 去掉重送 20 列 → 2,818 筆事件 → 違規 496 筆
週一    08-31  09-07  09-14  09-21
zone                            
Z1       26     29     35     24
Z2       32     36     49     35
Z3       38     26     30     22
Z4       21     25     26     42
四週違規最多（辨識到臉者）：W041 36 筆、W029 33 筆、W044 27 筆；其中即時規則告警過的只有 ['W041']
```

兩邊各看到對方看不到的東西：

- **即時層抓到了 W041**，在第 3 筆（14:08）就告警，處理整份檔案時記憶體裡最多只放了 4 筆（只記最近 10 分鐘，過期就忘）。這正是即時層該做的事，**pandas 做不到這麼快、也不需要它做**。
- **即時層看不到 W029 和 W044**。他們四週分別有 33、27 筆違規，但從沒在 10 分鐘內連續 3 次，所以一次告警都沒有。「同一個人反覆犯」是**累積**出來的模式，只有回頭看全部歷史才看得到。
- **即時層也不會發現重送**。cam-05 斷線後補傳的 20 筆被送了兩次（`event_id` 相同、只有 `ingested_at` 晚 14 分鐘）。即時層照單全收；歷史層要先去重，數字才對。`dedupe()` 只在「除了 `ingested_at` 之外完全相同」時才去掉，內容不同就停下來——第 09 節會把這件事講完整。

以下為完整 `01_position.py`，只讀 `data/`，不寫檔、不連線。看不懂 pandas 語法沒關係，本節只要看懂輸出；語法從第 02 節開始。

<!-- demo: 01_position.py -->
```python
"""第 01 節：同一個工地，三種資料形態；什麼該進 LLM 的 context，什麼不該。"""

import json
import math
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
EVENTS = DATA / "events" / "events.jsonl"
TYPES = DATA / "events" / "event-types.csv"
WINDOW_SECONDS = 600       # 即時規則：同一人 10 分鐘內
THRESHOLD = 3              # 第 3 筆「高處未使用安全帶」就告警


def estimate_tokens(text):
    """保守粗估（同第 16 節）：非 ASCII 字元與數字各算 1、其他 ASCII 算 0.5，再乘 1.2。"""
    heavy = sum(1 for ch in text if not ch.isascii() or ch.isdigit())
    light = len(text) - heavy
    return math.ceil((heavy + light * 0.5) * 1.2)


def stream_alerts(lines, window=WINDOW_SECONDS, threshold=THRESHOLD):
    """即時層：一筆到、判斷一筆，只記得每個人最近 window 秒。回傳 (告警清單, 記憶體中最多同時保留幾筆)。"""
    recent = defaultdict(deque)
    alerts, peak = [], 0
    for line in lines:
        e = json.loads(line)
        if e["event_type"] != "no_harness" or not e["worker_id"]:
            continue
        t = datetime.fromisoformat(e["event_time"])
        q = recent[e["worker_id"]]
        q.append(t)
        for who in list(recent):                     # 過期的就忘掉：所有人都只留最近 window 秒
            while recent[who] and (t - recent[who][0]).total_seconds() > window:
                recent[who].popleft()
            if not recent[who]:
                del recent[who]
        peak = max(peak, sum(len(x) for x in recent.values()))
        if len(q) >= threshold:
            alerts.append((e["worker_id"], e["event_time"], e["camera_id"]))
    return alerts, peak


def read_events(path=EVENTS):
    """先讀成字串，不讓 pandas 猜（第 02、03 節的立場）。"""
    return pd.read_json(path, lines=True, dtype=False, convert_dates=False)


def dedupe(events):
    """補傳會把同一筆送兩次：event_id 相同、只有 ingested_at 不同才算重送；內容不同就停。"""
    content = [c for c in events.columns if c != "ingested_at"]
    dup = events[events.duplicated("event_id", keep=False)]
    differ = dup.groupby("event_id")[content].nunique(dropna=False).gt(1).any(axis=1)
    if differ.any():
        raise ValueError(f"同一 event_id 內容不同：{differ.sum()} 個，例如 {differ[differ].index[0]}")
    return events.drop_duplicates("event_id", keep="first")


def weekly_violations(events, types):
    """歷史層：每區、每週（週一起算）各有幾筆違規。"""
    unknown = sorted(set(events["event_type"]) - set(types["event_type"]))
    if unknown:
        raise ValueError(f"未知事件類型 {unknown}")
    violation = set(types.loc[types["is_violation"] == "true", "event_type"])
    v = events[events["event_type"].isin(violation)]
    local = pd.to_datetime(v["event_time"], format="ISO8601").dt.tz_convert("Asia/Taipei")
    monday = (local.dt.normalize() - pd.to_timedelta(local.dt.weekday, unit="D")).dt.strftime("%m-%d")
    table = pd.crosstab(v["zone"], monday.rename("週"))
    table.columns.name = "週一"
    return table


def jsonl(df):
    return df.to_json(orient="records", lines=True, force_ascii=False)


if __name__ == "__main__":
    events = read_events()
    articles = pd.read_json(DATA / "articles.jsonl", lines=True, dtype=False, convert_dates=False)
    reports = pd.read_json(DATA / "events" / "near-miss-reports.jsonl", lines=True, dtype=False, convert_dates=False)
    types = pd.read_csv(TYPES, dtype=str, keep_default_na=False)

    print("== 1. 同一個工地，三種資料形態 ==")
    phones = reports["text"].str.contains(r"09\d\d-\d{3}-\d{3}").sum()
    print(f"事件 events.jsonl            {len(events):>5,} 列 × {events.shape[1]:>2} 欄；"
          f"一列＝某時某地發生一件事，{events['event_type'].nunique()} 種 event_type")
    print(f"文件 articles.jsonl          {len(articles):>5,} 列 × {articles.shape[1]:>2} 欄；"
          f"一列＝一條條文，content 平均 {articles['content'].str.len().mean():.0f} 字、最長 {articles['content'].str.len().max()} 字")
    print(f"文字 near-miss-reports.jsonl {len(reports):>5,} 列 × {reports.shape[1]:>2} 欄；"
          f"一列＝一段人寫的敘述，{phones} 段含手機號碼")

    print("\n== 2. list 管即時：一筆到、判斷一筆 ==")
    lines = EVENTS.read_text(encoding="utf-8").splitlines()
    alerts, peak = stream_alerts(lines)
    print(f"依到達順序逐筆處理 {len(lines):,} 筆；記憶體中最多同時保留 {peak} 筆")
    print(f"告警 {len(alerts)} 次，對象 {sorted({a[0] for a in alerts})}；第一次 {alerts[0][1]} {alerts[0][2]}")

    print("\n== 3. pandas 管歷史：每區每週違規 ==")
    unique = dedupe(events)
    table = weekly_violations(unique, types)
    print(f"{len(events):,} 列 → 去掉重送 {len(events) - len(unique)} 列 → {len(unique):,} 筆事件 → 違規 {int(table.values.sum())} 筆")
    print(table.to_string())
    named = unique[unique["event_type"].isin(set(types.loc[types["is_violation"] == "true", "event_type"]))
                   & (unique["worker_id"] != "")]
    top = named.groupby("worker_id").size().sort_values(ascending=False, kind="stable").head(3)
    print("四週違規最多（辨識到臉者）：" + "、".join(f"{w} {n} 筆" for w, n in top.items())
          + f"；其中即時規則告警過的只有 {sorted({a[0] for a in alerts} & set(top.index))}")

    print("\n== 4. 什麼該進 context ==")
    raw = EVENTS.read_text(encoding="utf-8")
    viol = set(types.loc[types["is_violation"] == "true", "event_type"])
    burst = events.index[(events["worker_id"] == "W041") & events["event_time"].str.startswith("2026-09-22T14")]
    tail = events.tail(500)
    candidates = [
        ("整份 events.jsonl", len(events), raw),
        ("只留違規（未去重）", int(events["event_type"].isin(viol).sum()), jsonl(events[events["event_type"].isin(viol)])),
        ("檔案最後 500 筆", len(tail), jsonl(tail)),
        ("每區每週違規摘要 CSV", len(table), table.to_csv()),
    ]
    for label, rows, text in candidates:
        print(f"{label:16} {rows:>5,} 列  字元 {len(text):>9,}  估計 token {estimate_tokens(text):>9,}")
    ratio = estimate_tokens(raw) / estimate_tokens(table.to_csv())
    print(f"整份事件是摘要表的 {ratio:,.0f} 倍")
    print(f"檔案最後 500 筆含 W041 09-22 14 時那 {len(burst)} 筆中的 {int(tail.index.isin(burst).sum())} 筆；"
          f"其 event_time 範圍 {tail['event_time'].min()[:16]} ～ {tail['event_time'].max()[:16]}")
```

執行（在本目錄下）：

```bash
python3 01_position.py
```

輸出依序是本頁第二段、第四段、第三段貼的四個區塊。

這張 4 列的表也不是終點。它說「Z4 第四週 42 筆、明顯偏高」，但沒說**為什麼**——Workshop 會看到，42 筆裡有 24 筆是同一個人。摘要該保留哪些維度、怎麼讓每一列都能追回原始事件，是第 12、15 節的事。本節只要記住：**送給 LLM 的東西，是這一層算出來的，不是原始資料。**

## 五、課前環境檢核

舊版的〈Install Pandas〉不再獨立成一節。上課前在終端機跑：

```bash
python3 -c "import sys, pandas, numpy; print(sys.version.split()[0], pandas.__version__, numpy.__version__)"
python3 01_position.py | head -4
```

第一行應印出 Python **3.11 以上**、pandas **3.0.x**（本課以 3.0.6 實測）；第二行應印出第二段那四行。Python 是 3.10 的話 pip 裝不到 pandas 3，請在開課前依 `README.md` 的環境說明處理，不要在課堂上排除。Jupyter 不是本課的主要載體：所有程式都是可以 `python3 檔名` 直接重跑的 `.py`。

## Workshop：模組清單、資料流圖、抓 AI 的錯

### 任務與時間

**35–41 分鐘：哪些屬於本課？** 下列是這個工地系統的模組。逐一判斷「屬於本課／不屬於（屬於哪一層）」，並各寫一句理由：

1. 攝影機上的安全帽偵測模型
2. 同一人 10 分鐘內 3 次未扣安全帶就推播給領班
3. 每天把事件寫進 MariaDB
4. 去掉補傳造成的重複事件
5. 每區每週違規統計表
6. 把虛驚通報裡的人名、電話遮掉
7. 用過去事件訓練一個「明天哪區會出事」的預測模型
8. 選出「該給 LLM 看的十行」並控制在預算內
9. LLM 回答主管的問題
10. 把條文的 `source_url` 一路保留到 LLM 的證據裡

**41–46 分鐘：畫資料流圖。** 畫出「來源 → 本課 → ML／LLM」的資料流，至少標出：三種形態各從哪來、本課的輸入檔與輸出物、哪一條線是即時層。可以手畫，也可以用文字或 Mermaid。

**46–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫「讀 `data/events/events.jsonl`，組一個 prompt 問 LLM 最近有什麼異常」（不必真的呼叫 LLM）。拿它的程式驗收：

1. 它把多少東西放進 prompt？用 Demo 的 `estimate_tokens()` 量。
2. 如果你回它「太長了」，它怎麼縮？縮完之後，W041 在 09-22 14 時的 18 筆還在不在？
3. 它有沒有處理重送的 20 筆？

### 參考判讀

- 模組判斷：**屬於本課 4、5、6、8、10**；不屬於 1（影像辨識）、2（即時層，list／dict 與規則）、3（上游：爬蟲／MariaDB 課）、7（機器學習課）、9（LLM 課）。
  - 第 6 題容易判斷錯：遮人名電話聽起來像「資安」，但它是把**文字形態**的資料整理成可以交出去的樣子，屬於第 17 節。
  - 第 2 題容易判斷錯：它用到了事件資料，但它只看「現在」；Demo 第二段的 `stream_alerts()` 只用 `deque`，沒有 pandas。
  - 第 10 題：「保留來源欄位」是本課的責任（第 03 節）——上游交來了，在這一層弄丟，下游就無法附出處。
- 一個可接受的資料流圖（文字版；本節測試不涵蓋）：

  ```mermaid
  flowchart LR
    cam[攝影機＋視覺模型] -->|事件| rt[即時告警：list／規則]
    cam -->|事件 events.jsonl| DA
    crawl[爬蟲課] -->|文件 articles.jsonl| DA
    db[(MariaDB)] -->|查詢結果| DA
    boss[主管通報] -->|文字 near-miss-reports.jsonl| DA
    subgraph DA[本課：pandas]
      clean[去重・驗證・對時間] --> agg[彙總・濃縮・去識別] --> ser[序列化・預算]
    end
    ser -->|十行摘要＋可回溯明細| LLM[LLM 課]
    agg -->|驗證過的表| ML[機器學習課]
  ```

  驗收重點不是畫得漂亮，而是：即時告警**不經過**本課；本課的輸出是摘要與明細，**不是原始事件**。
- 抓 AI 的錯，教師實測（Demo 第四段）：
  - 整份檔案估計 **727,156** token；只留違規 **127,376**；都遠超第 16 節的 3,000 預算。
  - 「只取最後 500 筆」：估計 121,419 token，仍然放不下；而且**W041 的 18 筆一筆都不在**（0／18），最後 500 筆從 09-22 15:16 開始。
  - 改成「先依 `event_time` 排序再取最後 500 筆」也一樣：**0／18**（教師另行實測，最後 500 筆從 09-22 15:16 開始）。不管依哪種時間取「最近」，只要取的是**筆數**，異常就可能剛好落在切點前面。
  - 沒去重：違規 498 筆而不是 496 筆（重送的 20 筆裡有 2 筆是 `restricted_entry`）。差 2 筆看起來無所謂，但 LLM 會把它當作事實引用。
- Z4 第四週 42 筆裡，**W041 一人 24 筆**，其他人合計 18 筆（教師實測）。這說明摘要表「Z4 第四週偏高」是對的，但**沒有人的維度就說不出原因**；這不是要把 2,838 筆送回去，而是摘要要多一個維度（第 12、15 節）。

### 驗收

- 十個模組都有判斷與一句理由，第 2、6 題的理由說得出「即時 vs 歷史」與「文字形態」。
- 資料流圖標出三種形態的來源檔、本課的輸出，以及一條不經過本課的即時告警線。
- AI 版本的 prompt 量過估計 token，並回答：縮短後的版本 W041 的 18 筆還剩幾筆。
- 能用一句話說明：為什麼「最後 500 筆」比「整份丟進去」更危險。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，**標準輸出逐字相同**。token 數字全部是**粗估**（與第 16 節 `estimate_tokens()` 同一規則），不是任何 tokenizer 的實測。

**資料**：`data/events/` 是 `tools/build_events.py` 產生的**合成資料**（固定種子，雜湊見 `data/events/MANIFEST.json`）：示範工地、2026-08-31～09-26、週日停工，人名、電話、事件全部虛構。本節用到的刻意埋入狀況：補傳重送 20 筆、W041 連續 18 筆 `no_harness`、檔案順序＝到達順序、通報含電話。**不宣稱任何真實工地的統計結論**。條文取自爬蟲課練習站，可能經刻意修改，不具法律效力。

**界線**：「三萬筆」是課綱的說法；本資料只有 2,838 筆，文中「約十個月」為等比推算。即時層的 10 分鐘／3 次是本節為了對照而設的規則，不是任何法規或廠商的告警標準。本節不呼叫 LLM，不宣稱「LLM 看了整份會答錯」——宣稱的只有可以直接量的兩件事：長度，以及「取最後 N 筆」會不會包含那段異常。本節**尚未實班試教**。

**舊教材**：改寫並合併 [Python 資料分析與處理](https://hackmd.io/@yillkid/SyNGe-Nyc) 與 [Pandas 在 AI 專案中的定位](https://hackmd.io/@yillkid/r1hdKQlza)。**保留**：系統分層表（YOLO／狀態機／事件紀錄／長期分析／LLM 改為工地情境）、「Pandas 是 AI 專案的記憶體」、「list 管即時，Pandas 管歷史」、「LLM 不應該看到 3 萬筆事件，應該看到 10 行摘要」、模組判斷 Workshop（擴為 10 題並加入上游與 ML）。**刪除**：「本課不教 Database / SQL」（學生已上過 SQL，第 04 節直接用）、「本課只使用 numpy 與 pandas」（NumPy 移附錄）、手打 list 轉 DataFrame 的 Workshop（改用真實檔案）。[事件 ≠ 影像 ≠ 陣列](https://hackmd.io/@yillkid/Sy6al0A7Zg) 的三層對照表原樣保留於第二段。[Install Pandas](https://hackmd.io/@yillkid/ryizVb415) 不再獨立成節，縮為第五段的課前檢核；舊版 `cars`／`passings` 範例與 W3Schools 線上環境刪除。

**下一節**：第 02 節〈CSV、編碼與多檔讀取〉——本節的程式都先用 `dtype=False`、`dtype=str` 讀檔，下一節說明為什麼：一行 `read_csv` 讓 pandas 替你猜型別，而它猜錯的時候不會報錯。
