# 08｜缺值與異常：判斷「能不能信」

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 08 節：缺值與異常：判斷「能不能信」，而不是「格式對不對」。**
> 本節拿工地 AI 攝影機的 2,838 筆事件，示範同樣是「空」的三種欄位各代表什麼、補 0 與 `dropna` 怎麼改變結論、哪一種異常是 bug 可以修、哪一種異常就是答案不能清。每一個清理動作都要留下紀錄：進幾列、出幾列、丟的是哪些、為什麼。
> 本節不是 `isna`／`fillna`／`dropna` 的 API 介紹，也不重教型態、重複與字串正規化（MariaDB 第 16 節已教，本節只留一張對照表）；驗證失敗要讓流程停下、重跑要一樣，是第 09 節的事。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：說出一個欄位的「空」是**沒發生**、**沒記錄**還是**不適用**；算出補 0 與 `dropna` 各讓數字偏多少；分辨「異常＝bug」與「異常＝真的出事」；交出一份清理紀錄，讓別人不看程式也知道少掉的列是哪些、為什麼。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–8 分鐘 | 三種缺值，三種意義 | `isna().sum()` 只看到 1 種；處理率 8.3% 還是 47.2% |
| 8–15 分鐘 | 補 0 與 `dropna` | Z4 信心度 0.762 → 0.399；2,818 列剩 174 列 |
| 15–22 分鐘 | 異常＝bug | cam-02 百分比：可以修，但原值要留 |
| 22–30 分鐘 | 異常＝真的出事 | z-score／IQR 都會把 W041 清掉 |
| 30–35 分鐘 | 清理紀錄與複習對照 | `clean()` 回傳結果＋紀錄＋丟棄清單 |
| 35–50 分鐘 | Workshop：補 0 vs `dropna`，交出被丟的列 | 清理前後列數＋丟棄清單與理由 |

先修：本課第 03（讀 JSONL 不讓 pandas 猜）、06（探索）、07（布林篩選、缺值在比較中的行為）節；MariaDB 第 16 節（空字串 vs NULL、型別、重複 ID）。環境同第 02 節。

## 一、三種缺值，三種意義

本節的資料是 `data/events/events.jsonl`：示範工地 4 個區域、8 支攝影機，2026-08-31～09-26（週日停工）的 AI 偵測事件。**全部是合成資料**，不代表任何真實工地。讀法照第 03 節：`dtype=False, convert_dates=False`，不讓 pandas 猜。

`events.jsonl` 有 2,838 列，但只有 2,818 個不同的 `event_id`——有一批補傳送了兩次（第 09、10 節會細談）。第一到五段先用去重後的 2,818 列，第六段再把去重寫進正式的清理流程。

先照「五分鐘探索法」問：缺值有多少？

```text
== 1. 三種缺值，三種意義 ==
isna().sum() 只看到 confidence 231 個缺值；空字串不算 NaN，所以 handled_at 0 個、worker_id 0 個
        欄位      情況   列數          意義
handled_at 違規、沒有處理  262   沒發生（還沒處理）
handled_at  ppe_ok 2322         不適用
confidence    null  231 沒記錄（cam-08）
 worker_id     空字串  364 辨識不到臉；事件仍發生
處理率：分母用全部 2818 列 → 8.3%；分母用違規 496 列 → 47.2%
```

`isna().sum()` 說「只有 `confidence` 有缺值」。實際上這份資料有三個欄位會「空」、合起來是**四種**意義，全都不同：

| 欄位 | 空的時候代表 | 能不能補？ |
| --- | --- | --- |
| `handled_at`（違規事件） | 主管**還沒處理**——缺值本身就是資訊 | 不能。補任何時間都是捏造「處理過了」 |
| `handled_at`（`ppe_ok`） | 戴好防護具，本來就**不需要處理** | 不能。它不是缺，是不適用 |
| `confidence` | cam-08 跑舊模型 `ppe-v2`，**沒有記錄**信心度 | 不能補 0；事件是真的，只是少一個欄位 |
| `worker_id` | **辨識不到臉**；違規照樣發生了 | 不能刪；做人員分析時排除，做工地統計時保留 |

最後一行是這一段的重點：「處理率」是多少？分母用全部 2,818 列是 8.3%，分母只算需要處理的違規 496 列是 47.2%。**同一欄、同一批空值，分母選錯就差五倍多**。這不是格式問題，是你有沒有先問「這個空是什麼意思」。

> 讀法用了 `dtype=False, convert_dates=False`，所以 `handled_at` 的空是空字串 `""`，不是 `NaN`。若用一行預設的 `read_json`，`handled_at` 會被自動轉成日期，空字串變 `NaT`——那時 `isna()` 就會數到它（教師實測 2,838 列中 2,602 列）。**同一份檔案，換一個讀法，「有幾個缺值」的答案就不同**；MariaDB 第 16 節「空字串 vs NULL」在 pandas 這一層一樣成立。

## 二、補 0：平均被拉低

AI 最常給的處理：

```python
df["confidence"] = df["confidence"].fillna(0)
```

依區域看信心度平均：

```text
== 2. 補 0：信心度平均被拉低 ==
       缺值  不補（skipna）    補 0
zone                        
Z1      0       6.148  6.148
Z2      0       0.773  0.773
Z3      0       0.774  0.774
Z4    231       0.762  0.399
Z1 平均 6.148：信心度不可能大於 1——先記下，第 4 段處理
```

- **補 0 讓 Z4 的平均從 0.762 掉到 0.399**。cam-08 在 Z4，它的 231 筆不是「信心度 0」，是「沒有這個數字」。補 0 之後，報告會寫「施工架的模型最不可靠」——事實是「施工架有一支攝影機沒回報」。
- pandas 的 `mean()` 預設 `skipna=True`，**不補就是跳過**，算的是「有記錄的那些」的平均。這是對的，但要在報告上寫明分母是 254 筆不是 485 筆。
- **Z1 的 6.148** 不是補值造成的——信心度不可能大於 1。輸出最後一行是程式自己挑出「平均 > 1 的區域」印出來的，不是手寫的；先記下來，第四段處理。

## 三、`dropna` 刪掉的是事件，不是壞資料

AI 另一個常見的寫法：「把空的都當缺值，然後 `dropna()`」。

```text
== 3. dropna 刪掉的是事件，不是壞資料 ==
把空字串當缺值後 dropna()：2818 列 → 174 列；ppe_ok 2322 → 0 列；cam-08 231 → 0 列
只刪 worker_id 空的列：違規 496 → 419，少了 77 筆（15.5%）
                   全部  刪掉未辨識後  少掉
event_type                       
no_harness        170     139  31
no_helmet         252     215  37
restricted_entry   74      65   9
```

- 2,818 列剩 174 列，而且**剩下的全是「違規且已處理」**——`ppe_ok` 的 `handled_at` 一定是空的，2,322 列全部被刪（2,322 → 0）；cam-08 沒有 `confidence`，231 列一筆不剩（231 → 0）。這張表已經不是「工地發生了什麼」，而是「主管處理過、而且不是 cam-08 拍到的違規」。**它不會報錯，列數也不是 0**，看起來像「清乾淨了」。
- 就算只刪 `worker_id` 空的列，違規也少了 77 筆（15.5%），其中「高處未使用安全帶」少 31 筆。辨識不到臉的人一樣站在施工架上。「每個工人違規幾次」可以排除他們；「這個區域違規幾次」不可以。
- **`dropna` 的語意是「這筆事件不存在」**。舊教材說「丟掉不能用的資料」——要先問：不能用在哪個問題上？

## 四、異常＝bug：cam-02 的百分比

第二段 Z1 的平均是 6.148。找出 `confidence > 1` 的列：

```text
== 4. 異常＝bug：cam-02 的百分比 ==
confidence > 1：69 列；攝影機 ['cam-02']；日期 2026-09-15～2026-09-17；範圍 43～99
÷100 後 Z1 平均 6.148 → 0.777
低信心 (c < 0.6)：178 列；不是高信心 ~(c >= 0.6)：409 列；差 231 列＝NaN（比較一律 False）
```

全部集中在**一支攝影機、連續三天**，數值 43～99，看起來是百分比（`87.0` 其實是 `0.87`）——韌體 bug，不是真的有大於 1 的信心度。這種異常**可以修**：除以 100。但有三個條件：

1. **先確認範圍**：只有 cam-02、只有這三天。如果 cam-05 也冒出 `> 1` 的值，或 cam-02 在 09-15～17 以外也冒出來，就不是同一個 bug（至少不是已確認的那一段），要停下來問廠商。第六段的 `clean()` 把範圍寫成常數 `PERCENT_BUG_CAMERA`、`PERCENT_BUG_DAYS`，攝影機或日期超出都會拋 `ValueError`；紀錄裡的日期也是從實際被修改的列算出來的，不是手寫字串。
2. **原值要留**：`clean()` 把原值存在 `confidence_raw`，修過的列看得出來。
3. **寫進紀錄**：「修改 69 列，理由：韌體 bug」。不寫，下一個人看到 cam-02 的分布會以為一切正常。

最後一行是第 07 節講過的 NaN 比較：`c < 0.6` 是 178 列，「不是 `c >= 0.6`」卻是 409 列，差的 231 列正是 cam-08 的 NaN——NaN 跟任何數比較都是 `False`，所以它既不「低」也不「高」。用 `~` 反轉條件，就把「沒記錄」算進「低信心」了。

## 五、異常＝真的出事：W041

常見的「清理異常值」規則是 z-score > 3 或 IQR 1.5 倍。拿它套在「每人每日違規次數」上：

```text
== 5. 異常＝真的出事：W041 ==
每人每日違規次數：322 格，中位數 1，最大 18（('W041', '2026-09-22')）
09-22 全工地 no_harness 24 筆，其中 W041 18 筆
z-score > 3  清掉  1 格、 18 筆事件；W041 09-22 被清掉：True；清完 09-22 no_harness 剩 6 筆（W041 0 筆）
IQR 1.5 倍    清掉 68 格、165 筆事件；W041 09-22 被清掉：True；清完 09-22 no_harness 剩 2 筆（W041 0 筆）
```

- W041 在 2026-09-22 下午，被 cam-07 在施工架連續偵測 18 次「高處未使用安全帶」。**這就是這套系統存在的理由**。
- z-score 只清掉一格——剛好就是它。
- IQR 更糟：中位數和四分位數都是 1，IQR 是 0，**任何一天違規 2 次以上都算異常**，68 格、165 筆違規全被清掉。
- 程式真的拿兩條規則的判定結果去濾事件（被判為異常的「人 × 日」格子裡的違規全部移除），再數 09-22 的 no_harness：z-score 清完從 24 筆剩 **6 筆**，「看起來是平常的一天」；IQR 清完只剩 **2 筆**——連其他人那天違規 2 次以上的紀錄也一起被清掉了。兩種規則下 W041 都是 0 筆。

**判斷方式**：異常若能用「資料怎麼產生」解釋（某支攝影機、某段時間、某種格式），多半是 bug；若異常指向「某個人、某個地方、某個行為」，而且資料本身前後一致（同一支攝影機 cam-07、約每 3 分鐘一筆、信心度 0.82–0.95），它多半是真的。統計規則分不出這兩種，**要你來分**。工地違規本來就是異常，清掉異常等於清掉答案。

## 六、清理紀錄：進幾列、出幾列、丟了誰

把以上判斷寫成一個 `clean()`：只做有理由的動作，每一步記下來，被丟的列另外交出去。

以下為完整 `08_missing_anomaly.py`，只讀 `data/`，不寫檔、不連線。

<!-- demo: 08_missing_anomaly.py -->
```python
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
```

執行（在本目錄下）：

```bash
python3 08_missing_anomaly.py
```

第六段輸出：

```text
== 6. 清理紀錄（audit trail）==
             步驟    進    出  丟棄  修改                                     理由
  依 event_id 去重 2838 2818  20   0                         補傳送了兩次；保留先到的一列
cam-02 百分比 ÷100 2818 2818   0  69 韌體 bug（09-15～09-17）；原值存 confidence_raw
  confidence 缺值 2818 2818   0   0                 cam-08 沒記錄：保留 NaN，不補 0
  worker_id 空字串 2818 2818   0   0                      事件仍發生：保留；人員分析時再排除
 handled_at 空字串 2818 2818   0   0                      沒處理／不適用：保留，分母要分開算
進 2838 列，出 2818 列；丟棄 20 列：
理由
event_id 重複（補傳重送）    20
            event_id event_type               ingested_at
cam-05-20260910-0016     ppe_ok 2026-09-11T01:19:01+00:00
cam-05-20260910-0028     ppe_ok 2026-09-11T01:19:01+00:00
cam-05-20260910-0024     ppe_ok 2026-09-11T01:19:05+00:00
```

讀它的方式：

- **2,838 進、2,818 出，少的 20 列全部說得出來**：同一批補傳送了兩次。丟棄清單（`dropped`）是完整的 DataFrame，可以交給別人逐列核對。
- 第二列的「09-15～09-17」是 `clean()` 從被 ÷100 的列算出來的；日期若超出 `PERCENT_BUG_DAYS`，`clean()` 會先停下來，不會走到這一步。
- **「決定不動」也要寫進紀錄**。三種缺值都是 0 列丟棄、0 列修改——但寫下「為什麼不動」，下一個人才不會「順手」補 0。
- **修改和丟棄分開數**：cam-02 的 69 列沒有被丟，被改了。只看「進幾列、出幾列」會以為這一步什麼都沒做。
- W041 的 18 筆一筆都沒少。`clean()` 裡沒有任何「清異常」的步驟——**不是忘了，是決定**。
- 為什麼 cam-02 以外的 `> 1` 不順手一起 ÷100、而是拋例外？因為那是「不知道原因的異常」，修法未知，不該猜。這一點和第 09 節「不過就停」的立場相同。

### 複習對照：型態、重複、字串正規化

這三件事 MariaDB 第 16 節（匯入品質）已教過原理，這裡只列 pandas 的對應寫法與本資料上的實測。**不在本節重教。**

| 主題 | MariaDB 16 學過的 | pandas 對應 | 本資料實測（教師） |
| --- | --- | --- | --- |
| 型態 | 型別錯誤要擋下 | `astype(float)` 失敗會拋例外；`pd.to_numeric(errors="coerce")` 會把失敗安靜變 NaN | `dashboard-export.csv` 的 `信心度` 是 `"70%"`／`"N/A"`：`astype(float)` 拋 `ValueError: could not convert string to float: '70%'`；去掉 `%` 後 `coerce` 產生 63 個 NaN，全部是 `N/A` |
| 重複 | 重複 ID、唯一鍵 | `duplicated(subset)`、`drop_duplicates(subset, keep=…)` | 整列 `duplicated()` 是 **0**（補傳的 `ingested_at` 不同）；`duplicated("event_id")` 是 **20**。**業務鍵選錯，去重等於沒做** |
| 空字串 vs NULL | 兩者語意不同 | `read_csv` 預設把 `N/A` 讀成 NaN；`keep_default_na=False` 才保留原字串 | 預設讀法 `信心度` 有 63 個 NaN；`dtype=str, keep_default_na=False` 讀則 0 個 NaN、63 個 `"N/A"` |
| 字串正規化 | 為比較而統一 | `.str.strip()`、`.str.lower()`、`.str.replace()` | `events.jsonl` 的 `event_type` 本來就只有 4 種、無大小寫混用；儀表板的 `人員` 用 `"未辨識"` 代替空字串（92 列），合併前要先對應回 `""` |

## Workshop：補 0 vs `dropna`，交出被丟的列

### 任務與時間

**35–42 分鐘：同一份資料，兩種處理。** 以去重後的 2,818 列、cam-02 已 ÷100 為起點，分別做：

- A：`confidence` 補 0。
- B：`dropna(subset=["confidence"])`。

各算：全工地的平均信心度、Z4 的違規數、Z4 的 no_harness 數。哪一種處理讓「施工架的模型最不可靠」？哪一種讓「施工架的違規比較少」？

**42–47 分鐘：交出 audit trail。** 把 B 寫成一個函式，回傳 `(結果, 紀錄, 被丟的列)`，紀錄至少有「進、出、丟棄、理由」。被丟的列依 `camera_id` × `event_type` 計數。

**47–50 分鐘：抓 AI 的錯。** 請 OpenCode「清理 `events.jsonl`：去除重複、處理缺值、移除異常值，輸出乾淨的資料」。拿它的程式驗收：

1. 輸出幾列？W041 在 09-22 的 18 筆 no_harness 還在嗎？
2. 去重用的是整列還是 `event_id`？還剩幾個重複的 `event_id`？
3. cam-08 還在嗎？`ppe_ok` 還在嗎？
4. 它有沒有告訴你丟了哪些列、為什麼？

### 參考判讀

- A（補 0）：全工地平均信心度 0.774 → 0.710；Z4 平均 0.762 → 0.399。違規數不變（496 筆），但「信心度最低的區域」變成 Z4——是假的。
- B（`dropna`）：平均信心度不變（0.774），但**違規事件 496 → 452**，Z4 違規 114 → 70、Z4 no_harness 86 → 56。被丟的 231 列全是 cam-08，其中 44 筆違規。B 讓施工架「看起來比較安全」——也是假的。
- 兩種處理**錯的方向不同**：補 0 改的是「數值」，`dropna` 改的是「事件數」。正確答案是：算信心度時跳過 NaN（並寫明分母 2,587 筆），算違規數時保留全部。
- 教師實測一個常見的 AI 版本（`read_json(lines=True)` 預設讀法 → `drop_duplicates()` → `dropna()` → 以 IQR 移除 `confidence` 離群值）：
  - 預設讀法把 `handled_at` 的空字串轉成 `NaT`，所以 `dropna()` 一口氣把 2,838 列砍到 **212 列**，全部是違規、cam-08 為 0；IQR 再砍到 **207 列**。
  - **整列 `drop_duplicates()` 一列都沒刪**（2,838 → 2,838）：補傳的兩列 `ingested_at` 不同。最後的 207 列中仍有 2 個重複的 `event_id`。
  - W041 在 09-22 的 18 筆只剩 14 筆。少掉的 4 筆不是被當成異常，而是**主管還沒處理**（`handled_at` 空）——最需要追的那幾筆，反而先被刪掉。剩下的 14 筆留下來，也只是因為它們剛好有 `handled_at`，不是 AI 判斷對了。請學生追問 AI「為什麼保留這些」，它答不出依據。
  - 如果 AI 版本先把空字串換成 NaN 再 `dropna()`（本節第三段的寫法），結果是 174 列。各家 AI 寫法不同，數字會不同；**判斷標準是：它有沒有交出被丟的列與理由**。
- 若學生的 audit trail 只有「2,818 → 2,587」，不合格：少的 231 列是哪支攝影機、哪些事件類型，要列得出來。
- 若學生用 `cleaned["confidence"] != cleaned["confidence_raw"]` 數「cam-02 修改了幾列」，會得到 **300**，不是 69：NaN 跟 NaN 比較 `!=` 是 `True`，cam-08 的 231 列被算成「改過」（教師撰寫本節測試時自己踩到）。要加上 `& cleaned["confidence_raw"].notna()`。

### 驗收

- 交出清理前後列數，以及被丟棄列的清單（DataFrame 或 CSV 皆可，不必寫檔，印出來即可）與每一類的理由。
- 能說出 `handled_at`、`confidence`、`worker_id` 三種空各代表什麼，以及「處理率」的分母該用哪一個。
- 能解釋為什麼 IQR 在本資料上會把「一天違規 2 次」也當成異常。
- AI 版本的四個問題都有答案，而且至少找到一個它默默丟掉的東西。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，**標準輸出逐字相同**。〈參考判讀〉與複習對照表的數字為教師另以兩個環境執行的片段實測，結果相同；這些片段不在 Demo 內，本節測試涵蓋其中的關鍵數字（`test_lesson_08.py`）。

**資料**：`data/events/` 由 `tools/build_events.py`（固定種子）產生，**全部為合成資料**；刻意埋入的狀況列於 `data/events/MANIFEST.json` 的 `planted`。本節用到：三種缺值、cam-02 百分比 bug、W041 的真實異常、補傳重送 20 筆。

**界線**：

- 「W041 是真的出事」是**依資料產生方式**判定的（產生器刻意埋入）。真實資料沒有產生器可以看，判斷要靠現場紀錄、同一時段其他攝影機、主管處理紀錄等旁證；本節不宣稱有一條統計規則能自動分辨。
- z-score 用樣本標準差（`std()` 預設 `ddof=1`）；改成母體標準差，W041 那一格 z 從 15.64 變 15.67，結論相同（教師實測）。
- 補傳重送的去重保留「先到的」一列，是因為兩列除 `ingested_at` 外完全相同；若內容不同，應比照第 09 節停下來。
- 本節**尚未實班試教**。

**舊教材**：改寫自 [缺值處理](https://hackmd.io/@yillkid/ryssxkCN-l)。保留「缺值不是錯，是常態」與「`dropna` 代表這筆事件不存在」兩句——後者升格為第三段的主張。**刪除**「數值欄補 0、次數補預設值」的常見補值情境表：在本資料上補 0 直接造成錯誤結論。論述從「一組清理 API」改為「判斷與紀錄」；`isna`／`fillna`／`dropna` 的語法不再逐一示範。型態（[astype](https://hackmd.io/@yillkid/B1qGwxAV-g)）、重複（[duplicated](https://hackmd.io/@yillkid/B1dnXVC4Zl)）、字串正規化（[str.replace](https://hackmd.io/@yillkid/HyBKSm0VZg)）三篇不再獨立成節，壓成第六段末的複習對照表；舊版「整列一模一樣＝重複」的定義，在本資料上實測會漏掉全部 20 筆重送，改為「先選業務鍵」。

**下一節**：第 09 節〈資料驗證與冪等〉——本節的 `clean()` 是「判斷」；下一節把「不能接受的資料」寫成會讓流程停下來的驗證，並證明同一批重跑結果一樣。
