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
