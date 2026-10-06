# 12｜彙總：分母是什麼、漏掉了誰

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 12 節：彙總：分母是什麼、漏掉了誰。**
> 本節把 2818 筆攝影機事件壓成「每人一列」「每區一列」的彙總表，而且每一個比例都要說得出**分母是誰**、每一張表都要說得出**誰不在裡面**。
> 本節不是 `groupby` 語法大全，也不做時間彙總（那是第 11 節）；這裡只處理「把很多列變成少數列」時，數字在哪裡默默變了。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 範例程式碼

- [demo：12_groupby_denominator.py](https://github.com/4-learn/data-analysis-and-process-demo/blob/master/2026/12_groupby_denominator.py)（與本頁 Demo 逐字相同）
- 練習資料與環境說明：[2026/README](https://github.com/4-learn/data-analysis-and-process-demo/tree/master/2026)

## 學習目標與時間

完成後，你能：說出 `size` 和 `count` 各自在算什麼；用 named aggregation 一次產出有名字的多個彙總欄；為一個「違規率」寫出它的分子與分母；找出 `groupby` 之後消失的那些列和那些人，並用名冊把沒有事件的人補回來。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–5 分鐘 | 事件 ≠ 行為；先去重 | 2838 → 2818，違規 498 → 496 |
| 5–12 分鐘 | `size` 與 `count` | cam-08 有 231 列、confidence 0 格 |
| 12–19 分鐘 | `agg` 多重聚合與命名 | 每區一列；`nunique` 把空字串算成一個人 |
| 19–26 分鐘 | 違規率的分母 | 同一份資料，四個「違規率」 |
| 26–35 分鐘 | 分組後誰消失了 | `dropna`、名冊 `reindex`、W023 的兩列 |
| 35–50 分鐘 | Workshop：區域 × 週的違規表 | 16 列的彙總表＋分母說明 |

先修：本課第 09 節（業務鍵去重）、第 11 節（時間欄轉型、週彙總）。環境同第 02 節。

## 一、事件不是行為；彙總之前先去重

`data/events/events.jsonl` 一列是**一次偵測**：某支攝影機，在某個時間，看到某個人（或認不出是誰），戴沒戴好防護具。老闆問的卻是「誰常違規」「哪一區比較危險」——**單看任何一列都回答不了**，要把很多列壓成少數幾列。這就是彙總：輸出一定比輸入少很多列，而每一列都代表一群事件。

壓之前先做第 09 節的事：**業務鍵去重**。cam-05 的補傳送了兩次，同一個 `event_id` 有兩列。沒去重就彙總，每一個數字都會被那 20 列污染：

```text
== 1. 先去重：分母從哪一份資料算 ==
原始 2838 列，不同 event_id 2818 個；去重後 2818 列
違規事件：去重前 498 筆，去重後 496 筆
```

差 2 筆看起來很小。但它不會報錯，也不會只發生一次——下次補傳送三次，你的週報就會多出一整天。**分母從哪一份資料算，是第一個要寫下來的決定。**本節之後所有數字都從去重後的 2818 列出發。

## 二、`size` 與 `count`：「幾列」和「幾格有值」

AI 最常給的寫法是 `df.groupby("camera_id").count()`。它回答的問題其實是「**每一欄有幾格不是缺值**」，不是「有幾筆事件」：

```text
== 2. size 與 count：「幾列」和「幾格有值」 ==
           列數_size  confidence_count  worker_id_count  worker_id空字串
camera_id                                                          
cam-01         466               466              466            51
cam-02         453               453              453            45
cam-03         311               311              311            48
cam-04         323               323              323            47
cam-05         394               394              394            46
cam-06         386               386              386            43
cam-07         254               254              254            41
cam-08         231                 0              231            43
```

- **`size` 算列數**，不看任何一欄的內容。「cam-08 有幾筆事件」答案是 231。
- **`count` 算非缺值的格數**。cam-08 跑舊模型、不記錄 confidence，所以 `confidence` 的 `count` 是 **0**。拿 `count()` 當事件數，cam-08 會被報成「沒有事件」；拿它當平均信心度的分母，那 231 筆就**靜悄悄地不在分母裡**。
- **`count` 不認得空字串**。`worker_id` 的 `count` 跟 `size` 一樣，因為「辨識不到臉」在本資料是 `""`，不是缺值——對 pandas 來說，空字串是一個有值的字串。每台攝影機各有 41–51 筆認不出人的事件，`count` 一筆也沒少算。

所以 `count` 的結果**取決於缺值怎麼表示**：同一件事（認不出人），用 `""` 記和用 `NaN` 記，`count` 就差 364。第五段會再遇到它。

## 三、`agg` 的多重聚合與命名

一次要好幾個數字時，用 named aggregation：`新欄名=("來源欄", 函式)`。欄名由你決定，不會出現 `('is_violation', 'mean')` 這種多層欄名，下游讀得懂：

```text
== 3. agg 多重聚合與命名：每區一列 ==
      事件數  違規數    違規率  人數_nunique  已辨識人數
zone                                    
Z1    919  114  0.124          35     34
Z2    634  152  0.240          34     33
Z3    780  116  0.149          39     38
Z4    485  114  0.235          32     31
```

2818 列變成 4 列。兩個要讀出來的地方：

- `違規率` 是布林欄的 `mean`：True 算 1、False 算 0，平均起來就是「違規事件 ÷ 這一區的事件數」。**分母是這一區所有的偵測**，包括認不出人的。
- **`nunique` 把空字串算成一個人**。每一區的 `人數_nunique` 都比 `已辨識人數` 多 1——多出來的「人」叫做 `""`。如果你要回答「這一區有幾位工人出現過」，直接 `nunique` 就錯了。

## 四、違規率的分母

「違規率是多少？」聽起來只有一個答案。同一份資料，換分母就有四個：

```text
== 4. 違規率的分母 ==
未去重：全部列     498 / 2838 = 17.5%
去重：全部偵測     496 / 2818 = 17.6%
去重：只算已辨識    419 / 2454 = 17.1%
去重：只算未辨識     77 /  364 = 21.2%
每人違規率的平均（52 人，每人權重相同）= 16.6%
```

- **「全部偵測」是工地層級的違規率**：每 100 次偵測有 17.6 次違規。要問「這個工地安不安全」用它。
- **「只算已辨識」是能追到人的違規率**。它比全部偵測低，因為在本資料中**認不出臉的事件違規率比較高**（21.2%）。只看已辨識的人，工地看起來比實際安全。（這是合成資料的結果；真實工地為什麼認不出臉，要回頭查影像，不能從表上猜。）
- **「每人違規率的平均」又是另一個數**：先每人算一個比例，再把 52 個比例平均。事件很多的人和事件很少的人權重一樣，結果 16.6%，跟任何一個「總數 ÷ 總數」都不同。兩種都可以用，但**報告上要寫是哪一種**。

這不是「哪個對」的問題，是**哪個回答了你被問的問題**。寫報告時，比例旁邊一定要寫分子與分母各是什麼（例如「419／2454，已辨識事件」）。

## 五、分組後誰消失了

### 分組鍵有缺值：整組丟掉，沒有警告

`groupby` 預設 `dropna=True`：**分組鍵是缺值的列，整組不會出現在結果裡**。先實測本資料：

```text
== 5. 分組鍵有缺值：誰消失了 ==
本資料 worker_id：空字串 364 筆，NaN 0 筆
groupby('worker_id')：53 組，合計 2818；空字串自成一組 364 筆
空字串轉成 NaN 後：52 組，合計 2454——364 筆不見了，沒有警告
加上 dropna=False：53 組，合計 2818；NaN 組 364 筆
```

- 本資料的「認不出人」是空字串，所以 `groupby` 讓它自成一組 `""`，**沒有消失**——但它混在 52 個人中間，看起來像第 53 位工人。
- 很多清理流程會「好心地」把空字串換成 `NaN`（第 08 節討論過缺值的表示法）。換完之後 `groupby` 就把 364 筆整組丟掉：合計從 2818 變成 2454，**沒有任何訊息**。
- 要看到它們，寫 `dropna=False`。

**怎麼抓這種錯？** 彙總後把計數加總，跟彙總前的列數比。2454 ≠ 2818，就知道有東西不見了。這一行檢查比任何 `groupby` 參數都可靠。

### 沒有事件的人：根本不會出現

`groupby` 只能分出「資料裡有的組」。W053–W060 整段期間沒有任何事件，所以每人彙總**只有 52 人**——「沒有違規」和「不在名單上」在結果裡長得一模一樣：都是沒有這一列。

要補回來，需要一份**不依賴事件的名單**：`workers.csv` 名冊。用名冊的 `worker_id` 去 `reindex`，沒事件的人補 0。但名冊有個陷阱：

```text
== 6. 沒有事件的人：用名冊補回 ==
groupby 結果 52 人；名冊 61 列、不同 worker_id 60 個
reindex(名冊整欄)：61 列，W023 出現 2 次，事件合計 2506（多算 52）
reindex(不重複 worker_id)：60 列，事件合計 2454；事件 0 的 8 人：W053…W060
```

W023 在 09-14 換了承攬商，名冊有兩列。直接拿整欄 `reindex`，W023 就出現兩次，他的 52 筆事件被**算了兩遍**。所以要先 `drop_duplicates()`，用「不重複的 worker_id」當名單。名冊兩列的完整處理（哪段期間算哪個承攬商）是第 14 節的主題。

`per_worker()` 把這些全部寫進去：只算已辨識的事件、以名冊為準補人、名冊有空 ID 或事件出現名冊沒有的人就停下來（那代表名冊過期，不是「補 0」能解決的）。`violation_rate` 的分母是**這個人被辨識到的事件數**；事件 0 的人分母是 0，所以留 `NaN`——「沒有資料」不是「違規率 0%」。

以下為完整 `12_groupby_denominator.py`，只讀 `data/events/`，不寫檔、不連線。

<!-- demo: 12_groupby_denominator.py -->
```python
"""第 12 節：彙總——分母是什麼、漏掉了誰。"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
EVENTS = DATA / "events"


def read_events(path=EVENTS / "events.jsonl"):
    """讀事件、依 event_id 去重（同一批補傳送了兩次，留先到的那份）。"""
    raw = pd.read_json(path, lines=True, dtype=False, convert_dates=False)
    return raw, raw.drop_duplicates("event_id", keep="first").reset_index(drop=True)


def violation_types(path=EVENTS / "event-types.csv"):
    types = pd.read_csv(path, dtype=str, keep_default_na=False)
    return set(types.loc[types["is_violation"] == "true", "event_type"])


def read_roster(path=EVENTS / "workers.csv"):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def per_worker(events, roster, violations):
    """每人一列：以名冊為準（沒有事件的人也要在），未辨識的事件不屬於任何人。"""
    ids = roster["worker_id"].drop_duplicates()
    if ids.eq("").any():
        raise ValueError("名冊有空的 worker_id")
    known = events[events["worker_id"] != ""].assign(
        is_violation=lambda d: d["event_type"].isin(violations))
    stranger = sorted(set(known["worker_id"]) - set(ids))
    if stranger:
        raise ValueError(f"事件中有名冊沒有的人：{stranger[:5]}")
    table = (known.groupby("worker_id")
             .agg(events=("event_id", "size"), violations=("is_violation", "sum"))
             .reindex(pd.Index(ids, name="worker_id"), fill_value=0))
    table["violation_rate"] = (table["violations"] / table["events"].replace(0, np.nan)).round(3)
    return table


if __name__ == "__main__":
    raw, ev = read_events()
    viol = violation_types()
    ev["is_violation"] = ev["event_type"].isin(viol)

    print("== 1. 先去重：分母從哪一份資料算 ==")
    print(f"原始 {len(raw)} 列，不同 event_id {raw['event_id'].nunique()} 個；去重後 {len(ev)} 列")
    print(f"違規事件：去重前 {int(raw['event_type'].isin(viol).sum())} 筆，去重後 {int(ev['is_violation'].sum())} 筆")

    print("\n== 2. size 與 count：「幾列」和「幾格有值」 ==")
    by_cam = ev.groupby("camera_id").agg(
        列數_size=("event_id", "size"),
        confidence_count=("confidence", "count"),
        worker_id_count=("worker_id", "count"),
        worker_id空字串=("worker_id", lambda s: int(s.eq("").sum())),
    )
    print(by_cam.to_string())

    print("\n== 3. agg 多重聚合與命名：每區一列 ==")
    by_zone = ev.groupby("zone").agg(
        事件數=("event_id", "size"),
        違規數=("is_violation", "sum"),
        違規率=("is_violation", "mean"),
        人數_nunique=("worker_id", "nunique"),
        已辨識人數=("worker_id", lambda s: s[s != ""].nunique()),
    ).round({"違規率": 3})
    print(by_zone.to_string())

    print("\n== 4. 違規率的分母 ==")
    known = ev[ev["worker_id"] != ""]
    rate_each = known.groupby("worker_id")["is_violation"].mean()
    rows = [
        ("未去重：全部列", int(raw["event_type"].isin(viol).sum()), len(raw)),
        ("去重：全部偵測", int(ev["is_violation"].sum()), len(ev)),
        ("去重：只算已辨識", int(known["is_violation"].sum()), len(known)),
        ("去重：只算未辨識", int(ev.loc[ev["worker_id"] == "", "is_violation"].sum()), int((ev["worker_id"] == "").sum())),
    ]
    for label, num, den in rows:
        print(f"{label:10} {num:4} / {den:4} = {num / den:.1%}")
    print(f"每人違規率的平均（{len(rate_each)} 人，每人權重相同）= {rate_each.mean():.1%}")

    print("\n== 5. 分組鍵有缺值：誰消失了 ==")
    print(f"本資料 worker_id：空字串 {int(ev['worker_id'].eq('').sum())} 筆，NaN {int(ev['worker_id'].isna().sum())} 筆")
    g = ev.groupby("worker_id").size()
    print(f"groupby('worker_id')：{len(g)} 組，合計 {g.sum()}；空字串自成一組 {g.loc['']} 筆")
    as_nan = ev.assign(worker_id=ev["worker_id"].replace("", np.nan))
    g = as_nan.groupby("worker_id").size()
    print(f"空字串轉成 NaN 後：{len(g)} 組，合計 {g.sum()}——{len(ev) - g.sum()} 筆不見了，沒有警告")
    g = as_nan.groupby("worker_id", dropna=False).size()
    print(f"加上 dropna=False：{len(g)} 組，合計 {g.sum()}；NaN 組 {g[g.index.isna()].iloc[0]} 筆")

    print("\n== 6. 沒有事件的人：用名冊補回 ==")
    roster = read_roster()
    counts = known.groupby("worker_id").size()
    print(f"groupby 結果 {len(counts)} 人；名冊 {len(roster)} 列、不同 worker_id {roster['worker_id'].nunique()} 個")
    dup = counts.reindex(roster["worker_id"], fill_value=0)
    print(f"reindex(名冊整欄)：{len(dup)} 列，W023 出現 {int((dup.index == 'W023').sum())} 次，事件合計 {dup.sum()}（多算 {dup.sum() - len(known)}）")
    table = per_worker(ev, roster, viol)
    zero = table.index[table["events"] == 0].tolist()
    print(f"reindex(不重複 worker_id)：{len(table)} 列，事件合計 {table['events'].sum()}；事件 0 的 {len(zero)} 人：{zero[0]}…{zero[-1]}")

    print(f"\n== 7. 每人彙總表：{len(table)} 列，分母寫在表上 ==")
    print(f"原始 {len(raw)} 列 → 每人 {len(table)} 列；另有未辨識 {len(ev) - len(known)} 筆事件不屬於任何人")
    print(table.sort_values("violations", ascending=False, kind="stable").head(5).to_string())
    print("…")
    print(table.tail(3).to_string())
```

執行（在本目錄下）：

```bash
python3 12_groupby_denominator.py
```

最後一段：

```text
== 7. 每人彙總表：60 列，分母寫在表上 ==
原始 2838 列 → 每人 60 列；另有未辨識 364 筆事件不屬於任何人
           events  violations  violation_rate
worker_id                                    
W041           67          36           0.537
W029           51          33           0.647
W044           47          27           0.574
W018           42          23           0.548
W007           52          16           0.308
…
           events  violations  violation_rate
worker_id                                    
W058            0           0             NaN
W059            0           0             NaN
W060            0           0             NaN
```

讀它的方式：

- **2838 列 → 60 列**。表上每一列都是一個人，60 個人一個不少；認不出臉的 364 筆不屬於任何人，**另外寫出來**，不偷偷混成一個叫 `""` 的工人，也不讓它無聲消失。
- 前五名正是 MANIFEST 埋入的五位重複違規者（W041、W029、W044、W018、W007）。第五名其實並列：W017 也是 16 次，`kind="stable"` 讓並列時照名冊順序排，輸出才不會每次不同。W041 的 36 次違規裡，有 18 次是 09-22 下午連續發生的——第 13、15 節會再回來看他。
- 最後三位 `events=0`、`violation_rate=NaN`：**他們在名冊上，只是攝影機沒拍到**。這張表交給下游時，0 跟 NaN 必須保持不同。

## Workshop：區域 × 週的違規表

### 任務與時間

**35–42 分鐘：做表。** 用去重後的事件，產出「區域 × 週」的彙總表：事件數、違規數、違規率。週的切法：台灣時間、週一到週日（第 11 節）。

```python
# Workshop 起手式，本節測試不涵蓋這段
raw, ev = read_events()
ev["is_violation"] = ev["event_type"].isin(violation_types())
t = pd.to_datetime(ev["event_time"], format="ISO8601").dt.tz_convert("Asia/Taipei")
ev["week"] = t.dt.tz_localize(None).dt.to_period("W-SUN").astype(str)
table = ev.groupby(["zone", "week"]).agg(...)   # 你來寫
```

然後回答：**表有幾列？違規率的分母是什麼？** 把答案寫在表的下面，一句話。

**42–46 分鐘：加總核對。** 你的表的 `events` 加總起來應該是多少？寫一行 `assert` 證明它。

**46–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫「讀 events.jsonl，算每個工人的違規次數與違規率，列出前三名」。拿它的程式檢查四件事：有沒有去重？`count` 用在哪一欄？「違規」是怎麼判定的？結果裡有沒有一個叫 `""` 的人、有沒有 W053？

### 參考判讀

- 表有 **16 列**（4 區 × 4 週），`events` 加總 **2818**。違規率的分母是「該區該週的全部偵測（含認不出人的）」。教師實測最高的一格是 **Z4 第 4 週（09-21～09-27）0.323**（42／130）——W041 在 09-22 的那串連續事件就在這裡。
- 若你的 `events` 加總是 2838，你忘了去重；若是 2454，你在某一步把認不出人的事件丟了（例如先轉 `NaN` 再分組）。**加總核對**是這兩種錯唯一的警報。
- 常見的 AI 版本（教師實測，一行 `read_json` ＋ `event_type != "ppe_ok"` ＋ `count`）得到 **53 組、合計 2838**：沒有去重，而且**第一名是 `""`**（總數 367、違規 77）——它把「認不出臉」當成一位違規最多的工人。W053–W060 不在結果裡。排第二的 W041（67／36）數字碰巧沒錯，因為重送的 20 筆裡沒有他的事件；**數字對了不代表方法對**。
- 「違規」若寫成 `event_type != "ppe_ok"`，本資料剛好跟 `event-types.csv` 的 `is_violation` 一致（4 種類型）；上游哪天新增一種非違規類型（例如 `vest_ok`），它就會被算成違規。違規的定義應該來自對照表，不是寫死在程式裡。

### 驗收

- 區域 × 週表 16 列，附一句分母說明，`assert table["events"].sum() == 2818` 通過。
- 能說出 `size` 與 `count` 在 cam-08 的差別，以及為什麼 `worker_id` 的 `count` 沒有少。
- 能說出四個違規率各自的分子與分母，並指出「只算已辨識」為什麼比較低。
- AI 版本的四件事都檢查過，至少指出兩個錯。
- 每人彙總表 60 列、W053–W060 在表上、W023 只出現一次。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，Demo **標準輸出逐字相同**。Workshop 的區域 × 週表兩版數字相同；AI 版本的 `worker_id` dtype 在 2.3.3 顯示 `object`、3.0 顯示 `str`，不影響計數。

> 兩版都實測過：`groupby` 預設丟掉 `NaN` 分組鍵（`dropna=True`）、`count` 不把空字串當缺值、`nunique` 把空字串算一個值。

**資料**：`data/events/` 為合成資料（`tools/build_events.py`，固定種子），人名、工號、事件皆虛構，**不代表任何真實工地的違規率**。本節用到的埋入狀況：重送 20 筆（違規 2 筆）、cam-08 無 confidence、worker_id 空字串 364 筆、W053–W060 無事件、W023 名冊兩列、W041 連續違規。違規的判定一律取自 `event-types.csv` 的 `is_violation`。

**界線**：本節的「每人違規率」只是描述，不是績效指標——偵測次數取決於這個人在哪一區工作、攝影機拍到他幾次，跨區比較並不公平。本節沒有處理 cam-02 的百分比 confidence（第 08 節），所以刻意沒有算平均信心度。本節**尚未實班試教**。

**舊教材**：改寫自 [依人／時間／區域彙總事件](https://hackmd.io/@yillkid/HyLKrIRE-e)。保留「事件 ≠ 行為、彙總是把很多列壓成少數列」的定位與 `groupby().size()` 作為第一個 API；**時間彙總移往第 11 節**；`value_counts` 的 Top-K 移往第 07 節（第 15 節的摘要再用到）；舊版「比例＝次數／總數」只有一種分母，改為四種分母對照；`size`／`count` 差異、named aggregation、`dropna`、名冊補人為新增。濃縮 [從事件到「行為紀錄」](https://hackmd.io/@yillkid/BJK6uTU4Zx)：只保留「單一事件＝事實，多個事件＝行為」一句；`shift`／`diff` 的序列語境本節不教（第 15 節的「連續違規」改用「同一人同一天違規達 5 筆」的規則，也沒有用 `shift`），舊版「太早 groupby 會破壞行為語境」的提醒改寫成第一段的去重與分母問題。

**下一節**：第 13 節〈衍生欄位與可稽核規則〉——有了每人違規次數，下一步是把它分級成 `risk_level`。分級的門檻從哪裡來、誰能檢查，比用哪個函式分級更重要。
