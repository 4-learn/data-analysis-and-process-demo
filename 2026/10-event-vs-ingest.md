# 10｜事件發生時間 vs 資料到達時間

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 10 節：事件發生時間 vs 資料到達時間。**
> 本節用工地事件的兩個時間欄——`event_time`（攝影機看到的那一刻，台北時間）與 `ingested_at`（伺服器收到的那一刻，UTC）——示範「以哪個時間彙總」怎麼改變每日計數：cam-05 斷線後隔天補傳，20 筆事件從 09-10 搬到 09-11；直接取 UTC 日期，210 筆早上 7 點的事件被算到前一天。最後把同樣的區分套回法規：抓到的時間不是修正的時間。
> 本節不是 `to_datetime`／時區／`resample` 的語法課（那是第 11 節），也不重教去重與冪等（第 09 節）。這裡只回答一個問題：**這一列算在哪一天？**

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 範例程式碼

- [demo：10_event_vs_ingest.py](https://github.com/4-learn/data-analysis-and-process-demo/blob/master/2026/10_event_vs_ingest.py)（與本頁 Demo 逐字相同）
- 練習資料與環境說明：[2026/README](https://github.com/4-learn/data-analysis-and-process-demo/tree/master/2026)

## 學習目標與時間

完成後，你能：說出一筆資料的「發生時間」與「到達時間」各回答什麼問題；指出以兩者分別做每日計數時，差異落在哪幾列、為什麼；說明「在某個時刻看某一天」為什麼會得到不同的數字；不再把 UTC 時間戳的日期當成本地日期。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–6 分鐘 | 檔案順序不是發生順序 | 45 列比上一列更早發生；最長延遲近 23 小時 |
| 6–12 分鐘 | 先去重 | 20 個 `event_id` 送了兩次，相隔 14 分鐘 |
| 12–24 分鐘 | 以哪個時間彙總 | 09-10：117 筆 vs 97 筆，差的 20 列全是 cam-05 |
| 24–30 分鐘 | UTC 日期不是台北日期 | 230 列算錯天，週日停工卻有 31 筆 |
| 30–35 分鐘 | 法規的兩個時間 | `modified_date` vs `fetched_at` |
| 35–50 分鐘 | Workshop：兩種每日計數 | 差異列清單＋哪個合理 |

先修：本課第 09 節（`event_id` 去重、`fetched_at` 比較先後）、第 03 節（`dtype=False, convert_dates=False`）。環境同第 02 節。

## 一、檔案順序＝到達順序，不是發生順序

`data/events/events.jsonl` 每一列有兩個時間（**全部是合成資料**）：

| 欄位 | 回答的問題 | 誰寫的 | 時區 |
| --- | --- | --- | --- |
| `event_time` | 這件事**什麼時候發生**？ | 攝影機 | `+08:00`（工地當地） |
| `ingested_at` | 這筆資料**什麼時候到**我們手上？ | 伺服器 | `+00:00`（UTC） |

檔案是伺服器依收到的順序一行一行寫的。AI 看到時間欄已經「看起來排好了」，常常直接 `df.iloc[0]` 當最早、`diff()` 算間隔、`head()` 當「第一筆事件」。先檢查：

```text
== 1. 檔案順序＝到達順序，不是發生順序 ==
2838 列；依 ingested_at 排好：True；依 event_time 排好：False
延遲中位數 0 days 00:00:10；超過 1 分鐘 40 列（20 個 event_id，每個到了兩次），全是 ['cam-05']
比上一列「更早發生」的列：45 列；其中補傳的列 20、其他 25（其他裡 cam-05 5）
最長延遲（第一次到達）：0 days 22:54:24，cam-05-20260910-0002
                  event_id                 event_time                ingested_at
1159  cam-05-20260910-0023  2026-09-10T14:23:15+08:00  2026-09-11T01:05:21+00:00
1160  cam-05-20260910-0001  2026-09-10T15:43:10+08:00  2026-09-11T01:05:24+00:00
1161  cam-05-20260910-0002  2026-09-10T10:11:05+08:00  2026-09-11T01:05:29+00:00
1162  cam-05-20260910-0020  2026-09-10T16:47:47+08:00  2026-09-11T01:05:34+00:00
```

- 檔案**依到達時間**排好，**不是依發生時間**。
- 大部分事件延遲 10 秒左右，兩個時間幾乎一樣——所以平常看不出差別。也因此，**大多數天兩種寫法算出來一樣，問題只在少數幾天出現**。
- 例外是 cam-05：40 列延遲超過 1 分鐘——但只有 **20 個** `event_id`，因為這批補傳每筆到了兩次（第二段處理）。只看第一次到達，最長延遲 22 小時 54 分（`cam-05-20260910-0002`，09-10 10:11 發生）。上面四列是 09-11 早上 09:05（台北）一口氣補傳的 09-10 事件，發生時間前後亂跳。
- 「比上一列更早發生」的 45 列裡，20 列屬於補傳；其他 25 列是零星的交換：兩支攝影機的事件只差幾秒、延遲不同，到達順序就交換了（cam-05 平常的事件也有 5 列）。延遲 1 秒和 20 秒都算正常。
- 注意找「最長延遲」的寫法：**在未去重的資料上** `delay.idxmax()` 會找到重送的第二份（延遲 23:08:24，多算了重送晚到的 14 分鐘）。Demo 只看每個 `event_id` 第一次到達的那一列，再找最大值。

## 二、先去重：補傳送了兩次

cam-05 的補傳被送了兩次。這是第 09 節的問題，本節只做一件事：**先依 `event_id` 去重，再談時間**。

```text
== 2. 先去重：補傳送了兩次 ==
重複的 event_id 20 個，兩次到達相隔 [Timedelta('0 days 00:14:00')]；2838 列 → 2818 列
不去重，09-11 到達的列數：151；去重後：131
```

不去重，09-11「收到」的資料多算 20 列；若用發生時間彙總，09-10 會是 137 筆而不是 117 筆（教師實測）。兩種錯誤疊在一起，你分不出差異是時間造成的還是重複造成的。**去重要在選時間之前做**。

## 三、以哪個時間彙總，09-10 就是幾筆

同一份 2,818 列，分別依發生日與到達日（**換成台北時間之後**的日期）做每日計數：

```text
== 3. 以哪個時間彙總，09-10 就是幾筆 ==
            依發生日  依到達日（台北）   差
2026-09-09   116       116   0
2026-09-10   117        97 -20
2026-09-11   111       131  20
2026-09-12   126       126   0
兩種日期不同的列：20 列；攝影機 ['cam-05']；發生 09-10 10:11～16:47；到達 09-11 09:05～09:05
開挖區（Z3）09-10 違規：依發生日 2 筆；依到達日 0 筆
在 2026-09-10T23:59 看 09-10 發生的事件：97 筆
在 2026-09-11T12:00 看 09-10 發生的事件：117 筆
```

- **差異只落在 20 列**，全是 cam-05 在 09-10 10:11～16:47 發生、09-11 09:05 才到的事件。其他 22 個施工日兩種計數完全相同（09-09、09-12 差 0 即是例子）。
- 依到達日彙總，開挖區 09-10 的違規是 **0 筆**——那天 cam-06 停機保養，cam-05 又斷線，**「0 筆」的意思是「沒有收到」，不是「沒有違規」**。依發生日是 2 筆。
- **哪一個是對的？看問題。** 「09-10 工地發生了幾次違規」→ 依發生日。「09-11 伺服器處理了多少資料」「這批資料延遲了多久」→ 依到達日。安全報表回答的是前者。
- 但依發生日也有代價：**同一個問題，在不同時刻問，答案不同**。09-10 晚上 23:59 看，09-10 有 97 筆；隔天中午再看，變 117 筆。如果每天晚上自動產出日報，09-10 那份會永遠少 20 筆，而且沒有任何東西提醒你——除非報表上寫明「截至何時」，或在遲到資料進來時重算前一天（重算要冪等，這是第 09 節的工具）。

`as_of(df, day, cutoff)` 就是「在 cutoff 這個時刻，day 當天的事件我們知道幾筆」。它要求 cutoff 帶時區：沒有時區的時刻，跟 `ingest_ts` 比不出先後。

## 四、`ingested_at` 直接取日期：那是 UTC 的日期

AI 常見的寫法是把時間欄的前 10 個字元當日期（`str[:10]`），或讀進來後直接 `.dt.date`。對 `event_time` 剛好沒事（它本來就是台北時間）；對 `ingested_at` 就錯了：

```text
== 4. ingested_at 直接取日期：那是 UTC 的日期 ==
UTC 日期與發生日不同：230 列；其中 07:xx 發生的 210 列（07:xx 發生的共 211 列，沒換日的：['2026-09-16T07:59:56+08:00']）
UTC 日期出現的週日：['2026-08-30', '2026-09-06', '2026-09-13', '2026-09-20']，共 31 筆（週日停工）
            event_id                event_time               ingested_at
cam-05-20260831-0004 2026-08-31T07:04:37+08:00 2026-08-30T23:04:45+00:00
```

- 台北比 UTC 快 8 小時。**早上 07:00–07:59 發生、幾秒後就到的事件，`ingested_at` 是 UTC 前一天 23 點**，210 列就這樣被算到前一天。07:xx 發生的共 211 列，唯一沒換日的是 09-16 07:59:56 發生、20 秒後（台北 08:00:16、UTC 00:00:16）才到的那一列——它到達時 UTC 已經是當天了。另外 20 列是第三段的 cam-05 補傳：它們本來就是隔天才到，跟時區無關。
- 最好認的破綻：**工地週日停工，UTC 日期卻有 4 個週日、共 31 筆**。資料檔的第一列（`cam-05-20260831-0004`）——08-31（週一）早上 07:04 的事件——UTC 日期是 08-30（週日）。
- 這個錯不會出現在第三段的表裡，因為那裡已經先換成台北時間（`tz_convert("Asia/Taipei")`）。換算的寫法是第 11 節的主題；本節只要記住：**「哪一天」永遠要說是哪個時區的哪一天**。

## 五、法規：抓到的時間不是修正的時間

同樣的區分在爬蟲資料上也成立。第 09 節用 `fetched_at` 判斷新舊；但 `fetched_at` 是「**我們什麼時候抓到**」，第 02 節匯出檔的 `modified_date` 才是「**法規什麼時候修正**」：

以下為完整 `10_event_vs_ingest.py`，只讀 `data/`，不寫檔、不連線。

<!-- demo: 10_event_vs_ingest.py -->
```python
"""第 10 節：事件什麼時候發生，和資料什麼時候到，是兩個時間。"""

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
EVENTS = DATA / "events" / "events.jsonl"
TPE = "Asia/Taipei"


def load_events(path=EVENTS):
    """讀進來不讓 pandas 猜，再明確轉型：event_time 帶 +08:00，ingested_at 是 UTC。"""
    df = pd.read_json(path, lines=True, dtype=False, convert_dates=False)
    for col in ("event_time", "ingested_at"):
        if not df[col].str.contains(r"(?:[+-]\d\d:\d\d|Z)$").all():
            raise ValueError(f"{col} 有沒帶時區的值，無法換算")
    df["event_ts"] = pd.to_datetime(df["event_time"], utc=True, format="ISO8601").dt.tz_convert(TPE)
    df["ingest_ts"] = pd.to_datetime(df["ingested_at"], utc=True, format="ISO8601").dt.tz_convert(TPE)
    return df


def dedupe(df):
    """補傳送了兩次：依 event_id 去重，保留先到的（第 09 節的冪等）。"""
    return df.sort_values("ingest_ts", kind="stable").drop_duplicates("event_id", keep="first")


def daily(df, by):
    """by='event'：依事件發生的台北日期；by='ingest'：依資料到達的台北日期。"""
    col = {"event": "event_ts", "ingest": "ingest_ts"}[by]
    return df.groupby(df[col].dt.strftime("%Y-%m-%d")).size()


def as_of(df, day, cutoff):
    """在 cutoff 這個時刻，「day 當天發生的事件」我們知道幾筆？"""
    cutoff = pd.Timestamp(cutoff)
    if cutoff.tzinfo is None:
        raise ValueError("cutoff 要帶時區")
    happened = df["event_ts"].dt.strftime("%Y-%m-%d") == day
    return int((happened & (df["ingest_ts"] <= cutoff)).sum())


def read_modified_dates(folder=DATA / "02-exports"):
    rows = []
    for path in sorted(folder.glob("*.csv")):
        for enc in ("utf-8-sig", "cp950"):
            try:
                df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding=enc)
                break
            except UnicodeDecodeError:
                continue
        rows.append(df[["pcode", "law_name", "modified_date"]].drop_duplicates())
    return pd.concat(rows, ignore_index=True)


if __name__ == "__main__":
    raw = load_events()
    cols = ["event_id", "event_time", "ingested_at"]

    print("== 1. 檔案順序＝到達順序，不是發生順序 ==")
    print(f"{len(raw)} 列；依 ingested_at 排好：{raw['ingest_ts'].is_monotonic_increasing}；"
          f"依 event_time 排好：{raw['event_ts'].is_monotonic_increasing}")
    delay = raw["ingest_ts"] - raw["event_ts"]
    late = delay > pd.Timedelta("1min")
    print(f"延遲中位數 {delay.median()}；超過 1 分鐘 {int(late.sum())} 列（{raw.loc[late, 'event_id'].nunique()} 個 event_id，"
          f"每個到了兩次），全是 {sorted(raw.loc[late, 'camera_id'].unique())}")
    back = raw["event_ts"] < raw["event_ts"].shift()
    print(f"比上一列「更早發生」的列：{int(back.sum())} 列；其中補傳的列 {int((back & late).sum())}、"
          f"其他 {int((back & ~late).sum())}（其他裡 cam-05 {int((back & ~late & (raw['camera_id'] == 'cam-05')).sum())}）")
    first = delay[~raw["event_id"].duplicated()]          # 每個 event_id 只看第一次到達（重送見第二段）
    i = first.idxmax()
    print(f"最長延遲（第一次到達）：{first.max()}，{raw.loc[i, 'event_id']}")
    print(raw.loc[i - 2:i + 1, cols].to_string())

    print("\n== 2. 先去重：補傳送了兩次 ==")
    twice = raw[raw["event_id"].duplicated(keep=False)]
    gap = twice.groupby("event_id")["ingest_ts"].agg(lambda s: s.max() - s.min())
    events = dedupe(raw)
    print(f"重複的 event_id {twice['event_id'].nunique()} 個，兩次到達相隔 {sorted(set(gap))}；"
          f"{len(raw)} 列 → {len(events)} 列")
    print(f"不去重，09-11 到達的列數：{int(daily(raw, 'ingest')['2026-09-11'])}；去重後：{int(daily(events, 'ingest')['2026-09-11'])}")

    print("\n== 3. 以哪個時間彙總，09-10 就是幾筆 ==")
    table = pd.DataFrame({"依發生日": daily(events, "event"), "依到達日（台北）": daily(events, "ingest")})
    table["差"] = table["依到達日（台北）"] - table["依發生日"]
    print(table.loc["2026-09-09":"2026-09-12"].to_string())
    moved = events[events["event_ts"].dt.date != events["ingest_ts"].dt.date]
    print(f"兩種日期不同的列：{len(moved)} 列；攝影機 {sorted(moved['camera_id'].unique())}；"
          f"發生 {moved['event_ts'].min():%m-%d %H:%M}～{moved['event_ts'].max():%H:%M}；"
          f"到達 {moved['ingest_ts'].min():%m-%d %H:%M}～{moved['ingest_ts'].max():%H:%M}")
    z3 = events[(events["zone"] == "Z3") & (events["event_type"] != "ppe_ok")]
    print(f"開挖區（Z3）09-10 違規：依發生日 {int(daily(z3, 'event').get('2026-09-10', 0))} 筆；"
          f"依到達日 {int(daily(z3, 'ingest').get('2026-09-10', 0))} 筆")
    for cutoff in ("2026-09-10T23:59:59+08:00", "2026-09-11T12:00:00+08:00"):
        print(f"在 {cutoff[:16]} 看 09-10 發生的事件：{as_of(events, '2026-09-10', cutoff)} 筆")

    print("\n== 4. ingested_at 直接取日期：那是 UTC 的日期 ==")
    utc_day = events.groupby(events["ingested_at"].str[:10]).size()
    wrong = events[events["ingested_at"].str[:10] != events["event_ts"].dt.strftime("%Y-%m-%d")]
    h7 = events["event_ts"].dt.hour == 7
    print(f"UTC 日期與發生日不同：{len(wrong)} 列；其中 07:xx 發生的 {int((wrong['event_ts'].dt.hour == 7).sum())} 列"
          f"（07:xx 發生的共 {int(h7.sum())} 列，沒換日的：{events.loc[h7 & ~events.index.isin(wrong.index), 'event_time'].tolist()}）")
    sundays = [d for d in utc_day.index if pd.Timestamp(d).dayofweek == 6]
    print(f"UTC 日期出現的週日：{sundays}，共 {int(utc_day[sundays].sum())} 筆（週日停工）")
    print(raw.iloc[[0]][["event_id", "event_time", "ingested_at"]].to_string(index=False))   # 檔案第一列

    print("\n== 5. 法規：抓到的時間不是修正的時間 ==")
    articles = pd.read_json(DATA / "articles.jsonl", lines=True, dtype=False, convert_dates=False)
    laws = read_modified_dates()
    laws["fetched_at"] = laws["pcode"].map(articles.groupby("pcode")["fetched_at"].max())
    laws["modified_date"] = pd.to_datetime(laws["modified_date"], format="%Y%m%d").dt.date
    print(laws.to_string(index=False))
    print(f"articles.jsonl 的 fetched_at：{articles['fetched_at'].nunique()} 種值；"
          f"modified_date 橫跨 {min(laws['modified_date'])}～{max(laws['modified_date'])}")
```

執行（在本目錄下）：

```bash
python3 10_event_vs_ingest.py
```

第五段輸出：

```text
== 5. 法規：抓到的時間不是修正的時間 ==
   pcode  law_name modified_date                fetched_at
N0020007   勞資爭議處理法    2021-04-28 2026-10-05T04:05:23+00:00
N0030001     勞動基準法    2024-07-31 2026-10-05T04:05:23+00:00
N0020012 大量解僱勞工保護法    2015-07-01 2026-10-05T04:05:23+00:00
articles.jsonl 的 fetched_at：1 種值；modified_date 橫跨 2015-07-01～2024-07-31
```

讀它的方式：

- 749 條的 `fetched_at` 只有一種值：一次全量爬取，全部是同一刻。它只能回答「我們手上的版本是什麼時候的」，**不能**回答「這條法規是什麼時候改的」。
- 三部法規的 `modified_date` 相差九年。如果下游有人問「勞動基準法最近一次修正是什麼時候」，拿 `fetched_at` 回答會說「2026-10-05」——錯。
- 這和第三段是同一件事：`modified_date` 是事件時間，`fetched_at` 是到達時間。第 09 節「較新的 `fetched_at` 勝出」是對的，因為那裡的問題是「哪一份是我們最後拿到的」；問題換成「哪一版是最新的法規」，就要看 `modified_date`。
- 練習站的條文**可能經刻意修改，不具法律效力**；`modified_date` 是練習站匯出檔的值，不代表官方法規資料庫的實際修正日。

## Workshop：兩種每日計數，哪個合理？

### 任務與時間

**35–42 分鐘：兩種每日計數。** 以去重後的 2,818 列，做「每日 × 違規／非違規」的計數兩份：一份依 `event_time` 的台北日期，一份依 `ingested_at` 換成台北時間後的日期。把兩份並排，列出**差異不為 0 的日期**，再列出**造成差異的每一列**（`event_id`、兩個時間、`event_type`）。

**42–46 分鐘：寫一句話判讀。** 主管要「每天的違規次數」，你交哪一份？如果日報每天 23:59 自動產出，09-10 那份會是幾筆？你要在報表上加什麼說明？

**46–50 分鐘：抓 AI 的錯。** 請 OpenCode「用 `events.jsonl` 算每天的事件數」。拿它的程式驗收：

1. 它用的是 `event_time` 還是 `ingested_at`？有沒有說明為什麼？
2. 有沒有依 `event_id` 去重？09-10 是 117 嗎？
3. 若它用 `ingested_at`：日期是 UTC 還是台北？結果裡有沒有週日？

### 參考判讀

- 依兩種日期做每日計數，差異只有 09-10（−20）與 09-11（+20）。造成差異的 20 列全是 cam-05、`event_id` 為 `cam-05-20260910-*`，發生於 09-10 10:11～16:47，台北時間 09-11 09:05 到達；其中 18 筆 `ppe_ok`、2 筆 `restricted_entry`（教師實測）。
- 交依發生日的那一份——問題是「哪天發生了幾次違規」。但要寫明「截至何時」；若 23:59 自動產出，09-10 會是 97 筆而不是 117 筆，差的 20 筆隔天 09:05 才到。若要日報可信，遲到的資料進來時要重算前一天。
- 教師實測一個常見 AI 版本（預設 `pd.read_json(lines=True)`，不去重，`groupby(df["ingested_at"].dt.date)`）：09-10 是 **95**、09-11 是 **154**，表上有 28 天（含 4 個週日）。換成 `event_time.dt.date`、仍不去重，09-10 是 **137**。三個數字都不是 117。
- 用 `ingested_at` 的 UTC 日期，**28 天中有 24 天的計數跟發生日不同**（教師實測，去重後）：差異不只 09-10，而是幾乎每一天都被 07:xx 的事件推到前一天。只檢查「09-10 對不對」的人會漏掉。
- 預設 `read_json` 會自動把 `_at`／`_time` 結尾的欄位（本資料是 `event_time`、`ingested_at`、`handled_at` 三欄）轉成帶時區的日期（第 03 節），`event_time` 保留 `+08:00`、`ingested_at` 是 UTC——所以 AI 版本對 `event_time` 取 `.dt.date` 剛好是對的。**剛好對**，不是寫對；換一個以 UTC 輸出 `event_time` 的廠商就錯了。

### 驗收

- 交出兩種每日計數並排的表，以及造成差異的 20 列清單。
- 能說出 09-10 依發生日、依到達日各是幾筆，各回答什麼問題，主管該看哪一個。
- 能解釋 UTC 日期為什麼會出現週日，並指出第一列（`cam-05-20260831-0004`）在 UTC 是哪一天。
- AI 版本三個問題都有答案。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，**標準輸出逐字相同**。〈參考判讀〉的 AI 版本數字為教師另以兩個環境執行片段所得，結果相同（pandas 2.3.3 的日期解析度是 `ns`，不影響計數）。

**資料**：`data/events/` 由 `tools/build_events.py` 產生，**全部為合成資料**；cam-05 斷線與補傳、補傳重送兩次、07:xx 跨日都是刻意埋入（`MANIFEST.json` 的 `planted`）。法規 `modified_date` 取自 `data/02-exports/` 三部法規匯出（第 02 節），`fetched_at` 取自 `data/articles.jsonl`。

**界線**：

- 本節只示範一種遲到（斷線補傳）。真實系統還有時鐘不準（攝影機時間比伺服器快）、時區設定錯誤、批次重跑等；判斷方式相同——找出兩個時間的差，看它集中在哪裡。
- 「遲到資料進來時重算前一天」本節只點出需求，不實作；它需要第 09 節的冪等合併。
- `as_of()` 以 `ingest_ts <= cutoff` 判定「當時知道」；cutoff 恰為 09-11 09:05:00 時是 97 筆（補傳最早一列在 09:05:01 到達），09:06 是 117 筆（教師實測）。
- 本節**尚未實班試教**。

**舊教材**：改寫自 [事件資料的時間觀念](https://hackmd.io/@yillkid/SJG4Da84Zl)。保留核心主張「一列一個時間點、時間要能排序與運算」與「看起來像時間 ≠ 能被計算的時間」（後者移往第 11 節）。**刪除**三種設計（step／day／start-end）的判斷題：學生已在 MariaDB 課設計過資料表，這一題層次太淺。**新增**舊版沒有的 event time vs ingestion time、遲到資料、UTC 日期陷阱，以及與爬蟲 `fetched_at` 的對照。

**下一節**：第 11 節〈to_datetime、時區與期間彙總〉——本節的「換成台北時間的日期」用了 `to_datetime(..., utc=True)` 與 `tz_convert`；下一節正式講這些工具，以及沒有時區的時間、混合時區、`resample` 與週的起點。
