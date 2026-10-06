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
