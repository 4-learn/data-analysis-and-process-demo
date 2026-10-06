"""第 07 節：欄位選取、布林篩選與 Top-K——挑對資料，並且知道自己挑掉了什麼。"""

import warnings
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
EVENTS = DATA / "events" / "events.jsonl"
TYPES = DATA / "events" / "event-types.csv"


def load_events():
    df = pd.read_json(EVENTS, lines=True, dtype=False, convert_dates=False)
    types = pd.read_csv(TYPES, dtype=str, keep_default_na=False)
    violations = set(types.loc[types["is_violation"] == "true", "event_type"])
    return df.assign(is_violation=df["event_type"].isin(violations))


def try_expr(label, fn):
    """執行一個篩選運算式，回傳一行說明：得到幾個 True，或丟出哪種例外。"""
    try:
        return f"{label} → {int(fn().sum())} 列"
    except (TypeError, ValueError) as exc:
        return f"{label} → {type(exc).__name__}"


def chained_assignment(df, cond, how):
    """三種「把 cam-02 百分比改回小數」的寫法。回傳 (警告類別, 原表還有幾筆 > 1)。"""
    df = df.copy()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if how == "df[cond][col] = x":
            df[cond]["confidence"] = df[cond]["confidence"] / 100
        elif how == "df[col][cond] = x":
            df["confidence"][cond] = df["confidence"][cond] / 100
        elif how == "df.loc[cond, col] = x":
            df.loc[cond, "confidence"] = df.loc[cond, "confidence"] / 100
        else:
            raise ValueError(f"未知寫法：{how}")
    kinds = sorted({w.category.__name__ for w in caught}) or ["無"]
    return ",".join(kinds), int((df["confidence"] > 1).sum())


def subset(df, zone, start, end, event_type):
    """區域 × 時間（當地時間字串，含 start、不含 end）× 事件。每個條件各自加括號。"""
    t = df["event_time"]
    if not (t.str.endswith("+08:00")).all():
        raise ValueError("event_time 不全是 +08:00，不能用字串比較時間")
    return df[(df["zone"] == zone) & (t >= start) & (t < end) & (df["event_type"] == event_type)]


def top_k(counts, k, keep):
    """Top-K，名次相同時由 keep 決定：'first'／'last' 硬切成 k 個，'all' 把並列的都留下。"""
    if keep not in ("first", "last", "all"):
        raise ValueError(f"keep 只能是 first／last／all，收到 {keep!r}")
    return counts.nlargest(k, keep=keep)


if __name__ == "__main__":
    df = load_events()

    print("== 1. loc 看標籤，iloc 看位置 ==")
    viol = df[df["is_violation"]]
    print(f"全部 {len(df)} 列；違規 {len(viol)} 列，index 前五個：{viol.index[:5].tolist()}")
    print(f"viol.iloc[0] → {viol.iloc[0]['event_id']}（第 0 個位置）")
    print(f"viol.loc[2]  → {viol.loc[2, 'event_id']}（標籤是 2 的那列）")
    try:
        viol.loc[0]
    except KeyError as exc:
        print(f"viol.loc[0]  → KeyError: {exc}（標籤 0 是 ppe_ok，被篩掉了）")
    print(f"df.loc[0:2] {len(df.loc[0:2])} 列（含 2）；df.iloc[0:2] {len(df.iloc[0:2])} 列（不含 2）")
    print(f"df.loc[viol.index[:3], ['worker_id', 'event_type']]：")
    print(df.loc[viol.index[:3], ["worker_id", "event_type"]].to_string())

    print("\n== 2. & | ~ 一定要加括號 ==")
    hour = df["event_time"].str[11:13].astype(int)
    v = df["is_violation"]
    print(try_expr("v & (hour >= 14)", lambda: v & (hour >= 14)))
    print(try_expr("v & hour >= 14（沒括號）", lambda: v & hour >= 14))
    print(try_expr("v & (df.confidence > 0.9)", lambda: v & (df["confidence"] > 0.9)))
    c_fixed = df["confidence"].mask(df["confidence"] > 1, df["confidence"] / 100)  # 不改原表
    print(f"  其中 c > 1（cam-02 百分比 bug）{int((v & (df['confidence'] > 1)).sum())} 列；"
          f"百分比改回小數後再算是 {int((v & (c_fixed > 0.9)).sum())} 列")
    print(try_expr("v & df.confidence > 0.9（沒括號）", lambda: v & df["confidence"] > 0.9))
    print(try_expr('df.zone == "Z4" | df.zone == "Z3"', lambda: df["zone"] == "Z4" | df["zone"] == "Z3"))
    print(try_expr("hour >= 14 and hour < 16", lambda: hour >= 14 and hour < 16))
    print(try_expr('df.zone.isin(["Z3", "Z4"])', lambda: df["zone"].isin(["Z3", "Z4"])))

    print("\n== 3. NaN 在比較裡兩邊都是 False ==")
    c = df["confidence"]
    high, low = c > 0.6, c <= 0.6
    print(f"confidence 缺值 {int(c.isna().sum())}；> 0.6 有 {int(high.sum())}；<= 0.6 有 {int(low.sum())}；"
          f"相加 {int(high.sum() + low.sum())}，少於 {len(df)}")
    print(f"~(c > 0.6) 有 {int((~high).sum())}——「不是高」≠「低」，多出來的 {int((~high).sum() - low.sum())} 筆是缺值")
    print(f"c == float('nan') 有 {int((c == float('nan')).sum())} 筆；c.isna() 有 {int(c.isna().sum())} 筆")
    print(f"另外 c > 1 有 {int((c > 1).sum())} 筆（cam-02 百分比 bug），全部算進了「> 0.6」")

    print("\n== 4. Copy-on-Write：改值只用 df.loc[cond, col] = x ==")
    bug = df["confidence"] > 1
    for how in ("df[cond][col] = x", "df[col][cond] = x", "df.loc[cond, col] = x"):
        kind, left = chained_assignment(df, bug, how)
        print(f"{how}：警告 {kind}；原表仍 > 1 的有 {left} 筆")

    print("\n== 5. 區域 × 時間 × 事件 ==")
    s = subset(df, "Z4", "2026-09-22T14:00", "2026-09-22T16:00", "no_harness")
    print(f"施工架 09-22 14:00–16:00 未掛安全帶：{len(s)} 列，人員 {s['worker_id'].value_counts().to_dict()}")
    q = df.query('zone == "Z4" and event_type == "no_harness" '
                 'and "2026-09-22T14:00" <= event_time < "2026-09-22T16:00"')
    print(f"同一個條件用 query()：{len(q)} 列；與布林遮罩同一批列？{q.index.equals(s.index)}")
    s = subset(df, "Z3", "2026-09-10T00:00", "2026-09-11T00:00", "restricted_entry")
    print(f"開挖區 09-10 跨越警示線：{len(s)} 列，不同 event_id {s['event_id'].nunique()} 個")

    print("\n== 6. Top-K：三種寫法，以及名次相同 ==")
    counts = df[df["is_violation"]].groupby("worker_id").size()
    print(f"value_counts().head(3)：{df.loc[df['is_violation'], 'worker_id'].value_counts().head(3).to_dict()}")
    named = counts.drop("")
    print(f"排除空字串後 nlargest(3)：{named.nlargest(3).to_dict()}")
    by_count = named.sort_values(ascending=False, kind="stable")  # 並列時保留分組順序（worker_id 由小到大）
    print(f"sort_values(kind='stable').head(3)：{by_count.head(3).to_dict()}")
    print(f"第 5 名附近：{by_count.iloc[3:7].to_dict()}")
    print(f"sort_values(kind='stable').head(5) → {by_count.head(5).index.tolist()}")
    for keep in ("first", "last", "all"):
        print(f"nlargest(5, keep={keep!r}) → {list(top_k(named, 5, keep).index)}")
    table = named.rename("次數").reset_index()
    tie_break = table.sort_values(["次數", "worker_id"], ascending=[False, True]).head(5)
    print(f"多欄排序（次數↓、worker_id↑）head(5) → {tie_break['worker_id'].tolist()}")
    ranked = named.rank(method="min", ascending=False).astype(int)
    print(f"rank(method='min') ≤ 5：{ranked[ranked <= 5].sort_values().to_dict()}")
