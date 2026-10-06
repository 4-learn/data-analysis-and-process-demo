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
