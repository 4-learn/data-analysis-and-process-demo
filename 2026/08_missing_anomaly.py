"""第 08 節：缺值與異常——判斷「能不能信」，而且每一個清理動作都留下紀錄。"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
EVENTS = DATA / "events" / "events.jsonl"


def load_events(path=EVENTS):
    return pd.read_json(path, lines=True, dtype=False, convert_dates=False)


def is_violation(df):
    return df["event_type"] != "ppe_ok"


def missing_meaning(df):
    """同樣是「空」，意義不同：要拆開來數，不是一句 isna().sum()。"""
    v = is_violation(df)
    rows = [
        ("handled_at", "違規、沒有處理", int((v & (df["handled_at"] == "")).sum()), "沒發生（還沒處理）"),
        ("handled_at", "ppe_ok", int((~v & (df["handled_at"] == "")).sum()), "不適用"),
        ("confidence", "null", int(df["confidence"].isna().sum()), "沒記錄（" + "、".join(
            sorted(df.loc[df["confidence"].isna(), "camera_id"].unique())) + "）"),
        ("worker_id", "空字串", int((df["worker_id"] == "").sum()), "辨識不到臉；事件仍發生"),
    ]
    return pd.DataFrame(rows, columns=["欄位", "情況", "列數", "意義"])


def percent_bug(df):
    """confidence 應在 0–1；大於 1 的是韌體把百分比寫進來（第四段）。"""
    return df["confidence"] > 1


# 已確認的 bug 範圍：只有這支攝影機、只有這幾天（第四段）。超出範圍就不是同一個 bug。
PERCENT_BUG_CAMERA = "cam-02"
PERCENT_BUG_DAYS = ("2026-09-15", "2026-09-17")


def zscore_outliers(counts, threshold=3.0):
    """常見的「清異常」規則：|z| > threshold 視為離群值。"""
    z = (counts - counts.mean()) / counts.std()
    return z.abs() > threshold


def iqr_outliers(counts, k=1.5):
    q1, q3 = counts.quantile([0.25, 0.75])
    return (counts < q1 - k * (q3 - q1)) | (counts > q3 + k * (q3 - q1))


def clean(raw):
    """只做有理由的動作；每一步記下進幾列、出幾列、動了幾列、理由。被丟的列另外回傳。"""
    if raw["event_id"].isna().any() or (raw["event_id"] == "").any():
        raise ValueError("event_id 有空值：無法判斷重複，停止清理")
    log, dropped = [], []
    df = raw.copy()

    dup = df.duplicated("event_id", keep="first")    # 檔案順序＝到達順序：留第一次到的（見第 09 節）
    dropped.append(df[dup].assign(理由="event_id 重複（補傳重送）"))
    log.append(("依 event_id 去重", len(df), len(df) - int(dup.sum()), int(dup.sum()), 0, "補傳送了兩次；保留先到的一列"))
    df = df[~dup].copy()

    bug = percent_bug(df)
    if bug.any() and set(df.loc[bug, "camera_id"]) != {PERCENT_BUG_CAMERA}:
        raise ValueError(f"confidence > 1 出現在 cam-02 以外：{sorted(set(df.loc[bug, 'camera_id']))}，先問廠商")
    days = df.loc[bug, "event_time"].str[:10]
    outside = sorted(set(days[(days < PERCENT_BUG_DAYS[0]) | (days > PERCENT_BUG_DAYS[1])]))
    if outside:
        raise ValueError(f"confidence > 1 出現在 {PERCENT_BUG_DAYS[0]}～{PERCENT_BUG_DAYS[1]} 以外：{outside}，先問廠商")
    span = f"{days.min()[5:]}～{days.max()[5:]}" if bug.any() else "無"
    df["confidence_raw"] = df["confidence"]           # 原值留著，修過的列看得出來
    df.loc[bug, "confidence"] = df.loc[bug, "confidence"] / 100
    log.append(("cam-02 百分比 ÷100", len(df), len(df), 0, int(bug.sum()), f"韌體 bug（{span}）；原值存 confidence_raw"))

    for what, why in [("confidence 缺值", "cam-08 沒記錄：保留 NaN，不補 0"),
                      ("worker_id 空字串", "事件仍發生：保留；人員分析時再排除"),
                      ("handled_at 空字串", "沒處理／不適用：保留，分母要分開算")]:
        log.append((what, len(df), len(df), 0, 0, why))

    log = pd.DataFrame(log, columns=["步驟", "進", "出", "丟棄", "修改", "理由"])
    return df.reset_index(drop=True), log, pd.concat(dropped, ignore_index=True)


if __name__ == "__main__":
    raw = load_events()
    events = raw.drop_duplicates("event_id")          # 第 1–5 段先用去重後的 2818 列；正式流程在第 6 段
    v = is_violation(events)

    print("== 1. 三種缺值，三種意義 ==")
    na = events.isna().sum()
    print(f"isna().sum() 只看到 confidence {int(na['confidence'])} 個缺值；空字串不算 NaN，"
          f"所以 handled_at {int(na['handled_at'])} 個、worker_id {int(na['worker_id'])} 個")
    print(missing_meaning(events).to_string(index=False))
    handled = events["handled_at"] != ""
    print(f"處理率：分母用全部 {len(events)} 列 → {handled.mean():.1%}；"
          f"分母用違規 {int(v.sum())} 列 → {handled[v].mean():.1%}")

    print("\n== 2. 補 0：信心度平均被拉低 ==")
    by_zone = pd.DataFrame({
        "缺值": events["confidence"].isna().groupby(events["zone"]).sum(),
        "不補（skipna）": events.groupby("zone")["confidence"].mean(),
        "補 0": events["confidence"].fillna(0).groupby(events["zone"]).mean(),
    }).round(3)
    print(by_zone.to_string())
    over = by_zone[by_zone["不補（skipna）"] > 1]
    for zone, row in over.iterrows():
        print(f"{zone} 平均 {row['不補（skipna）']:.3f}：信心度不可能大於 1——先記下，第 4 段處理")

    print("\n== 3. dropna 刪掉的是事件，不是壞資料 ==")
    naive = events.replace("", np.nan).dropna()
    print(f"把空字串當缺值後 dropna()：{len(events)} 列 → {len(naive)} 列；"
          f"ppe_ok {int((~v).sum())} → {int((~is_violation(naive)).sum())} 列；"
          f"cam-08 {int((events['camera_id'] == 'cam-08').sum())} → {int((naive['camera_id'] == 'cam-08').sum())} 列")
    known = events[events["worker_id"] != ""]
    print(f"只刪 worker_id 空的列：違規 {int(v.sum())} → {int(is_violation(known).sum())}，"
          f"少了 {int(v.sum() - is_violation(known).sum())} 筆（{1 - is_violation(known).sum() / v.sum():.1%}）")
    lost = pd.DataFrame({"全部": events[v].groupby("event_type").size(),
                         "刪掉未辨識後": known[is_violation(known)].groupby("event_type").size()})
    lost["少掉"] = lost["全部"] - lost["刪掉未辨識後"]
    print(lost.to_string())

    print("\n== 4. 異常＝bug：cam-02 的百分比 ==")
    bug = percent_bug(events)
    days = events.loc[bug, "event_time"].str[:10]
    print(f"confidence > 1：{int(bug.sum())} 列；攝影機 {sorted(events.loc[bug, 'camera_id'].unique())}；"
          f"日期 {days.min()}～{days.max()}；範圍 {events.loc[bug, 'confidence'].min():g}～{events.loc[bug, 'confidence'].max():g}")
    fixed = events.copy()
    fixed.loc[bug, "confidence"] = fixed.loc[bug, "confidence"] / 100
    print(f"÷100 後 Z1 平均 {events.loc[events['zone'] == 'Z1', 'confidence'].mean():.3f} → "
          f"{fixed.loc[fixed['zone'] == 'Z1', 'confidence'].mean():.3f}")
    c = fixed["confidence"]
    print(f"低信心 (c < 0.6)：{int((c < 0.6).sum())} 列；不是高信心 ~(c >= 0.6)：{int((~(c >= 0.6)).sum())} 列；"
          f"差 {int((~(c >= 0.6)).sum() - (c < 0.6).sum())} 列＝NaN（比較一律 False）")

    print("\n== 5. 異常＝真的出事：W041 ==")
    per_day = (events[v & (events["worker_id"] != "")]
               .groupby([events["worker_id"], events["event_time"].str[:10].rename("day")]).size())
    print(f"每人每日違規次數：{len(per_day)} 格，中位數 {per_day.median():g}，最大 {per_day.max()}（{per_day.idxmax()}）")
    cell = pd.MultiIndex.from_arrays([events["worker_id"], events["event_time"].str[:10]])
    d22 = (events["event_type"] == "no_harness") & events["event_time"].str.startswith("2026-09-22")
    print(f"09-22 全工地 no_harness {int(d22.sum())} 筆，其中 W041 {int((d22 & (events['worker_id'] == 'W041')).sum())} 筆")
    for name, flag in [("z-score > 3", zscore_outliers(per_day)), ("IQR 1.5 倍", iqr_outliers(per_day))]:
        removed = v & (events["worker_id"] != "") & cell.isin(per_day.index[flag])   # 真的照規則判定結果去濾
        kept = events[~removed]
        print(f"{name:12} 清掉 {int(flag.sum()):>2} 格、{int(removed.sum()):>3} 筆事件；"
              f"W041 09-22 被清掉：{bool(flag.get(('W041', '2026-09-22')))}；"
              f"清完 09-22 no_harness 剩 {int(d22[~removed].sum())} 筆（W041 {int((d22[~removed] & (kept['worker_id'] == 'W041')).sum())} 筆）")

    print("\n== 6. 清理紀錄（audit trail）==")
    cleaned, log, dropped = clean(raw)
    print(log.to_string(index=False))
    print(f"進 {len(raw)} 列，出 {len(cleaned)} 列；丟棄 {len(dropped)} 列：")
    print(dropped["理由"].value_counts().to_string())
    print(dropped[["event_id", "event_type", "ingested_at"]].head(3).to_string(index=False))
