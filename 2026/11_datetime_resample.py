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
