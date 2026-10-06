"""第 14 節：跨來源合併——先預測列數，合併後驗證列數。"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
EVENTS = DATA / "events"
VIOLATIONS = {"no_helmet", "no_harness", "restricted_entry"}


def read_events():
    ev = pd.read_json(EVENTS / "events.jsonl", lines=True, dtype=False, convert_dates=False)
    return ev.drop_duplicates("event_id").reset_index(drop=True)


def read_csv(name):
    return pd.read_csv(EVENTS / name, dtype=str, keep_default_na=False)


def attach_roster(events, roster):
    """事件接名冊：以事件「當地日期」落在 valid_from..valid_to（空＝至今）的那一列為準。

    left join：認不出人的事件保留；合併後列數必須等於事件數，否則就是 fan-out。
    """
    if roster["valid_from"].eq("").any():
        raise ValueError("名冊有空的 valid_from")
    day = events["event_time"].str[:10]                       # event_time 是 +08:00 當地時間
    m = events.assign(_day=day).merge(roster, on="worker_id", how="left", indicator=True)
    in_range = (m["_day"] >= m["valid_from"]) & ((m["valid_to"] == "") | (m["_day"] <= m["valid_to"]))
    keep = (m["_merge"] == "left_only") | in_range
    out = m[keep].drop(columns="_day")
    if out["event_id"].duplicated().any():
        dup = out.loc[out["event_id"].duplicated(), "worker_id"].unique().tolist()
        raise ValueError(f"名冊有效期間重疊：{dup[:5]}")
    unmatched = set(out.loc[(out["_merge"] == "left_only") & (out["worker_id"] != ""), "event_id"])
    lost = sorted(set(events.loc[events["worker_id"] != "", "event_id"]) - set(out["event_id"]) | unmatched)
    if lost:
        raise ValueError(f"{len(lost)} 筆已辨識事件對不到名冊（不在名冊或不在有效期間內），例如 {lost[0]}")
    if len(out) != len(events):
        raise ValueError(f"合併前 {len(events)} 列，合併後 {len(out)} 列")
    return out.reset_index(drop=True)


def attach_articles(events, types, articles):
    """事件 → 事件類型 → 法條原文。鍵是 (pcode, slug)，不是只有 slug。"""
    cols = ["pcode", "slug", "law_name", "article_no", "content", "source_url"]
    m = (events.merge(types, on="event_type", how="left", validate="many_to_one", indicator="_type")
         .merge(articles[cols], on=["pcode", "slug"], how="left", validate="many_to_one"))
    unknown = m.loc[m["_type"] == "left_only", "event_type"].unique().tolist()
    if unknown:
        raise ValueError(f"事件類型不在對照表：{unknown}")
    no_text = m[(m["is_violation"] == "true") & m["content"].isna()]
    if len(no_text):
        raise ValueError(f"違規事件找不到法條：{no_text[['event_type', 'pcode', 'slug']].drop_duplicates().values.tolist()}")
    if len(m) != len(events):
        raise ValueError(f"合併前 {len(events)} 列，合併後 {len(m)} 列")
    return m.drop(columns="_type")


def predict_rows(left, right, on, how):
    """不執行 merge，只看兩邊鍵的出現次數，算出 merge 會產生幾列。"""
    lk = left[on].value_counts()
    rk = right[on].value_counts()
    both = lk.index.intersection(rk.index)
    n = int((lk[both] * rk[both]).sum())                      # 兩邊都有的鍵：左 × 右
    if how in ("left", "outer"):
        n += int(lk.drop(both).sum())                         # 只有左邊有：各留一列
    if how in ("right", "outer"):
        n += int(rk.drop(both).sum())
    return n


def checked_merge(log, step, left, right, reason, **kw):
    """先預測、再執行、再核對；預測不準就停下來，並把結果記進合併前後列數表。"""
    guess = predict_rows(left, right, kw["on"], kw.get("how", "inner"))
    out = left.merge(right, **kw)
    if len(out) != guess:
        raise ValueError(f"{step}：預測 {guess} 列，實際 {len(out)} 列")
    log.append((step, len(left), guess, len(out), reason))
    return out


def dashboard_as_events(dash, types):
    """把儀表板匯出轉成事件表的欄名與單位，才能跟 events 對齊。"""
    zones = {v["name"]: k for k, v in json.loads((EVENTS / "MANIFEST.json").read_text(encoding="utf-8"))["zones"].items()}
    return pd.DataFrame({
        "event_id": dash["事件編號"],
        "zone": dash["區域"].map(zones),
        "camera_id": dash["攝影機"],
        "worker_id": dash["人員"].replace("未辨識", ""),
        "event_type": dash["事件"].map(dict(zip(types["label_zh"], types["event_type"]))),
        "confidence": pd.to_numeric(dash["信心度"].str.rstrip("%").replace("N/A", np.nan)) / 100,
        "event_time": pd.to_datetime(dash["發生時間"], format="%Y/%m/%d %H:%M").dt.strftime("%Y-%m-%dT%H:%M"),
    })


if __name__ == "__main__":
    ev = read_events()
    roster = read_csv("workers.csv")
    types = read_csv("event-types.csv")
    articles = pd.read_json(DATA / "articles.jsonl", lines=True, dtype=False, convert_dates=False)
    ev["violation"] = ev["event_type"].isin(VIOLATIONS)   # 布林；event-types.csv 的 is_violation 是字串
    known = ev["worker_id"] != ""
    log = []

    print("== 1. 先預測，再執行 ==")
    rows_per = roster["worker_id"].value_counts()
    multi = rows_per[rows_per > 1]
    fan = {w: int((ev["worker_id"] == w).sum()) for w in multi.index}
    no_event = len(set(roster["worker_id"]) - set(ev["worker_id"]))
    print(f"事件 {len(ev)} 列（已辨識 {int(known.sum())}、未辨識 {int((~known).sum())}）；名冊 {len(roster)} 列、"
          f"不同 worker_id {roster['worker_id'].nunique()}；名冊不只一列的人 "
          + "、".join(f"{w}（{multi[w]} 列、事件 {fan[w]} 筆）" for w in multi.index)
          + f"；名冊上沒有事件的 {no_event} 人")
    for how in ("inner", "left", "outer"):
        guess = predict_rows(ev, roster, "worker_id", how)
        got = len(ev.merge(roster, on="worker_id", how=how))
        print(f"how={how:5}  預測 {guess}  實際 {got}  與事件數相差 {got - len(ev):+d}")
    extra = sum(fan[w] * (multi[w] - 1) for w in multi.index)
    naive = checked_merge(log, "events × workers.csv（只用 worker_id, left）", ev, roster,
                          "、".join(f"{w} 名冊 {multi[w]} 列" for w in multi.index) + f"：{extra} 筆事件被複製",
                          on="worker_id", how="left")

    print("\n== 2. validate 讓 fan-out 變成錯誤 ==")
    try:
        ev.merge(roster, on="worker_id", how="left", validate="many_to_one")
    except pd.errors.MergeError as exc:
        print("MergeError:", str(exc).splitlines()[0])

    print("\n== 3. 依有效期間合併 ==")
    staff = attach_roster(ev, roster)
    log.append(("events × workers.csv（依有效期間）", len(ev), len(ev), len(staff), "attach_roster() 內部核對：每筆事件只對到一段名冊"))
    w23 = staff[staff["worker_id"] == "W023"].groupby("contractor", sort=False).agg(
        事件=("event_id", "size"), 違規=("violation", "sum"), 最早=("event_time", "min"), 最晚=("event_time", "max"))
    w23[["最早", "最晚"]] = w23[["最早", "最晚"]].apply(lambda s: s.str[:10])
    print(w23.to_string())
    by = pd.DataFrame({
        "天真合併": naive[naive["violation"]].groupby("contractor").size(),
        "依有效期間": staff[staff["violation"]].groupby("contractor").size(),
    })
    print(by.to_string())
    print(f"違規合計：天真合併 {int(by['天真合併'].sum())}、依有效期間 {int(by['依有效期間'].sum())}"
          f"（已辨識違規 {int(ev.loc[known, 'violation'].sum())}）")

    print("\n== 4. how 與 indicator：誰不見了 ==")
    audit = ev.merge(roster.drop_duplicates("worker_id"), on="worker_id", how="outer", indicator=True)
    print(audit["_merge"].value_counts().to_string())
    left_only = audit[audit["_merge"] == "left_only"]
    right_only = audit[audit["_merge"] == "right_only"]
    print(f"left_only 的 worker_id：{left_only['worker_id'].unique().tolist()}；right_only：{right_only['worker_id'].min()}…{right_only['worker_id'].max()}")
    old = roster[roster["worker_id"] != "W041"]          # 假設：拿到一份漏了 W041 的舊名冊
    inner = ev.merge(old.drop_duplicates("worker_id"), on="worker_id", how="inner")
    gone = ev[~ev["event_id"].isin(inner["event_id"])]
    print(f"名冊漏了 W041 時 how=inner：{len(ev)} → {len(inner)} 列；消失 {len(gone)} 筆，"
          f"其中未辨識 {int((gone['worker_id'] == '').sum())}、W041 {int((gone['worker_id'] == 'W041').sum())}（違規 {int(gone.loc[gone['worker_id'] == 'W041', 'violation'].sum())}）")
    try:
        attach_roster(ev, old)
    except ValueError as exc:
        print("attach_roster:", exc)
    checked_merge(log, "events × workers.csv（名冊去重, inner）", ev, roster.drop_duplicates("worker_id"),
                  f"未辨識 {int((~known).sum())} 筆沒有 worker_id 可對", on="worker_id", how="inner")

    print("\n== 5. 三方合併：事件 → 類型 → 法條原文 ==")
    typed = ev.merge(types, on="event_type", validate="many_to_one")
    per_slug = articles["slug"].value_counts()
    fan_out = {s: int(per_slug.get(s, 0)) for s in types.loc[types["is_violation"] == "true", "slug"]}
    dropped = typed.loc[~typed["slug"].isin(per_slug.index), "event_type"].value_counts()
    slug_only = checked_merge(log, "× event-types × articles（只用 slug）", typed, articles,
                              "違規 fan-out（" + "、".join(f"{s} 對 {k} 部" for s, k in fan_out.items() if k > 1) + "）＋"
                              + "、".join(f"{e} {n} 筆" for e, n in dropped.items()) + "被 inner 丟掉", on="slug")
    print(f"只用 slug 接 articles：{len(ev)} → {len(slug_only)} 列；" + "、".join(f"'{s}' 對到 {k} 部" for s, k in fan_out.items()))
    full = attach_articles(ev, types, articles)
    log.append(("× event-types × articles（pcode＋slug, left）", len(ev), len(ev), len(full), "attach_articles() 內部核對：無差異"))
    per_type = (full[full["violation"]]
                .groupby(["event_type", "law_name", "article_no"], sort=False)
                .agg(事件數=("event_id", "size"), 條文=("content", "first")))
    per_type["條文"] = per_type["條文"].str.replace("\n", " ").str[:28] + "…"
    print(per_type.to_string())
    print(f"ppe_ok {int((full['event_type'] == 'ppe_ok').sum())} 筆沒有對應法條（不是違規，content 為 NaN）")

    print("\n== 6. concat：欄名不同就不會對齊 ==")
    dash = pd.read_csv(EVENTS / "dashboard-export.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    week1 = ev[ev["event_time"] < "2026-09-07"].drop(columns="violation")
    stacked = pd.concat([week1, dash], ignore_index=True)
    print(f"events 第 1 週 {week1.shape} ＋ 儀表板 {dash.shape} → {stacked.shape}")
    half = stacked.isna().sum()
    print(f"{int((half == len(week1)).sum())} 欄恰好有 {len(week1)} 個 NaN；例如 event_id 缺 {half['event_id']}、事件編號 缺 {half['事件編號']}")
    shared = set(week1.columns) & set(dash.columns)
    log.append(("concat events 第 1 週 ＋ 儀表板（原欄名）", len(week1), len(week1) + len(dash), len(stacked),
                f"欄名相同的 {len(shared)} 欄：{week1.shape[1]}＋{dash.shape[1]}＝{stacked.shape[1]} 欄，每列有一邊全是 NaN"))
    aligned = dashboard_as_events(dash, types)
    again = pd.concat([week1[aligned.columns], aligned], ignore_index=True)
    print(f"轉成相同欄名後 concat：{again.shape}；event_id 重複 {int(again['event_id'].duplicated().sum())} 筆——同一週、同一批事件")
    check = week1.merge(aligned, on="event_id", how="outer", validate="one_to_one", indicator=True, suffixes=("", "_dash"))
    both = check[check["_merge"] == "both"]
    diff = {c: int((both[c] != both[c + "_dash"]).sum()) for c in ["zone", "camera_id", "worker_id", "event_type"]}
    diff["event_time"] = int((both["event_time"].str[:16] != both["event_time_dash"]).sum())
    diff["confidence"] = int(((both["confidence"] - both["confidence_dash"]).abs() > 0.005).sum())
    print(f"改用 merge 對帳：{check['_merge'].value_counts().to_dict()}；欄位不一致 {diff}")

    print("\n== 7. 合併前後列數 ==")
    report = pd.DataFrame(log, columns=["步驟", "合併前", "預測", "合併後", "原因"])
    report.insert(4, "差異", report["合併後"] - report["合併前"])
    print(report.to_string(index=False))
    print(f"預測與實際全部一致：{bool((report['預測'] == report['合併後']).all())}")
