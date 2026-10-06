# 13｜衍生欄位與可稽核規則

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 13 節：衍生欄位與可稽核規則。**
> 本節把第 12 節的「每人違規次數」改成每人每週一列，再分級成 `risk_level`。重點不是「用哪個函式分級」，而是**分出來的等級，別人能不能檢查**：門檻寫在哪裡、邊界算哪一級、沒資料算哪一級、規則改了怎麼知道。
> 本節不是特徵工程課——「哪些欄位適合拿去訓練模型」是機器學習課第 02 節的事；這裡只負責交出一份**有版本、有出處**的判定結果。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：說出 `apply` 逐列 `if` 在本資料上分錯了哪些列、為什麼不會報錯；用 `np.select` 與 `pd.cut` 寫出邊界明確、缺值有去處的分級；說明 `qcut` 為什麼不能當判定規則；為一條規則輸出版本、門檻、資料期間與依據。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–5 分鐘 | 衍生欄位不是原始資料 | 每人每週 240 列，32 列 NaN |
| 5–14 分鐘 | `apply` 逐列 `if` | 240 列分錯 61 列，沒有錯誤訊息 |
| 14–22 分鐘 | `np.select` 與 `pd.cut` | `right=True` 讓 0 次變 NaN |
| 22–28 分鐘 | `qcut` 的問題 | 同樣 4 次，第 1 週「中」、第 2 週「高」 |
| 28–35 分鐘 | 規則要有版本與出處 | 規則說明、`rule_version` 欄 |
| 35–50 分鐘 | Workshop：改規則，交出差異 | risk-v2 與差異清單 |

先修：本課第 08 節（缺值＝沒發生／沒記錄）、第 12 節（每人彙總、名冊補人）。環境同第 02 節。

## 一、衍生欄位不是原始資料

`risk_level` 不在任何一個上游檔案裡。它是**你**訂的規則算出來的：「一週違規 3 次以上算中、5 次以上算高」。攝影機沒有說過這句話，主管也沒有——這是一個決定。

所以衍生欄位跟原始欄位有一個根本差別：**原始欄位錯了，可以回頭查來源；衍生欄位錯了，只能回頭查規則。**規則若只存在某個人的 `if` 裡，就沒有人能查。

本節的表是「每人每週一列」：第 12 節的每人彙總，再依週切開；名冊 60 人 × 資料期間 4 週＝240 列。某人某週一次都沒被辨識到，`violations` 留 `NaN`，**不是 0**：

```text
每人每週 240 列（60 人 × 4 週）；violations 為 NaN 的 32 列（那一週沒被拍到）
```

32 列是 W053–W060 的 8 人 × 4 週。0 次違規的意思是「拍到了，都有戴好」；NaN 的意思是「沒拍到，不知道」。這兩件事分級時必須去不同的地方。

## 二、`apply` 逐列 `if`：錯在哪裡

舊教材與 AI 最常給的寫法（這段即 Demo 第 1 段裡的 `naive()`；單獨列出的這個區塊本節測試不涵蓋）：

```python
def naive(n):          # 需求：「3 次以上為中、5 次以上為高」
    if n > 5:
        return "高"
    elif n > 3:
        return "中"
    else:
        return "低"

table["naive"] = table["violations"].apply(naive)
```

常聽到的批評是「`apply` 很慢」。在 240 列上，慢根本不是問題。**問題是它錯了，而且錯得很安靜**：

```text
== 1. apply 逐列 if：邊界與 NaN ==
 violations apply_if np_select
        3.0        低         中
        5.0        中         高
        NaN        低       無資料
240 列中分錯 61 列：邊界 3 或 5 次 29 列、NaN 變成「低」 32 列、其他 0 列；沒有任何錯誤訊息
```

兩個錯，各自有來由：

- **邊界**：需求說「3 次**以上**」，程式寫 `> 3`。剛好 3 次、剛好 5 次的人被降了一級——29 列。這種錯在 `if` 鏈裡很難看出來，因為門檻散在三行裡，每一行看起來都合理。
- **NaN**：`NaN > 5` 是 `False`、`NaN > 3` 也是 `False`（第 08 節：NaN 的大小比較一律為 False），於是一路掉進 `else`，變成「低」。**沒被拍到的 8 個人，被標成低風險**。下游看到「低」，會以為這個人表現良好。

就算把 `>` 改成 `>=`，NaN 的 32 列照樣變「低」（教師實測）。`if` 鏈的結構本身就是問題：**它一定有一個 `else`，任何沒想到的值都會被收進去**，而且不會告訴你。

## 三、`np.select` 與 `pd.cut`：讓每一個值都有明確的去處

### `np.select`：條件清單，對號入座

`risk_level()` 把規則寫成一組條件與標籤，`np.select` 依序比對：

- 第一條條件是 `x.isna()` → 「無資料」。缺值**先**被接住，不會落進任何一級。
- 每一級寫成「下限含、上限不含」：`(x >= 3) & (x < 5)`。邊界只有一種寫法，不會有人寫 `>`、有人寫 `>=`。
- `default="未分類"`，跑完檢查有沒有任何列是「未分類」——有就拋例外。`if` 鏈的 `else` 吞掉意外，這裡把意外變成錯誤。
- 負數、非整數直接拒絕：違規次數不會是 -1 或 2.5，出現了代表上游壞了。

門檻不寫在函式裡，寫在 `RULE` 這個資料結構裡。要改門檻，改的是資料，不是程式邏輯——下一段的規則說明也從同一份 `RULE` 產生，**說明和實際執行的規則不可能不同步**。

### `pd.cut`：預設的邊界跟你想的不一樣

`pd.cut` 是專門做分級的函式，但它的預設是 `right=True`：區間**左開右閉** `(0, 3]`。同一組門檻 `[0, 3, 5, inf]`：

```text
== 2. pd.cut 的 right：同一組門檻，兩種邊界 ==
 violations right=True right=False
          0        NaN           低
          2          低           低
          3          低           中
          4          中           中
          5          中           高
         24          高           高
right=True ：低 135、中 18、高 11、NaN 76（其中 0 次的 44 列）
right=False：低 154、中 39、高 15、NaN 32（其中 0 次的 0 列）
right=False 與 np.select 結果相同：True
```

- `right=True`（預設）：3 次算「低」、5 次算「中」——跟第二段 `apply` 的錯法一模一樣。更糟的是 **0 次變成 NaN**：`(0, 3]` 不包含 0。「整週都戴好安全帽」的 44 列，跟「沒拍到」的 32 列混在一起，一共 76 個 NaN。
- `right=False`：區間 `[0, 3)`，「下限含、上限不含」，結果與 `np.select` 完全相同。

**`pd.cut` 不是錯的工具，但它的預設值不是你的規則。**用它時把 `right` 明寫出來，並且像 `np.select` 一樣，事後檢查 NaN 的數量是不是剛好等於原本的缺值數。

## 四、`qcut`：門檻跟著資料跑

`pd.qcut` 依「分位數」切：例如前 50% 算低、50–90% 算中、最高 10% 算高。不用自己想門檻，看起來很方便。每一週各自 `qcut`：

```text
== 3. qcut：門檻跟著資料跑 ==
      week                    門檻 2 次 4 次  高的人數
2026-08-31 [0.0, 1.5, 4.0, 10.0]   中   中     2
2026-09-07  [0.0, 2.0, 3.9, 6.0]   低   高     6
2026-09-14 [0.0, 2.0, 5.0, 12.0]   低   中     5
2026-09-21 [0.0, 1.0, 3.9, 24.0]   中   高     6
每週各自 qcut 與固定規則 risk-v1 相比：208 列中 33 列等級不同
```

- **同樣是一週違規 4 次**：第 1 週「中」、第 2 週「高」、第 3 週「中」、第 4 週「高」。同樣 2 次，有兩週是「中」、兩週是「低」。
- 門檻 `3.9`、`1.5` 不是任何人訂的數字，是分位數內插出來的。被問「為什麼他是高風險」，你只能回答「因為他比這週 90% 的人多」——**跟他自己做了什麼無關，跟別人做了什麼有關**。
- 「高」的人數也不由行為決定：分位數保證大約固定比例的人會是高，整個工地都變安全了，也一樣有人是「高」。

`qcut` 適合回答「這個人在這群人裡排第幾」（描述），不適合當「這個人要不要被約談」的判定規則。判定規則的門檻必須**事先訂好、寫下來、不隨資料變動**，才能稽核。

## 五、規則要有版本與出處

可稽核的意思是：拿到結果的人，**不看程式**也能知道每一個等級是怎麼來的，而且能自己重算一遍。`describe_rule()` 從 `RULE` 和 `event-types.csv` 產生一段說明，跟結果一起交出去：

```text
== 4. 規則說明：版本、門檻、資料期間、出處 ==
規則 risk-v1（2026-10-05 訂定）
計數單位：每人每週（週一～週六，台灣時間）已辨識、依 event_id 去重後的違規次數
資料期間：2026-08-31 ～ 2026-09-26
  低：0 次以上、未滿 3 次
  中：3 次以上、未滿 5 次
  高：5 次以上
  無資料：該週沒有被辨識到任何事件（不是 0 次）
計入的違規類型與依據（營造安全衛生設施標準，練習站條文，不具法律效力）：
  no_helmet（未戴安全帽）→ N0060014 第 11-1 條：進入營繕工程工作場所應正確戴用安全帽
  no_harness（高處未使用安全帶）→ N0060014 第 19 條：高度二公尺以上有墜落之虞且防護設備開啟時應使用安全帶
  restricted_entry（跨越警示線）→ N0060014 第 24 條：作業進行中應禁止勞工跨越警示線
門檻依據：event-types.csv 的 is_violation；門檻為本課示範用，不是任何法規或公司規定
```

一段規則說明至少要回答五件事：

| 問題 | 本例 |
| --- | --- |
| 哪一版？ | `risk-v1`，2026-10-05 訂定；結果表每一列都帶 `rule_version` |
| 算的是什麼？ | 計數單位：每人每週、已辨識、去重後 |
| 邊界算哪邊？ | 「以上」「未滿」，不是「大於」「到」 |
| 沒資料算什麼？ | 「無資料」，獨立一級 |
| 依據是什麼？ | 違規類型對到法條（`pcode`＋`slug`，第 14 節會接上條文原文）；**門檻本身沒有法規依據**，這一點要直接寫出來 |

最後一條最容易被省略。法條規定「應戴安全帽」，沒有規定「一週 5 次算高風險」。把門檻寫得像是法規要求，是把自己的決定偽裝成別人的。

以下為完整 `13_derived_rules.py`，只讀 `data/events/`，不寫檔、不連線。

<!-- demo: 13_derived_rules.py -->
```python
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
```

執行（在本目錄下）：

```bash
python3 13_derived_rules.py
```

最後一段：

```text
== 5. 交出去的表 ==
risk_level
低      154
中       39
高       15
無資料     32
worker_id       week  events  violations risk_level rule_version
     W041 2026-08-31       6         2.0          低      risk-v1
     W041 2026-09-07      12         4.0          中      risk-v1
     W041 2026-09-14      17         6.0          高      risk-v1
     W041 2026-09-21      32        24.0          高      risk-v1
```

讀它的方式：

- 154＋39＋15＋32＝240，**每一列都有等級**，「無資料」單獨一類。
- W041 四週依序是低、中、高、高。第 4 週 24 次中有 18 次是 09-22 下午連續發生的（第 12 節）——等級看得出「他變糟了」，看不出「那是一個下午的事」。這是第 15 節要處理的。
- `events` 是整數、`violations` 是浮點數：沒被拍到的那一週，偵測次數確實是 0，違規次數卻是「不知道」。浮點數是因為 NaN，不是寫錯。

## Workshop：改規則，交出差異

### 任務與時間

**35–42 分鐘：發布 risk-v2。** 安全主管要求收緊：「2 次以上為中、4 次以上為高」。複製 `RULE`，改成 `risk-v2`，重新分級，並輸出新的規則說明。

```python
# Workshop 起手式，本節測試不涵蓋這段
table, types, period = weekly_counts()
table["v1"] = risk_level(table["violations"])
v2 = dict(RULE, version="risk-v2", levels=[("低", 0, 2), ("中", 2, 4), ("高", 4, None)])
table["v2"] = risk_level(table["violations"], v2)
```

**42–46 分鐘：交出差異。** 有幾列的等級變了？用 `pd.crosstab(table["v1"], table["v2"])` 看它們從哪裡移到哪裡。「無資料」有沒有變？應不應該變？

**46–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫「依每週違規次數產生 risk_level：3 次以上中、5 次以上高」。拿它的程式跑本節的 240 列，檢查三件事：剛好 3 次、5 次的人是哪一級？W053 是哪一級？有沒有一段文字說明規則版本與門檻？

### 參考判讀

- risk-v2 下，**67 列**等級改變；分布為低 101、中 78、高 29、無資料 32（教師實測）。「無資料」32 列不變——門檻怎麼改，沒拍到的人都不該被分到任何一級。
- 若你的 v2 讓「無資料」變少，代表你的程式在某一步把 NaN 補成了 0。教師實測：先 `fillna(0)` 再分級，v1 的「低」從 154 變 186。
- 常見的 AI 版本是 `apply` ＋ `if n >= 5 … elif n >= 3 … else`：邊界對了，但 W053–W060 的 32 列被標成「低」（教師實測 240 列中錯 32 列）；或是 `pd.cut(x, [0, 3, 5, inf])` 沒寫 `right`：3 次算低、0 次變 NaN。**兩種都不會報錯**。
- AI 幾乎不會主動輸出規則說明。沒有版本的分級結果，下週門檻改了，沒有人分得出哪些「高」是舊規則判的。

### 驗收

- `risk_level` **不得以 `apply` 逐列判斷實作**；用 `np.select` 或 `pd.cut(right=False)`。
- 240 列每一列都有等級；NaN 的列是「無資料」，數量等於原本的缺值數（32）。
- 交出 risk-v2 的規則說明，五個問題（版本、單位、邊界、無資料、依據）都有回答，且寫明門檻沒有法規依據。
- 交出 v1 → v2 的差異列數與 crosstab，並能解釋為什麼「無資料」不變。
- 能說出 `qcut` 為什麼不能當判定規則（同樣 4 次，不同週不同級）。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，Demo **標準輸出逐字相同**；Workshop 參考判讀的數字兩版相同。兩版都實測過：`pd.cut` 預設 `right=True` 讓左端點 0 變 NaN；`qcut` 以 `[0, 0.5, 0.9, 1]` 切本資料四週皆不需 `duplicates="drop"`。

**資料**：同第 12 節，合成資料，不代表任何真實工地。門檻 3／5 次為**示範用**，不是任何法規、標準或公司規定；違規類型對應的法條取自練習站 `articles.jsonl`，可能經刻意修改，不具法律效力。週以 `event_time` 的當地日期計算（週一起算，週日停工）。

**與機器學習課的對齊**（ML 課第 02 節接手「事件彙總表」）：

- 本節產出的欄位是 `worker_id, week, events, violations, risk_level, rule_version`，一列是「一人一週」。ML 課的問題是「這個**事件**要不要通知主管」，一列是一個事件；y 是「主管實際有沒有處理」，也就是 `handled_at` 是否非空（教師實測：已辨識的違規 419 筆中，有 `handled_at` 的 190 筆）。
- **`handled_at` 及任何由它衍生的欄位都是答案的影子**：「處理時間」「本週已處理次數」「處理率」……只要從 `handled_at` 算出來，就是把 y 放進 X。本節的表刻意**不含** `handled_at` 衍生欄位；若 ML 課要加，必須在講義中標成洩漏欄位，不是特徵。
- 本節的 `violations`、`risk_level` 是**整週**算的。若直接依 `(worker_id, week)` 接回事件當特徵，週一的事件就看得到週六才發生的違規。教師實測：2454 筆已辨識事件中，「整週等級」與「事件發生當下、只算這週之前已發生的違規」的等級不同者 **490 筆**；整週等級為「高」的事件 213 筆，當下就已達「高」的只有 82 筆。ML 課若要用，需改成「截至事件時間之前」的累計（`groupby().cumsum()` 減去自己），或用前一週的等級。此項建議需 ML 課第 02、03 節撰寫者確認。
- `risk_level` 本身是規則的輸出；ML 課第 01 節的「規則版 baseline」可以直接用它，但要記錄 `rule_version`。

**界線**：本節不談「門檻該訂多少」——那需要現場與安全主管的判斷，不是資料能決定的。`np.select` 在大資料上比 `apply` 快，但本節**沒有做速度比較**，也不以速度當論點。本節**尚未實班試教**。

**舊教材**：改寫自 [新增衍生欄位（風險分數、等級）](https://hackmd.io/@yillkid/B1904jR4-l)。保留「衍生欄位不是原始資料、是定義規則後算出來的」與「一整欄一起算」；舊版的 `apply(risk_level)` 改為**反例**，並實測它在本資料的邊界與 NaN 錯誤；`risk_score = fail_count` 這一步（把一欄複製成另一欄）刪除；「對 AI 模型來說這是 Feature Engineering 的第一步」的論述**換成「可稽核的判定規則」**，特徵工程交給 ML 課。[DataFrame 合併與操作](https://hackmd.io/@yillkid/SJENzeiEc) 的運算部分（`subtract` 兩表相減）不採用：它示範的是 index 對齊的算術，與分級無關；本節 Workshop 的 v1／v2 比較改用 `crosstab`。`np.select`、`pd.cut`、`qcut`、規則說明與版本皆為新增。

**下一節**：第 14 節〈跨來源合併與 fan-out〉——規則說明裡的「N0060014 第 19 條」只是一個代碼。下一節把事件、名冊、事件類型、法條原文四份資料接起來，並看 W023 的兩列名冊會讓數字翻倍到什麼程度。
