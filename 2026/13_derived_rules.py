"""第 13 節：衍生欄位與可稽核規則——把每人每週違規次數分級成 risk_level。"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
EVENTS = DATA / "events"

RULE = {
    "version": "risk-v1",
    "decided": "2026-10-05",
    "unit": "每人每週（週一～週六，台灣時間）已辨識、依 event_id 去重後的違規次數",
    "levels": [("低", 0, 3), ("中", 3, 5), ("高", 5, None)],   # 下限含、上限不含
    "no_data": "無資料",
    "basis": "event-types.csv 的 is_violation；門檻為本課示範用，不是任何法規或公司規定",
}


def weekly_counts(events_path=EVENTS / "events.jsonl", types_path=EVENTS / "event-types.csv",
                  roster_path=EVENTS / "workers.csv"):
    """每人每週一列；以名冊 × 資料期間的週為骨架，沒被拍到的那一週留 NaN（不是 0）。"""
    ev = pd.read_json(events_path, lines=True, dtype=False, convert_dates=False).drop_duplicates("event_id")
    types = pd.read_csv(types_path, dtype=str, keep_default_na=False)
    roster = pd.read_csv(roster_path, dtype=str, keep_default_na=False)
    ev = ev[ev["worker_id"] != ""].copy()
    ev["is_violation"] = ev["event_type"].isin(types.loc[types["is_violation"] == "true", "event_type"])
    day = pd.to_datetime(ev["event_time"].str[:10], format="%Y-%m-%d")     # event_time 是工地當地時間
    ev["week"] = (day - pd.to_timedelta(day.dt.dayofweek, unit="D")).dt.strftime("%Y-%m-%d")
    grid = pd.MultiIndex.from_product([roster["worker_id"].drop_duplicates(), sorted(ev["week"].unique())],
                                      names=["worker_id", "week"])
    table = (ev.groupby(["worker_id", "week"])
             .agg(events=("event_id", "size"), violations=("is_violation", "sum"))
             .reindex(grid))
    table["events"] = table["events"].fillna(0).astype("int64")    # 沒被拍到＝0 筆偵測；違規次數則是「不知道」
    period = (ev["event_time"].min()[:10], ev["event_time"].max()[:10])
    return table.reset_index(), types, period


def risk_level(violations, rule=RULE):
    """依規則分級；NaN 一律標「無資料」，不能落進任何一級。"""
    x = pd.Series(violations, dtype="float64")
    if (x < 0).any():
        raise ValueError(f"違規次數不可為負：{x[x < 0].tolist()[:3]}")
    if (x.dropna() % 1 != 0).any():
        raise ValueError("違規次數必須是整數")
    conds, labels = [x.isna()], [rule["no_data"]]
    for label, low, high in rule["levels"]:
        conds.append((x >= low) & (x < high) if high is not None else (x >= low))
        labels.append(label)
    out = np.select(conds, labels, default="未分類")
    if (out == "未分類").any():
        raise ValueError(f"規則沒有涵蓋：{x[out == '未分類'].tolist()[:3]}")
    return pd.Series(out, index=x.index, name="risk_level")


def error_breakdown(x, got, expected):
    """拿「實際分錯的列」拆原因，不是拿「值剛好在邊界的列」去湊。"""
    wrong = pd.Series(got, index=x.index) != pd.Series(expected, index=x.index)
    parts = {"邊界 3 或 5 次": int((wrong & x.isin([3, 5])).sum()), "NaN": int((wrong & x.isna()).sum())}
    parts["其他"] = int(wrong.sum()) - sum(parts.values())
    return int(wrong.sum()), parts


def cut_counts(x, bins, right, labels=("低", "中", "高")):
    """pd.cut 的各級列數；「其中 0 次」是 NaN 且原值為 0 的列，實際算出來，不是猜。"""
    c = pd.cut(x, bins, right=right, labels=list(labels))
    counts = {lb: int((c == lb).sum()) for lb in labels}
    counts["NaN"] = int(c.isna().sum())
    counts["0 次"] = int((c.isna() & (x == 0)).sum())
    return counts


def describe_rule(rule, types, period):
    lines = [f"規則 {rule['version']}（{rule['decided']} 訂定）",
             f"計數單位：{rule['unit']}",
             f"資料期間：{period[0]} ～ {period[1]}"]
    for label, low, high in rule["levels"]:
        lines.append(f"  {label}：{low} 次以上" + (f"、未滿 {high} 次" if high is not None else ""))
    lines.append(f"  {rule['no_data']}：該週沒有被辨識到任何事件（不是 0 次）")
    lines.append("計入的違規類型與依據（營造安全衛生設施標準，練習站條文，不具法律效力）：")
    for r in types[types["is_violation"] == "true"].itertuples():
        lines.append(f"  {r.event_type}（{r.label_zh}）→ {r.pcode} 第 {r.slug} 條：{r.basis}")
    lines.append(f"門檻依據：{rule['basis']}")
    return "\n".join(lines)


if __name__ == "__main__":
    table, types, period = weekly_counts()
    x = table["violations"]
    print(f"每人每週 {len(table)} 列（{table['worker_id'].nunique()} 人 × {table['week'].nunique()} 週）；"
          f"violations 為 NaN 的 {int(x.isna().sum())} 列（那一週沒被拍到）\n")

    print("== 1. apply 逐列 if：邊界與 NaN ==")

    def naive(n):          # 需求：「3 次以上為中、5 次以上為高」
        if n > 5:
            return "高"
        elif n > 3:
            return "中"
        else:
            return "低"

    table["naive"] = x.apply(naive)
    table["risk_level"] = risk_level(x)
    probe = pd.DataFrame({"violations": [3.0, 5.0, np.nan]})
    probe["apply_if"] = probe["violations"].apply(naive)
    probe["np_select"] = risk_level(probe["violations"]).values
    print(probe.to_string(index=False))
    n_wrong, parts = error_breakdown(x, table["naive"], table["risk_level"])
    print(f"{len(table)} 列中分錯 {n_wrong} 列：邊界 3 或 5 次 {parts['邊界 3 或 5 次']} 列、NaN 變成「低」 {parts['NaN']} 列、"
          f"其他 {parts['其他']} 列；沒有任何錯誤訊息")

    print("\n== 2. pd.cut 的 right：同一組門檻，兩種邊界 ==")
    bins = [0, 3, 5, np.inf]
    probe = pd.DataFrame({"violations": [0, 2, 3, 4, 5, 24]})
    for right in (True, False):
        probe[f"right={right}"] = pd.cut(probe["violations"], bins, right=right,
                                         labels=["低", "中", "高"]).astype(object).fillna("NaN")
    print(probe.to_string(index=False))
    for right in (True, False):
        k = cut_counts(x, bins, right)
        print(f"right={right!s:5}：低 {k['低']}、中 {k['中']}、高 {k['高']}、NaN {k['NaN']}（其中 0 次的 {k['0 次']} 列）")
    same = pd.cut(x, bins, right=False, labels=["低", "中", "高"]).astype(object).fillna("無資料")
    print(f"right=False 與 np.select 結果相同：{bool((same == table['risk_level']).all())}")

    print("\n== 3. qcut：門檻跟著資料跑 ==")
    q = [0, 0.5, 0.9, 1]
    rows, by_qcut = [], []
    for week, grp in table.dropna(subset=["violations"]).groupby("week"):
        cats, edges = pd.qcut(grp["violations"], q, labels=["低", "中", "高"], retbins=True)
        by_qcut.append(cats.astype(str))
        lookup = dict(zip(grp["violations"], cats.astype(str)))
        rows.append({"week": week, "門檻": [round(float(e), 1) for e in edges],
                     "2 次": lookup.get(2.0, "-"), "4 次": lookup.get(4.0, "-"), "高的人數": int((cats == "高").sum())})
    print(pd.DataFrame(rows).to_string(index=False))
    by_qcut = pd.concat(by_qcut)
    differ = by_qcut != table.loc[by_qcut.index, "risk_level"]
    print(f"每週各自 qcut 與固定規則 risk-v1 相比：{len(by_qcut)} 列中 {int(differ.sum())} 列等級不同")

    print("\n== 4. 規則說明：版本、門檻、資料期間、出處 ==")
    print(describe_rule(RULE, types, period))

    print("\n== 5. 交出去的表 ==")
    table["rule_version"] = RULE["version"]
    out = table[["worker_id", "week", "events", "violations", "risk_level", "rule_version"]]
    print(out["risk_level"].value_counts().reindex(["低", "中", "高", "無資料"]).to_string())
    print(out[out["worker_id"] == "W041"].to_string(index=False))
