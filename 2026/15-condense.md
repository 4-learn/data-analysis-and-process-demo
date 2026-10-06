# 15｜濃縮：LLM 不該看到三萬筆

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 15 節：濃縮：LLM 不該看到三萬筆。**
> 本節把四週、兩千八百多筆工地 AI 攝影機事件，濃縮成一張「給 LLM 的十行摘要」：Top-K、趨勢、異常、資料註記。重點不是「變短」，而是**每一行都要追得回它是由哪幾筆事件算出來的**，並另附一份明細。
> 本節不是 `groupby` 教學（第 12 節已教），也不處理格式與 token 預算的取捨（那是第 16 節）。這裡只決定：**什麼進摘要、用什麼鍵把它接回原始資料**。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：把事件表濃縮成十行以內、每行帶可回溯鍵的摘要；說出摘要裡哪一行是「平均值」會蓋掉的東西；用鍵在明細裡回答「是哪幾筆」，並量出原始事件與摘要的長度差。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–5 分鐘 | 為什麼不把事件直接丟給 LLM | 長度差四百倍以上 |
| 5–12 分鐘 | AI 的第一版：`groupby` → `to_dict` | 第 1 名是「空字串」；答不出「哪幾筆」 |
| 12–18 分鐘 | 先清理，並記下改了什麼 | 稽核紀錄：去重 20、百分比修正 69 |
| 18–24 分鐘 | 平均值掩蓋了什麼 | W041 平均每天 1.57 筆 vs 單日 18 筆 |
| 24–35 分鐘 | 十行摘要＋明細 | `condense()`、`trace()` |
| 35–50 分鐘 | Workshop：一行改變排名 | 拿掉一個異常，看 Top-K 怎麼變 |

先修：本課第 10–14 節（時間、彙總、可稽核規則、合併）。環境同第 02 節：Python 3.11 以上、pandas 3.0；`to_markdown` 另需 `tabulate`。

## 一、為什麼不把事件直接丟給 LLM

安全主管想問 LLM：「這四週工地狀況如何？誰最需要關心？」最直覺的做法是把 `events.jsonl` 整份貼進去。量一下（第六段有完整輸出；「原始事件」量的是**檔案裡的原始行**，去掉重送的 20 行）：

```text
原始事件（檔案原行，去重後）           字元   975,730  估計 token   722,019
十行摘要（Markdown）           字元     1,655  估計 token     1,137
```

（token 為第 16 節的**保守粗估**，不是任何模型的實測。）

七十二萬 token 不只是「放不下」。即使放得下，模型也得自己數「W041 有幾筆違規」——**數數是 LLM 最不可靠的事之一**，而 pandas 一行就數對了。所以分工是：

- **pandas 負責算**：計數、排名、比率、找異常。
- **LLM 負責說**：把算好的結果寫成主管看得懂的話。
- **摘要負責接**：每一個數字都帶一把鍵，讓人（或下一輪的程式）能回到原始事件核對。

最後一點是本節的主張。**摘要裡沒有鍵，LLM 只能引用你給它的數字，而沒有人能檢查那個數字從哪來。**

## 二、AI 的第一版：`groupby` → `to_dict`

請 AI「把事件彙總成每人違規次數，轉成給 LLM 的格式」，常見答案就是舊教材的終點（後面第五段有完整程式）：

```python
raw[raw["event_type"] != "ppe_ok"].groupby("worker_id").size() \
    .sort_values(ascending=False).head(3).reset_index(name="violations").to_dict("records")
```

```text
== 1. AI 的第一版：groupby → to_dict ==
[{'worker_id': '', 'violations': 77}, {'worker_id': 'W041', 'violations': 36}, {'worker_id': 'W029', 'violations': 33}]
欄位只有 ['worker_id', 'violations']：問「W041 的 36 筆是哪幾筆？」，摘要本身答不出來
違規總數（沒去重）498；第 1 名 worker_id=''
```

跑得動、沒有錯誤訊息，但有三個問題：

1. **第 1 名是空字串**。`worker_id == ""` 是「辨識不到臉」（第 08 節），77 筆來自許多不同的人，被當成一個「人」排進第一名。交給 LLM，它會寫出「編號空白的人員違規最多」。
2. **沒去重**。違規總數 498，比實際的 496 多 2——cam-05 補傳那批送了兩次，裡面剛好有 2 筆違規。數字小，但它證明這份摘要**沒有經過清理**。
3. **答不出「哪幾筆」**。主管看到「W041 違規 36 次」，下一句一定問「是哪幾次？什麼時候？在哪？」。這份摘要只有 `worker_id` 和次數，**要回答只能重跑一次程式**，而且得猜當初是怎麼算的。

## 三、先清理，並記下改了什麼

濃縮之前的資料必須是乾淨的，而且**清理本身要留紀錄**——摘要裡的數字是清理後算的，看摘要的人要知道清理做了什麼。

`clean()` 做三件事：

- **以 `event_id` 去重，留最先到達的那筆**（檔案順序＝到達順序）。兩筆除了 `ingested_at` 晚 14 分鐘之外完全相同（教師實測：去掉 `ingested_at` 後逐欄相等）。
- **cam-02 的百分比 ÷100**。09-15～17 這台輸出 43–99 的數字，是韌體 bug（第 08 節）。以 `confidence > 1` 判斷並標記 `conf_fixed`，**不是默默改掉**。
- **標記補傳**：到達時間晚於事件時間 1 小時以上的事件。全部 20 筆都是 cam-05 09-10 那批；其他事件延遲最多 20 秒（教師實測）。

```text
== 2. 清理：去重、修正百分比，並記下改了什麼 ==
{'原始列數': 2838, '重送去重': 20, 'confidence 百分比÷100': 69, '補傳（到達晚於 1 小時）': 20}
清理後 2818 筆；違規 496 筆
```

不修百分比會怎樣？第三段最後一行：同樣是去重後的 2818 筆，只差「有沒有 ÷100」，全場平均 confidence 從 0.774 變成 **2.682**——69 筆就把兩千多筆的平均拉到不可能的值。（兩個數字要在同一批列上比；拿沒去重的 2838 列算「修正前」是 2.667，混進了去重的影響。）cam-08 的 231 個 null 則**不要補**：那是「沒記錄」，`mean()` 預設略過它們，摘要不拿 confidence 做結論。

## 四、平均值掩蓋了什麼

```text
== 3. 平均值掩蓋了什麼 ==
每週違規率：08-31 16.9%、09-07 16.7%、09-14 19.6%、09-21 17.1%
W041：出勤 23 天、違規 36 筆，平均每天 1.57 筆；單日最多 18 筆（2026-09-22）
W029：出勤 21 天、違規 33 筆，平均每天 1.57 筆；單日最多 3 筆（2026-09-10）
全場平均 confidence（去重後 2818 筆）：修正前 2.682，修正後 0.774
```

- **每週違規率很平**：16.9%、16.7%、19.6%、17.1%。如果摘要只寫「各週違規率約 17%，無明顯變化」，這句話是對的，而且**完全看不到 09-22 下午發生的事**。
- **W041 平均每天 1.57 筆，W029 也是 1.57 筆**——只看平均，兩人分不出差別。但 W029 單日最多 3 筆，W041 有一天是 **18 筆**：09-22 14:02 起在施工架連續被偵測到未掛安全帶，相鄰兩筆間隔 2–4 分鐘（約每 3 分鐘一筆）、從 14:02 到 14:53。這是**真的危險**（第 08 節），不是雜訊，不能被平均掉，也不能被當成離群值刪掉。

所以摘要要有一類「異常清單」，規則寫死、可稽核（第 13 節）：**同一人同一天違規達 5 筆即列入**。為什麼是 5？本資料除 W041 那天以外，單日最多 3 筆（教師實測：門檻設 3 會列出 14 組、設 4 只剩 W041 這一組）。門檻是看過分布才定的，要寫在規則旁邊。

## 五、十行摘要＋明細

摘要長這樣：每一列有**類別、項目、筆數 `n`、說明，以及 `key`**。`key` 是一個可以直接丟給 `ev.query()` 的條件字串——**用它查出來的筆數必須等於 `n`**，這是摘要與原始資料之間的契約。

為什麼用查詢條件，不直接附 `event_id` 清單？「Z2 違規 152 筆」附 152 個 `event_id` 就不是十行摘要了。條件很短、人看得懂，而且明細可以隨時重算。`event_id` 清單放在**另一份明細**裡，給程式與稽核用，不給 LLM。

設計決定：

- **未辨識獨立成一列**，不參加人員排名，但不能刪——77 筆違規真的發生了。
- **趨勢用週對週**：最後一週與前一週的筆數和違規率。週從週一起算（`event_time` 的當地日期，第 11 節）。
- **資料註記也是摘要的一部分**：cam-02 修正與 cam-05 補傳。說明欄的攝影機、日期、延遲小時數、異常的時間範圍與間隔，都由 `condense()` 從資料算出來，不是手寫的字串——資料變了，說明跟著變。LLM 要知道「confidence 有一段是修正過的」，才不會引用它做結論；鍵是 `conf_fixed`、`late` 這兩個清理時留下的標記欄。

以下為完整 `15_condense.py`，只讀 `data/events/`，不寫檔、不連線。

<!-- demo: 15_condense.py -->
```python
"""第 15 節：把兩千多筆事件濃縮成給 LLM 的十行摘要，而且每一行都追得回原始事件。"""

import json
import math
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data" / "events"
TOP_K = 3
BURST = 5          # 同一人同一天違規達 5 筆即列為異常（本資料其他人單日最多 3 筆）


def estimate_tokens(text):
    """沿用第 16 節的保守粗估：非 ASCII 字元與數字各算 1、其他 ASCII 算 0.5，再乘 1.2。"""
    heavy = sum(1 for ch in text if not ch.isascii() or ch.isdigit())
    return math.ceil((heavy + (len(text) - heavy) * 0.5) * 1.2)


def read_events(path=DATA / "events.jsonl"):
    return pd.read_json(path, lines=True, dtype=False, convert_dates=False)


def raw_lines(raw, path=DATA / "events.jsonl"):
    """檔案裡的原始 JSONL 行（以 event_id 去重、留最先到達的那行）——這才是「整份貼進去」的長度。

    不用 raw.to_json() 重新序列化：pandas 會把 / 寫成 \\/、拿掉空白，量到的是 pandas 的格式，不是檔案。
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) != len(raw):
        raise ValueError(f"檔案 {len(lines)} 行，DataFrame {len(raw)} 列：行號對不上")
    keep = raw.drop_duplicates("event_id", keep="first").index
    return "\n".join(lines[i] for i in keep) + "\n"


def clean(raw):
    """去重（留最先到達的那筆）、修正 cam-02 的百分比；回傳 (事件, 稽核紀錄)。"""
    ev = raw.drop_duplicates("event_id", keep="first").copy()
    t = pd.to_datetime(ev["event_time"], format="ISO8601")
    lag = pd.to_datetime(ev["ingested_at"], format="ISO8601") - t
    ev["conf_fixed"] = ev["confidence"] > 1
    ev.loc[ev["conf_fixed"], "confidence"] = ev.loc[ev["conf_fixed"], "confidence"] / 100
    ev["late"] = lag > pd.Timedelta(hours=1)
    ev["is_violation"] = ev["event_type"] != "ppe_ok"
    ev["date"] = t.dt.strftime("%Y-%m-%d")
    ev["hour"] = t.dt.hour
    ev["week"] = (t.dt.normalize() - pd.to_timedelta(t.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d")
    audit = {"原始列數": len(raw), "重送去重": len(raw) - len(ev),
             "confidence 百分比÷100": int(ev["conf_fixed"].sum()), "補傳（到達晚於 1 小時）": int(ev["late"].sum())}
    return ev.reset_index(drop=True), audit


def condense(ev, zones):
    """產生十行摘要；每一列的 key 是可以直接丟給 ev.query() 的條件，n 是它選到的筆數。"""
    if ev["event_id"].duplicated().any():
        raise ValueError("event_id 有重複：先 clean() 去重再濃縮，否則每個數字都會多算")
    v = ev[ev["is_violation"]]
    rows = []

    def add(kind, item, key, note=""):
        rows.append({"類別": kind, "項目": item, "n": len(ev.query(key)), "說明": note, "key": key})

    people = v[v["worker_id"] != ""].groupby("worker_id").size().sort_values(ascending=False, kind="stable")
    for wid in people.head(TOP_K).index:
        add("Top 人", wid, f"is_violation and worker_id == '{wid}'",
            f"出現於 {v.loc[v['worker_id'] == wid, 'date'].nunique()} 天")
    add("未辨識", "辨識不到臉", "is_violation and worker_id == ''", "不是一個人，不列入排名")
    zone = v.groupby("zone").size().sort_values(ascending=False, kind="stable").index[0]
    add("Top 區", f"{zone} {zones[zone]}", f"is_violation and zone == '{zone}'")
    hour = int(v.groupby("hour").size().sort_values(ascending=False, kind="stable").index[0])
    add("Top 時段", f"{hour:02d}:00–{hour:02d}:59", f"is_violation and hour == {hour}")
    weeks = v.groupby("week").size()
    last, prev = weeks.index[-1], weeks.index[-2]
    rate = ev.groupby("week")["is_violation"].mean()
    add("趨勢", f"週 {last}", f"is_violation and week == '{last}'",
        f"前週 {weeks[prev]} 筆；違規率 {rate[prev]:.1%}→{rate[last]:.1%}")
    per_day = v[v["worker_id"] != ""].groupby(["worker_id", "date"]).size()
    for (wid, day), n in per_day[per_day >= BURST].items():
        hit = v[(v["worker_id"] == wid) & (v["date"] == day)]
        t = pd.to_datetime(hit["event_time"], format="ISO8601").sort_values()
        gap = math.ceil(t.diff().max().total_seconds() / 60)          # 相鄰兩筆最長間隔，算出來，不寫死「連續」
        types = "、".join(sorted(hit["event_type"].unique()))
        add("異常", f"{wid} {day}", f"is_violation and worker_id == '{wid}' and date == '{day}'",
            f"{t.iloc[0]:%H:%M}–{t.iloc[-1]:%H:%M} {types}，間隔 ≤{gap} 分鐘")
    fixed = ev[ev["conf_fixed"]]
    add("資料註記", f"{'、'.join(sorted(fixed['camera_id'].unique()))} confidence", "conf_fixed",
        f"{fixed['date'].min()[5:]}～{fixed['date'].max()[5:]} 輸出百分比，已÷100")
    late = ev[ev["late"]]
    lag = (pd.to_datetime(late["ingested_at"], format="ISO8601")
           - pd.to_datetime(late["event_time"], format="ISO8601")).dt.total_seconds() / 3600
    add("資料註記", "補傳", "late",
        f"{'、'.join(sorted(late['camera_id'].unique()))} {late['date'].min()[5:]} 的事件晚 "
        f"{math.floor(lag.min())}–{math.ceil(lag.max())} 小時才到；重送已去重")
    return pd.DataFrame(rows)


def trace(ev, summary):
    """可回溯的明細：摘要第幾行 → 它涵蓋的每一筆 event_id。"""
    empty = [key for key in summary["key"] if ev.query(key).empty]
    if empty:
        raise ValueError(f"摘要有 {len(empty)} 列追不回任何事件，例如 {empty[0]!r}")
    parts = [ev.query(key)[["event_id", "event_time", "worker_id", "zone", "event_type"]].assign(line=i + 1)
             for i, key in enumerate(summary["key"])]
    detail = (pd.concat(parts, ignore_index=True)
              .sort_values(["line", "event_time", "event_id"], kind="stable", ignore_index=True))  # 不靠檔案順序
    return detail[["line"] + [c for c in detail.columns if c != "line"]]


if __name__ == "__main__":
    raw = read_events()
    zones = {z: v["name"] for z, v in json.loads((DATA / "MANIFEST.json").read_text(encoding="utf-8"))["zones"].items()}

    print("== 1. AI 的第一版：groupby → to_dict ==")
    naive = (raw[raw["event_type"] != "ppe_ok"].groupby("worker_id").size()
             .sort_values(ascending=False).head(3).reset_index(name="violations").to_dict("records"))
    print(naive)
    print(f"欄位只有 {list(naive[0])}：問「W041 的 36 筆是哪幾筆？」，摘要本身答不出來")
    print(f"違規總數（沒去重）{int((raw['event_type'] != 'ppe_ok').sum())}；第 1 名 worker_id={naive[0]['worker_id']!r}")

    print("\n== 2. 清理：去重、修正百分比，並記下改了什麼 ==")
    ev, audit = clean(raw)
    print(audit)
    print(f"清理後 {len(ev)} 筆；違規 {int(ev['is_violation'].sum())} 筆")

    print("\n== 3. 平均值掩蓋了什麼 ==")
    rate = ev.groupby("week")["is_violation"].mean()
    print("每週違規率：" + "、".join(f"{w[5:]} {r:.1%}" for w, r in rate.items()))
    w41 = ev[ev["is_violation"] & (ev["worker_id"] == "W041")].groupby("date").size()
    days = ev.loc[ev["worker_id"] == "W041", "date"].nunique()
    for wid in ("W041", "W029"):
        per = ev[ev["is_violation"] & (ev["worker_id"] == wid)].groupby("date").size()
        days = ev.loc[ev["worker_id"] == wid, "date"].nunique()
        print(f"{wid}：出勤 {days} 天、違規 {per.sum()} 筆，平均每天 {per.sum() / days:.2f} 筆；單日最多 {per.max()} 筆（{per.idxmax()}）")
    before = raw.drop_duplicates("event_id", keep="first")             # 同樣去重，只差「有沒有 ÷100」
    print(f"全場平均 confidence（去重後 {len(before)} 筆）：修正前 {before['confidence'].mean():.3f}，修正後 {ev['confidence'].mean():.3f}")

    print("\n== 4. 十行摘要：每一列都帶查詢鍵 ==")
    summary = condense(ev, zones)
    print(summary.to_markdown(index=False))

    print("\n== 5. 用鍵回答「哪幾筆？」 ==")
    detail = trace(ev, summary)
    print(f"明細 {len(detail)} 列，涵蓋 {detail['event_id'].nunique()} 個不同事件；每行 n 與明細列數一致："
          f"{(detail.groupby('line').size().values == summary['n'].values).all()}")
    burst = detail[detail["line"] == summary.index[summary["類別"] == "異常"][0] + 1]
    print(burst.head(3).to_string(index=False))
    print(f"…共 {len(burst)} 筆，最後一筆 {burst['event_id'].iloc[-1]}")

    print("\n== 6. 長度：原始事件 vs 摘要 ==")
    md = summary.to_markdown(index=False)
    for label, text in [("原始事件（檔案原行，去重後）", raw_lines(raw)),
                        ("十行摘要（Markdown）", md),
                        ("摘要去掉 key 欄", summary.drop(columns="key").to_markdown(index=False)),
                        ("明細（JSONL，給程式不給 LLM）", detail.to_json(orient="records", lines=True, force_ascii=False))]:
        print(f"{label:24} 字元 {len(text):>9,}  估計 token {estimate_tokens(text):>9,}")
    dense = len("".join(md.split()))
    no_key = len("".join(summary.drop(columns="key").to_markdown(index=False).split()))
    print(f"十行摘要 {len(md):,} 字元中，Markdown 對齊用的空白 {md.count(' '):,} 個；"
          f"去掉空白後 {dense:,} 字元，key 欄佔 {(dense - no_key) / dense:.0%}")
```

執行（在本目錄下）：

```bash
python3 15_condense.py
```

```text
== 4. 十行摘要：每一列都帶查詢鍵 ==
| 類別     | 項目                |   n | 說明                                 | key                                                           |
|:-------|:------------------|----:|:-----------------------------------|:--------------------------------------------------------------|
| Top 人  | W041              |  36 | 出現於 14 天                           | is_violation and worker_id == 'W041'                          |
| Top 人  | W029              |  33 | 出現於 18 天                           | is_violation and worker_id == 'W029'                          |
| Top 人  | W044              |  27 | 出現於 14 天                           | is_violation and worker_id == 'W044'                          |
| 未辨識    | 辨識不到臉             |  77 | 不是一個人，不列入排名                        | is_violation and worker_id == ''                              |
| Top 區  | Z2 鋼構組立           | 152 |                                    | is_violation and zone == 'Z2'                                 |
| Top 時段 | 14:00–14:59       |  78 |                                    | is_violation and hour == 14                                   |
| 趨勢     | 週 2026-09-21      | 123 | 前週 140 筆；違規率 19.6%→17.1%           | is_violation and week == '2026-09-21'                         |
| 異常     | W041 2026-09-22   |  18 | 14:02–14:53 no_harness，間隔 ≤4 分鐘    | is_violation and worker_id == 'W041' and date == '2026-09-22' |
| 資料註記   | cam-02 confidence |  69 | 09-15～09-17 輸出百分比，已÷100            | conf_fixed                                                    |
| 資料註記   | 補傳                |  20 | cam-05 09-10 的事件晚 16–23 小時才到；重送已去重 | late                                                          |
```

讀它的方式：

- **Top 時段 14:00 的 78 筆裡，有 18 筆是 W041 那一次**。拿掉那 18 筆，14 點只剩 60 筆，Top 時段會變成 13 點（64 筆）——一個異常就能改寫一列 Top-K。這正是 Workshop 要你親手驗證的事。
- **趨勢那一列寫「前週 140 筆 → 本週 123 筆」，看起來在改善**。但本週包含 W041 的 18 筆；把它們拿掉是 105 筆，違規率 15.0%。所以「改善」與「最嚴重的一次事件」**同時發生在同一週**。摘要把兩者分成兩列，LLM 才不會只寫其中一句。
- **資料註記列的 `n`** 不是違規數：69 是被修正的事件數（多數是 `ppe_ok`），20 是補傳數。說明欄寫清楚了，但要提醒 LLM 組不要把它加進違規總數。

用鍵回答「哪幾筆？」：

```text
== 5. 用鍵回答「哪幾筆？」 ==
明細 633 列，涵蓋 403 個不同事件；每行 n 與明細列數一致：True
 line             event_id                event_time worker_id zone event_type
    8 cam-07-20260922-0014 2026-09-22T14:02:00+08:00      W041   Z4 no_harness
    8 cam-07-20260922-0015 2026-09-22T14:05:48+08:00      W041   Z4 no_harness
    8 cam-07-20260922-0016 2026-09-22T14:08:38+08:00      W041   Z4 no_harness
…共 18 筆，最後一筆 cam-07-20260922-0031
```

`trace()` 依每一列的 `key` 展開成明細，`line` 對回摘要第幾行；同一行內依 `event_time`、`event_id` 排序，**不依賴檔案的到達順序**（補傳的事件在檔案裡排在隔天，按到達順序列出會錯位）。633 列對應 403 個不同事件——**同一筆事件可以出現在好幾行**（W041 那 18 筆同時在第 1、6、7、8 行），所以明細不能拿來加總。`trace()` 遇到「查不到任何事件」的鍵會直接報錯：鍵寫錯，比沒有鍵更糟。

## 六、長度：原始事件 vs 摘要

```text
== 6. 長度：原始事件 vs 摘要 ==
原始事件（檔案原行，去重後）           字元   975,730  估計 token   722,019
十行摘要（Markdown）           字元     1,655  估計 token     1,137
摘要去掉 key 欄               字元       887  估計 token       657
明細（JSONL，給程式不給 LLM）      字元    89,609  估計 token    67,575
十行摘要 1,655 字元中，Markdown 對齊用的空白 894 個；去掉空白後 750 字元，key 欄佔 47%
```

以估計 token 算，摘要約是原始事件的六百分之一（722,019 ÷ 1,137 ≈ 635 倍；字元約 590 倍）。明細比摘要長約 54 倍（字元），**這是刻意的**：明細不進 context，它是給人稽核、給下一輪程式查的。LLM 回答「W041 那天是幾點到幾點？」時，可以靠摘要說明欄的 `14:02–14:53`；回答不了的細節，系統拿 `key` 去查明細，而不是讓模型猜。

`key` 欄本身佔了摘要約一半的長度：拿掉 `key` 欄是 887 字元（1,655 的 54%）。但 Markdown 表格有 894 個對齊用的空白，長度會跟著最長的那一格變；去掉空白後摘要 750 字元，`key` 欄佔 47%——兩種量法都是「約一半」，結論成立。要不要把 `key` 也送進 LLM，是第 16 節的預算問題；本節的立場是：**摘要檔一定保留它**，送出時可以丟，但丟了就要能用列號接回來。

## Workshop：一個異常，能改寫幾行摘要？

### 任務與時間

**35–42 分鐘：拿掉 W041 那一天。** 假設有人在「清理」時把 W041 09-22 的 18 筆當離群值刪掉。用 Demo 的函式重做摘要，逐行比較：

```python
# Workshop 起手式，本節測試不涵蓋這段
from my_condense import read_events, clean, condense   # 先把本節 Demo 存成 my_condense.py
zones = {"Z1": "出入口", "Z2": "鋼構組立", "Z3": "開挖區", "Z4": "施工架"}
ev, audit = clean(read_events())
cut = ev.query("not (worker_id == 'W041' and date == '2026-09-22' and is_violation)")
print(condense(cut, zones).drop(columns="key").to_string())
```

回答：哪幾行變了？如果交給 LLM 的是這份，它會怎麼描述最後一週？

**42–46 分鐘：鍵的契約。** 對 Demo 的摘要每一行，用 `ev.query(key)` 查出來的筆數是不是等於 `n`？再故意把某一列的 `key` 改錯（例如 `'W041'` 改成 `'W401'`），呼叫 `trace()`，看會發生什麼。

**46–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫「把 events.jsonl 濃縮成給 LLM 的摘要」。拿它的版本檢查四件事：(1) 有沒有以 `event_id` 去重？(2) Top-K 第 1 名是不是空字串？(3) 有沒有用平均（每週違規率、每人平均每天幾筆）取代異常清單？(4) 摘要裡任挑一個數字，**你能不能不重跑它的程式就找出是哪幾筆？**

### 參考判讀

- 拿掉 W041 那 18 筆後（教師實測，2,800 筆）：Top 人變成 W029 33、W044 27、W018 23，**W041 從第 1 名掉出前三**（剩 18 筆）；Top 時段從 14 點（78）變成 **13 點（64）**；最後一週從 123 筆、17.1% 變成 **105 筆、15.0%**；**異常清單整列消失**，摘要從 10 行變 9 行。LLM 拿到這份，會寫出「最後一週明顯改善、無異常」——四週裡最危險的事件，被一次「清理」從四個地方同時抹掉。
- 這也是為什麼第 08 節說「異常要分兩種」：cam-02 的百分比是 bug，修正並註記；W041 是真的出事，**保留並單獨列出**。兩者都進摘要，但類別不同。
- 鍵的契約：Demo 第五段已印出「每行 n 與明細列數一致：True」。把 `key` 改成 `'W401'`，`trace()` 會拋出 `ValueError: 摘要有 1 列追不回任何事件…`。若你的版本只是印出空表格，代表它沒有守這個契約。
- 常見的 AI 版本就是第二段：`groupby("worker_id").size()` 再 `to_dict`。第 1 名是 `''`（77 筆）、總數 498（沒去重）。這兩個錯都**不會有錯誤訊息**；只有你去看第 1 名是誰，才會發現。
- AI 也常寫「每人平均每日違規次數」當作「風險指標」：W041 是 1.57，與 W029 並列（第三段），看不出 W041 有一天 18 筆、W029 單日最多 3 筆。平均值本身沒有錯，錯在**只有平均值**。

### 驗收

- 能重現 Demo 第 4 段的十行摘要，並說出每一列的 `key` 是什麼意思。
- 拿掉 W041 09-22 之後，能指出至少三行的變化（Top 人、Top 時段、趨勢、異常）。
- 能示範：給定摘要任一列，用 `key` 在 30 秒內列出對應的 `event_id`。
- 對 AI 的版本，四項檢查都有結論；至少找出一個「跑得動但答案會誤導」的地方。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6、tabulate 0.10.0。本頁所有輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，標準輸出**逐字相同**。舊稿的「原始事件」長度是用 `to_json()` 重新序列化量的（916,552 字元）：pandas 會去掉 `": "` 後的空白、把 `/` 寫成 `\/`，量到的是 pandas 的輸出格式而不是檔案；現改量檔案原行（975,730 字元）。

**token 數字的等級**：全部是第 16 節的**粗估**（`estimate_tokens()` 同一規則，本節重寫一份以維持單檔），不是 tokenizer 實測。

**資料**：`data/events/` 為 `tools/build_events.py` 產生的**合成資料**（固定種子，雜湊記於 `data/events/MANIFEST.json`）。W041、cam-02、cam-05 都是刻意埋入的狀況，見 MANIFEST 的 `planted`。本節的排名與趨勢**不代表任何真實工地的統計結論**；事件類型對應的法條取自練習站，可能經刻意修改，不具法律效力。

**界線**：

- 異常門檻「單日 5 筆」是看過這份資料的分布後定的，**不是通用標準**；換一個工地要重新看分布。
- `key` 用 `DataFrame.query()` 字串，前提是值裡沒有單引號。本資料的 `worker_id`、`zone`、日期都不會有；若鍵的值來自自由文字，要改用欄位＋值的結構化格式（例如 `{"worker_id": "W041", "date": "2026-09-22"}`）。
- 本節不呼叫 LLM，不宣稱「有鍵的摘要讓模型答得比較好」；那需要評測（LLM 課第 07 節）。本節只驗證「摘要的每個數字都能從原始資料重算出來」。
- 本節**尚未實班試教**。

**舊教材**：改寫自 [Workshop：將事件資料轉為長期行為表](https://hackmd.io/@yillkid/SkKZy30Ebl)。保留：情境（AI 攝影機 × 工地安全）、流程「篩選 → 彙總 → 結構化輸出」、「把事件轉成以人為單位的摘要」的目標。刪除：手打的 4 列 `DataFrame`（改用 2,838 列的真實檔案）、`value` 欄（本資料以 `event_type` 表達）、`timestamp` 轉換步驟（第 11 節已教）。舊版終點 `to_dict(orient="records")` 原樣保留在第二段，作為「沒有鍵的摘要」反例；序列化本身移到第 16 節。

**下一節**：第 16 節〈序列化與 context 預算〉——這份十行摘要要用什麼格式送出？`key` 欄要不要一起送？
