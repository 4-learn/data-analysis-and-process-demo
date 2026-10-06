# 11｜to_datetime、時區與期間彙總

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 11 節：to_datetime、時區與期間彙總。**
> 本節把兩份來源的時間字串變成**時區明確**的 datetime，再做「每日 × 區域」與「每週」彙總。會遇到四個不報錯、或報錯方式依版本而不同的陷阱：`errors="coerce"` 安靜丟資料、沒有時區的時間被 `utc=True` 當成 UTC（差 8 小時）、混合時區字串、以及「週從哪天開始」與「沒事件的日子是 0 還是不存在」。
> 本節不是「事件時間 vs 到達時間」（第 10 節），也不是分母與比例（第 12 節）。這裡處理的是：**時間欄變成 datetime 之後，切日、切週切得對不對。**

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：用 `to_datetime` 的 `format` 與 `errors` 讓壞資料報錯而不是消失；對沒有時區的時間做 `tz_localize`，對混合時區的字串用 `utc=True` 再 `tz_convert`；說出 `dt.date`、`dt.floor`、`dt.hour` 各回傳什麼；用 `Grouper`／`resample` 做日與週的彙總，並指出週的起點與 0 列對結果的影響。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–6 分鐘 | 格式與 `errors` | `format` 讓壞格子報錯；`coerce` 讓它安靜變 NaT |
| 6–14 分鐘 | 沒有時區的時間 | `tz_localize` vs `utc=True`：65 筆換了日期 |
| 14–19 分鐘 | 混合時區 | pandas 3 拋例外、pandas 2.3 給 `object` |
| 19–23 分鐘 | `dt` 存取子 | `dt.date` 是 Python 物件；`dt.floor` 留著時區 |
| 23–30 分鐘 | 每日計數 | 24 天、27 天、95 格：誰補 0、誰不補 |
| 30–35 分鐘 | 週彙總 | `W` 4 週、`W-MON` 5 週 |
| 35–50 分鐘 | Workshop：每日 × 區域、週彙總 | 時區明確的兩張表 |

先修：本課第 10 節（`event_time` 與 `ingested_at`、台北日期 vs UTC 日期）、第 03 節（`convert_dates=False`）、第 08 節（0 和缺值不一樣）。環境同第 02 節。

## 一、格式與 `errors`

本節用兩份來源（**全部是合成資料**）：

| 檔案 | 時間欄 | 長相 | 時區 |
| --- | --- | --- | --- |
| `events/events.jsonl` | `event_time` | `2026-08-31T07:04:37+08:00` | 有（台北） |
| `events/dashboard-export.csv` | `發生時間` | `2026/08/31 07:04` | **沒有**；廠商說是工地當地時間 |

儀表板匯出是第 1 週的 692 筆，和 `events.jsonl` 同一批事件。先把 `發生時間` 轉成 datetime，再故意在記憶體裡弄壞兩格（一格換成 `-` 分隔、一格寫 `N/A`）：

```text
== 1. 格式與 errors ==
692 列 → dtype 是 datetime：True；時區：None
format 指定、遇到不符：ValueError: time data "2026-08-31 07:20" doesn't match format "%Y/%m/%d %H:%M"
errors='coerce'：不報錯，2 格變 NaT；之後 dropna 就少 2 筆事件，沒有任何訊息
```

- **寫明 `format`**：格式不符就拋 `ValueError`，而且告訴你是哪個值。你會知道上游換了格式。
- **`errors="coerce"`**：不報錯，壞的格子變 `NaT`。這是 AI 很愛加的參數（「讓程式不要當掉」）——之後任何 `dropna()` 或時間篩選都會把這兩筆事件安靜地丟掉，跟第 08 節的 `dropna` 是同一件事。要用 `coerce`，就要接著數 `isna().sum()`，並把變成 NaT 的列交出來。
- 轉好的時間**時區是 `None`**。datetime 型別對了，但它還不知道自己是哪裡的時間。

> 網路上的舊教學常用 `errors="ignore"`（轉不了就原樣回傳）。教師實測：pandas 2.3.3 會發出 `FutureWarning: errors='ignore' is deprecated`；pandas 3.0.6 傳入時拋出沒有訊息的 `AssertionError`。看到 AI 這樣寫，直接改掉。本節測試不涵蓋這段。

## 二、沒有時區的時間：localize，不是當成 UTC

要讓儀表板的時間能跟 `events.jsonl` 比較，它需要時區。兩種寫法：

```python
# 本節測試不涵蓋這段（Demo 裡有同樣的寫法）
right = pd.to_datetime(s, format="%Y/%m/%d %H:%M").dt.tz_localize("Asia/Taipei")   # 這是台北時間
wrong = pd.to_datetime(s, format="%Y/%m/%d %H:%M", utc=True)                       # 這是 UTC 時間
```

```text
== 2. 沒有時區的時間：localize，不是當成 UTC ==
原字串 2026/08/31 07:04
tz_localize(TPE)：2026-08-31 07:04:00+08:00
utc=True       ：2026-08-31 15:04:00+08:00（台北時間）
與 events.jsonl 同一筆比對（取到分鐘）：localize 版 692 筆全部相同：True
utc=True 版：65 筆換了日期，11 筆落在週日；出現的小時 [0, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```

- `utc=True` 對**沒有時區**的字串的意思是「**把它當成 UTC**」，不是「幫我轉成 UTC」。早上 07:04 的事件變成台北 15:04，**全部差 8 小時，沒有任何警告**。
- 破綻要你自己去找：工地 07:00–16:59 上工，`utc=True` 版的小時卻是 15 點到半夜 0 點；65 筆換了日期，11 筆落在停工的週日。
- `tz_localize("Asia/Taipei")` 的意思是「這些時間**就是**台北時間」。localize 後跟 `events.jsonl` 同一 `event_id` 逐筆比對（`events.jsonl` 取到分鐘），692 筆全部相同。
- `tz_localize` 只能用在沒有時區的時間上；對已經帶時區的欄位呼叫，pandas 會拋 `TypeError: Already tz-aware, use tz_convert to convert.`（教師實測，兩版相同）。**localize 是「宣告」，convert 是「換算」**。

**沒有時區的時間，時區不是 pandas 能猜的，是你要去問的**：去看廠商文件、或像本節一樣拿另一份帶時區的來源逐筆比對。第 10 節的 `ingested_at` 帶 `+00:00`，`utc=True` 對它是正確的；同一個參數，對這份儀表板就是 8 小時的誤差。

## 三、混合時區的字串

第 10 節的兩個時間欄，一個 `+08:00`、一個 `+00:00`。如果它們被放進同一欄（例如兩個系統的紀錄合併後），會怎樣？

```text
== 3. 混合時區的字串 ==
0    2026-08-31T07:04:37+08:00
1    2026-08-31T07:12:32+08:00
2    2026-08-30T23:04:45+00:00
3    2026-08-30T23:12:51+00:00
ValueError: Mixed timezones detected
utc=True 再 tz_convert： ['08-31 07:04:37', '08-31 07:12:32', '08-31 07:04:45', '08-31 07:12:51']
```

- **pandas 3.0.6**：`to_datetime` 直接拋 `ValueError: Mixed timezones detected. Pass utc=True in to_datetime ...`。
- **pandas 2.3.3**：**不報錯**，回傳 `dtype=object`（一格一個 Python `Timestamp`，各帶各的時區），發出 `FutureWarning`；之後一用 `.dt` 就是 `AttributeError: Can only use .dt accessor with datetimelike values`。也就是說，**同一支程式在 pandas 2 是「後面某一行才壞」，在 pandas 3 是「這一行就壞」**。Demo 在 pandas 2.3.3 這一行印的是 `沒有報錯：dtype=object，.dt 不能用；警告 ['FutureWarning']`。
- 正確寫法兩版相同：`utc=True` 先統一到 UTC，再 `tz_convert("Asia/Taipei")` 換回本地。第 2、3 列（UTC 的 23:04、23:12）換回台北就是 08-31 07:04、07:12——它們正是第 0、1 列的到達時間。

## 四、`dt` 存取子

```text
== 4. dt 存取子 ==
dt.date  → datetime.date(2026, 8, 31)（Python date，欄位 dtype=object）
dt.floor('D') → 2026-08-31 00:00:00+08:00（還是時間，時區還在）
dt.floor('h') → 2026-08-31 07:00:00+08:00
dt.hour 分布： {7: 211, 8: 347, 9: 331, 10: 308, 11: 133, 12: 270, 13: 359, 14: 360, 15: 270, 16: 229}
```

| 寫法 | 回傳 | 適合 |
| --- | --- | --- |
| `dt.date` | Python `datetime.date` 物件，欄位是 `object` | 印出來給人看；`groupby` 鍵 |
| `dt.floor("D")` | 當天 00:00 的 datetime，**時區保留** | 之後還要 `resample`、比大小、跨時區比較 |
| `dt.floor("h")` | 整點 | 每小時計數 |
| `dt.hour` | 整數 0–23 | 依「幾點」分組（不分日期） |

`dt.date` 取的是**這個時區的**日期——所以第 10 節要先 `tz_convert` 到台北再取。對 UTC 時間直接 `dt.date`，就是第 10 節「07:xx 算到前一天」的錯。`dt.hour` 的分布 7–16 點，正好是工地上工時間；第二段 `utc=True` 版的 15–0 點，用這一行就看得出來。

## 五、每日計數：缺列 vs 0 列

工地週日停工。四種寫法算「每天幾筆」：

```text
== 5. 每日計數：缺列 vs 0 列 ==
groupby(dt.date)：24 天；resample('D')：27 天，其中 0 的是 ['09-06 Sun', '09-13 Sun', '09-20 Sun']
groupby(Grouper(freq='D'))：27 天；groupby([Grouper(freq='D'), 'zone'])：24 天
違規 日×區 的 groupby：95 格（24 天 × 4 區 = 96）；缺的那格：['09-01'] ['Z4']
daily_zone()：24 天 × 4 區；Z4 平均每日違規 缺列算 4.96、補 0 算 4.75、連週日也補 0 算 4.22
```

- **`groupby(dt.date)` 只產生有事件的日子**：24 天，週日不存在。
- **`resample("D")` 從第一天到最後一天每天一格**：27 天，三個週日是 0。（09-27 是週日但在最後一筆事件之後，所以不在表裡。）
- **`groupby(pd.Grouper(key="ts", freq="D"))` 只有一個鍵時跟 `resample` 一樣**，27 天、補 0；**再加一個 `zone` 鍵就不補了**，回到 24 天（教師實測，兩版相同）。同一個 `Grouper`，多一個鍵行為就變，這是最容易誤會的地方。
- 違規的「日 × 區」：24 天 × 4 區應有 96 格，`groupby` 只產生 95 格——**09-01 的 Z4 沒有違規，那一格不是 0，是不存在**。

缺列與 0 列會改變平均：Z4「平均每天幾筆違規」，缺列算 4.96（分母 23 天）、補 0 算 4.75（分母 24 個施工日）、連週日也補 0 算 4.22（分母 27 天）。**哪個對？** 「施工日平均」是 4.75；「日曆日平均」是 4.22；4.96 什麼都不是——它的分母是「Z4 有違規的日子」，這是第 12 節「分母是什麼」的伏筆。

`daily_zone(df, workdays)` 的做法：`groupby` 之後用 `unstack(fill_value=0)` 補齊區域，再用 `reindex(workdays, fill_value=0)` 補齊日期。**要補到哪些日子，是你決定的**（施工日？日曆日？），不是 pandas 決定的。

## 六、週彙總：週從哪天開始

以下為完整 `11_datetime_resample.py`，只讀 `data/`，不寫檔、不連線。

<!-- demo: 11_datetime_resample.py -->
```python
"""第 11 節：把字串變成時區明確的時間，再做日／週彙總。"""

import warnings
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data" / "events"
TPE = "Asia/Taipei"
DASH_FORMAT = "%Y/%m/%d %H:%M"


def load_events(path=DATA / "events.jsonl"):
    df = pd.read_json(path, lines=True, dtype=False, convert_dates=False).drop_duplicates("event_id")
    df["ts"] = pd.to_datetime(df["event_time"], format="ISO8601", utc=True).dt.tz_convert(TPE)
    return df.reset_index(drop=True)


def load_dashboard(path=DATA / "dashboard-export.csv", tz=TPE):
    """儀表板匯出的時間沒有時區；廠商文件說是工地當地時間，所以 localize 成台北，不是當成 UTC。"""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df["ts"] = pd.to_datetime(df["發生時間"], format=DASH_FORMAT).dt.tz_localize(tz)
    return df


def require_aware(ts, name="ts"):
    if not pd.api.types.is_datetime64_any_dtype(ts):
        raise TypeError(f"{name} 不是 datetime（dtype={ts.dtype}）")
    if ts.dt.tz is None:
        raise ValueError(f"{name} 沒有時區：先 tz_localize 成資料產生地的時區")
    return ts


def daily_zone(df, workdays=None):
    """每日 × 區域違規數。groupby 只會產生「有事件」的格子；要 0 就得自己給完整的日曆。"""
    require_aware(df["ts"])
    v = df[df["event_type"] != "ppe_ok"]
    table = v.groupby([v["ts"].dt.floor("D"), "zone"]).size().unstack("zone", fill_value=0)
    if workdays is not None:
        table = table.reindex(workdays, fill_value=0)
    return table


def weekly(df, start="MON"):
    """以「週的第一天」為標籤的週彙總：區間是 [start, 下一個 start)。

    pandas 的 'W-XXX' 指的是週的「最後一天」，而且預設 closed='right'、label='right'；
    所以要「週一開始、標籤是週一」得寫 W-MON ＋ closed/label='left'。
    """
    require_aware(df["ts"])
    if start not in ("MON", "SUN"):
        raise ValueError(f"start 只能是 MON 或 SUN：{start!r}")
    s = df.set_index("ts").sort_index()
    return s.resample(f"W-{start}", label="left", closed="left").size()


if __name__ == "__main__":
    events = load_events()
    raw_dash = pd.read_csv(DATA / "dashboard-export.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")

    print("== 1. 格式與 errors ==")
    t = pd.to_datetime(raw_dash["發生時間"], format=DASH_FORMAT)
    print(f"{len(t)} 列 → dtype 是 datetime：{pd.api.types.is_datetime64_any_dtype(t)}；時區：{t.dt.tz}")
    broken = raw_dash["發生時間"].copy()
    broken.iloc[[3, 100]] = ["2026-08-31 07:20", "N/A"]          # 在記憶體裡弄壞兩格
    try:
        pd.to_datetime(broken, format=DASH_FORMAT)
    except ValueError as exc:
        print("format 指定、遇到不符：ValueError:", str(exc).split(",")[0].split(". ")[0])
    coerced = pd.to_datetime(broken, format=DASH_FORMAT, errors="coerce")
    print(f"errors='coerce'：不報錯，{int(coerced.isna().sum())} 格變 NaT；"
          f"之後 dropna 就少 {int(coerced.isna().sum())} 筆事件，沒有任何訊息")

    print("\n== 2. 沒有時區的時間：localize，不是當成 UTC ==")
    right = load_dashboard()["ts"]
    wrong = pd.to_datetime(raw_dash["發生時間"], format=DASH_FORMAT, utc=True).dt.tz_convert(TPE)
    print(f"原字串 {raw_dash['發生時間'].iloc[0]}")
    print(f"tz_localize(TPE)：{right.iloc[0]}")
    print(f"utc=True       ：{wrong.iloc[0]}（台北時間）")
    match = right.reset_index(drop=True).equals(
        events.set_index("event_id").loc[raw_dash["事件編號"], "ts"].dt.floor("min").reset_index(drop=True))
    print(f"與 events.jsonl 同一筆比對（取到分鐘）：localize 版 {len(right)} 筆全部相同：{match}")
    print(f"utc=True 版：{int((wrong.dt.date != right.dt.date).sum())} 筆換了日期，"
          f"{int((wrong.dt.dayofweek == 6).sum())} 筆落在週日；出現的小時 {sorted(wrong.dt.hour.unique().tolist())}")

    print("\n== 3. 混合時區的字串 ==")
    mixed = pd.concat([events["event_time"].head(2), events["ingested_at"].head(2)], ignore_index=True)
    print(mixed.to_string())
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            out = pd.to_datetime(mixed, format="ISO8601")
            try:
                out.dt.hour
                dt_ok = "可以用"
            except AttributeError:
                dt_ok = "不能用"
            print(f"沒有報錯：dtype={out.dtype}，.dt {dt_ok}；警告 {[w.category.__name__ for w in caught]}")
        except ValueError as exc:
            print("ValueError:", str(exc).split(".")[0])
    fixed = pd.to_datetime(mixed, format="ISO8601", utc=True).dt.tz_convert(TPE)
    print("utc=True 再 tz_convert：", fixed.dt.strftime("%m-%d %H:%M:%S").tolist())

    print("\n== 4. dt 存取子 ==")
    ts = events["ts"]
    print(f"dt.date  → {ts.dt.date.iloc[0]!r}（Python date，欄位 dtype={ts.dt.date.dtype}）")
    print(f"dt.floor('D') → {ts.dt.floor('D').iloc[0]}（還是時間，時區還在）")
    print(f"dt.floor('h') → {ts.dt.floor('h').iloc[0]}")
    print("dt.hour 分布：", ts.dt.hour.value_counts().sort_index().to_dict())

    print("\n== 5. 每日計數：缺列 vs 0 列 ==")
    by_date = events.groupby(ts.dt.date).size()
    by_resample = events.set_index("ts").resample("D").size()
    by_grouper = events.groupby(pd.Grouper(key="ts", freq="D")).size()
    print(f"groupby(dt.date)：{len(by_date)} 天；resample('D')：{len(by_resample)} 天，"
          f"其中 0 的是 {by_resample[by_resample == 0].index.strftime('%m-%d %a').tolist()}")
    print(f"groupby(Grouper(freq='D'))：{len(by_grouper)} 天；"
          f"groupby([Grouper(freq='D'), 'zone'])：{events.groupby([pd.Grouper(key='ts', freq='D'), 'zone']).size().index.get_level_values(0).nunique()} 天")
    v = events[events["event_type"] != "ppe_ok"]
    cells = v.groupby([v["ts"].dt.floor("D"), "zone"]).size()
    n_day, n_zone = cells.index.get_level_values(0).nunique(), cells.index.get_level_values(1).nunique()
    print(f"違規 日×區 的 groupby：{len(cells)} 格（{n_day} 天 × {n_zone} 區 = {n_day * n_zone}）；缺的那格：", end="")
    full = cells.unstack("zone")
    print(full[full.isna().any(axis=1)].index.strftime("%m-%d").tolist(), full.columns[full.isna().any()].tolist())
    workdays = by_resample.index[by_resample.index.dayofweek != 6]
    table = daily_zone(events, workdays)
    print(f"daily_zone()：{table.shape[0]} 天 × {table.shape[1]} 區；Z4 平均每日違規 "
          f"缺列算 {cells.xs('Z4', level='zone').mean():.2f}、補 0 算 {table['Z4'].mean():.2f}、"
          f"連週日也補 0 算 {table.reindex(by_resample.index, fill_value=0)['Z4'].mean():.2f}")

    print("\n== 6. 週彙總：週從哪天開始 ==")
    for label, s in [("resample('W')", v.set_index("ts").resample("W").size()),
                     ("resample('W-MON')", v.set_index("ts").resample("W-MON").size()),
                     ("weekly(start='MON')", weekly(v, "MON")),
                     ("weekly(start='SUN')", weekly(v, "SUN"))]:
        print(f"{label:22} {len(s)} 週：", dict(zip(s.index.strftime("%m-%d"), s.tolist())))
```

執行（在本目錄下）：

```bash
python3 11_datetime_resample.py
```

第六段輸出（違規數）：

```text
== 6. 週彙總：週從哪天開始 ==
resample('W')          4 週： {'09-06': 117, '09-13': 116, '09-20': 140, '09-27': 123}
resample('W-MON')      5 週： {'08-31': 23, '09-07': 117, '09-14': 120, '09-21': 135, '09-28': 101}
weekly(start='MON')    4 週： {'08-31': 117, '09-07': 116, '09-14': 140, '09-21': 123}
weekly(start='SUN')    4 週： {'08-30': 117, '09-06': 116, '09-13': 140, '09-20': 123}
```

讀它的方式：

- **`W` 就是 `W-SUN`**：「每週**結束**在週日」，標籤是那個週日。本資料第一天是週一，所以四週剛好是完整的週一到週六。
- **`W-MON` 是「每週結束在週一」**，不是「週一開始」。而且 `resample` 對週的預設是 `closed="right"`、`label="right"`：08-31（週一）自己一週，只有 23 筆；之後每一週是「週二到下週一」。**5 週、第一週只有 23 筆、最後一週標在資料範圍之外的 09-28**——想要「週一開始」卻寫 `W-MON`，表就是這樣。
- 想要「標籤是週的第一天」：`resample("W-MON", closed="left", label="left")`，這就是 `weekly(start="MON")`。數字跟 `W` 相同，只是標籤從週日換成週一。
- `weekly(start="SUN")` 標籤是週日（週日開始）。本資料週日停工，所以數字相同、標籤不同；**換成週日也上工的資料，數字就會不同**。報表上的「第 37 週」是哪 7 天，要寫出來。

## Workshop：每日 × 區域、週彙總

### 任務與時間

**35–42 分鐘：每日 × 區域。** 讀 `events.jsonl`（依 `event_id` 去重），把 `event_time` 轉成台北時區的 datetime，產生「施工日 × 區域」的違規數表：24 列 × 4 欄，沒有違規的格子是 0。印出 `ts` 欄的 dtype 證明時區明確，並回答：09-01 的 Z4 是幾？你的表是怎麼讓它出現的？

**42–46 分鐘：週彙總。** 把上一張表彙總成「週一開始」的週表（4 列 × 4 欄），標籤用週一的日期。再用 `resample("W-MON")`（不加參數）做一次，比較兩者。

**46–50 分鐘：抓 AI 的錯。** 請 OpenCode「讀 `dashboard-export.csv`，轉成 UTC 時間，做每日事件數」。拿它的程式驗收：

1. 它有沒有用 `utc=True` 直接轉沒有時區的 `發生時間`？第一列 `2026/08/31 07:04` 轉完是 UTC 幾點？
2. 換回台北時間後，`dt.hour` 有沒有出現 0 點或 17 點以後？
3. 每日計數有沒有週日？
4. 它的 `to_datetime` 有沒有 `errors="coerce"`？若有，它有沒有回報變成 NaT 的列數？

### 參考判讀

- 「施工日 × 區域」違規數表 24 × 4，合計 Z1 114、Z2 152、Z3 116、Z4 114（與第 12 節每區一列的違規數相同；Z4 的 114 也見於第 08 節）。09-01 的 Z4 是 **0**；只用 `groupby([...]).size().unstack()` 的話，那一格是 NaN（`unstack()` 不給 `fill_value` 時），只用 `groupby` 不 `unstack` 則根本沒有那一列。09-22 的 Z4 是 20（其中 18 筆是第 08 節的 W041）。
- 週一開始的週表（`resample("W-MON", closed="left", label="left")`）：

  | 週一 | Z1 | Z2 | Z3 | Z4 |
  | --- | --- | --- | --- | --- |
  | 08-31 | 26 | 32 | 38 | 21 |
  | 09-07 | 29 | 36 | 26 | 25 |
  | 09-14 | 35 | 49 | 30 | 26 |
  | 09-21 | 24 | 35 | 22 | 42 |

  不加參數的 `resample("W-MON")` 會是 5 列，第一列（08-31）只有 Z1 8、Z2 6、Z3 6、Z4 3——只有週一那一天。用 `dt.isocalendar().week` 分組（ISO 週，週一開始）會得到與上表相同的數字，但標籤是 36–39 週，跨年時要小心（教師實測；本節測試不涵蓋 ISO 週）。
- AI 版本若對 `發生時間` 用 `utc=True`：第一列變成 `2026-08-31 07:04:00+00:00`，換回台北是 15:04；小時出現 0、15–23；每日計數有 11 筆落在週日（第二段的數字）。**程式完全沒報錯**。若它「轉成 UTC」的做法是先 `tz_localize("Asia/Taipei")` 再 `tz_convert("UTC")`，那是對的：第一列是 `2026-08-30 23:04:00+00:00`。
- 若 AI 版本用 `errors="coerce"`：本份儀表板 692 筆格式一致，不會產生 NaT——**這次沒事不代表寫法沒問題**，請學生用第一段的方法弄壞一格驗證它會不會回報。

### 驗收

- 時間欄必須是 datetime 且時區明確：`df["ts"].dt.tz` 印出 `Asia/Taipei`（或 `UTC`，但要說明為什麼），不是 `None`。
- 交出 24 × 4 的「施工日 × 區域」表，09-01 的 Z4 是 0 而不是 NaN 或不存在。
- 交出 4 列的週表，並寫一句話說明週的起點與標籤是哪一天。
- 能說出 `utc=True` 對「沒有時區」與「有時區」的字串各做了什麼。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，**標準輸出只有一行不同**：

- 第三段混合時區：pandas 3.0.6 印 `ValueError: Mixed timezones detected`；pandas 2.3.3 印 `沒有報錯：dtype=object，.dt 不能用；警告 ['FutureWarning']`。已寫入 `test_lesson_11.py` 的 `PANDAS2_DIFFS`。
- 標準輸出以外：日期解析度 pandas 2.3.3 是 `ns`、3.0.6 是 `us`（Demo 不印 dtype 字串，不影響輸出）；`errors="ignore"` 在 2.3.3 是 `FutureWarning`、在 3.0.6 是 `AssertionError`（第一段附註，不在 Demo 內）。其他行為（`tz_localize` 對已有時區拋 `TypeError`、`Grouper` 單鍵補 0／多鍵不補、週的預設 `closed`／`label`）兩版相同。

**資料**：`data/events/` 由 `tools/build_events.py` 產生，**全部為合成資料**。儀表板的 `發生時間` 是由 `event_time` 以台北時間格式化而得（產生器原始碼可查），所以本節「localize 成台北才對」有標準答案；真實廠商匯出沒有產生器可看，要問廠商或像第二段一樣逐筆比對。

**界線**：

- 本節不處理夏令時間（台灣目前不實施）。對有夏令時間的時區，`tz_localize` 會遇到「不存在的時間」與「重複的時間」，需要 `nonexistent`／`ambiguous` 參數；本節未實測，不寫。
- `rolling`（移動平均）本節不教，本課其他節目前也沒有用到。月彙總（`resample("MS")`）語法相同；本資料只有 27 天，不示範。
- 本節**尚未實班試教**。

**舊教材**：改寫自 [timestamp 與 pd.to_datetime](https://hackmd.io/@yillkid/HJ9pDaUEbx)。保留核心主張「字串時間不是可分析的時間，時間轉型要在資料進表那一刻完成」。**修正**兩處：舊版說 pandas 的時間型別是 `datetime64[ns]`——pandas 3.0.6 從字串解析出來的預設是 `datetime64[us]`（教師實測；2.3.3 仍是 `ns`）；舊版的 `pd.to_datetime(df["timestamp"])` 沒有 `format`、沒有時區，本節改為一律寫 `format` 並明確時區。**新增**舊版沒有的時區、`errors`、`Grouper`／`resample`、週的起點與 0 列。舊版的 `diff()` 算事件間隔範例刪除（第 10 節已說明檔案順序不是發生順序，未排序就 `diff()`，去重後的 2,818 列中有 35 個間隔是負的，教師實測）。

**下一節**：第 12 節〈彙總：分母是什麼、漏掉了誰〉——本節的「Z4 平均每日違規 4.96／4.75／4.22」已經碰到分母；下一節正式處理 `size` 與 `count`、比例的分母，以及「沒有事件的人根本不會出現在結果裡」。
