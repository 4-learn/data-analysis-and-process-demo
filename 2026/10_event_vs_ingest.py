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
