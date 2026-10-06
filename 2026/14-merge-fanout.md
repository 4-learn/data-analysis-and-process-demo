# 14｜跨來源合併與 fan-out

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 14 節：跨來源合併與 fan-out。**
> 本節把事件接上名冊、接上事件類型、再接上法條原文；也把廠商儀表板的匯出跟事件表疊在一起。每一次合併都**先預測列數、再執行、再核對**，並交出一張「合併前後列數與原因」的表。
> 本節不是 SQL JOIN 課（MariaDB 課已教）；這裡處理的是 pandas 的 `merge` 在什麼情況下**默默多出列、默默少掉列**，以及怎麼讓它停下來。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 範例程式碼

- [demo：14_merge_fanout.py](https://github.com/4-learn/data-analysis-and-process-demo/blob/master/2026/14_merge_fanout.py)（與本頁 Demo 逐字相同）
- 練習資料與環境說明：[2026/README](https://github.com/4-learn/data-analysis-and-process-demo/tree/master/2026)

## 學習目標與時間

完成後，你能：在執行 `merge` 之前算出它會產生幾列；說出 `inner`／`left`／`outer` 各自讓誰消失；用 `validate` 與 `indicator` 讓 fan-out 與遺漏變成看得見的錯誤；依有效期間合併一份「同一個人有兩列」的名冊；分辨什麼時候該 `concat`、什麼時候該 `merge`。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–6 分鐘 | 先預測，再執行 | 三種 `how` 由鍵次數算出的預測與實際列數 |
| 6–10 分鐘 | `validate` | fan-out 變成 `MergeError` |
| 10–18 分鐘 | 依有效期間合併 | W023 的 52 筆分到正確的承攬商 |
| 18–24 分鐘 | `how` 與 `indicator` | 誰在 left_only、誰在 right_only |
| 24–30 分鐘 | 三方合併：事件 → 法條原文 | 鍵是 `(pcode, slug)`，不是 `slug` |
| 30–35 分鐘 | `concat` 的欄位對齊 | 19 欄、每列有一邊全是 NaN |
| 35–50 分鐘 | Workshop：每個承攬商的違規率 | 合併前後列數表＋差異原因 |

先修：本課第 12 節（名冊補人、W023 兩列）、第 13 節（規則說明裡的法條代碼）；MariaDB 課的 JOIN。環境同第 02 節。

## 一、先預測，再執行

課綱要求的順序：**先在紙上算出 `merge` 會產生幾列，再按執行**。算不出來，代表你還不知道兩邊的鍵長什麼樣子。

要算，需要五個數字：事件幾列、其中幾列有 `worker_id`；名冊幾列、幾個不同的人；有沒有人在名冊出現不只一次、他有幾筆事件；名冊上有誰沒有任何事件。

```text
== 1. 先預測，再執行 ==
事件 2818 列（已辨識 2454、未辨識 364）；名冊 61 列、不同 worker_id 60；名冊不只一列的人 W023（2 列、事件 52 筆）；名冊上沒有事件的 8 人
how=inner  預測 2506  實際 2506  與事件數相差 -312
how=left   預測 2870  實際 2870  與事件數相差 +52
how=outer  預測 2878  實際 2878  與事件數相差 +60
```

預測怎麼來的（Demo 的 `predict_rows()` 就是這個算法：**只數兩邊每個鍵出現幾次，不執行 merge**——兩邊都有的鍵產生「左邊次數 × 右邊次數」列，只有一邊有的鍵在 `left`／`outer` 時各留一列）：

- **inner**：只留兩邊都有的鍵。已辨識 2454 筆，其中 W023 的 52 筆在名冊對到兩列，各變兩列：2454＋52＝**2506**。未辨識的 364 筆（`worker_id` 是 `""`）名冊沒有對應，全部消失。
- **left**：事件全留。2818＋52＝**2870**。
- **outer**：再加上名冊上沒有事件的 8 人，各一列：2870＋8＝**2878**。

三種結果**沒有一種等於 2818**。`inner` 比事件少、`left` 比事件多，而兩者都**沒有任何警告**。拿 `left` 的結果去數「違規幾次」，W023 的違規就被算了兩遍。這就是 **fan-out**：一對多的鍵讓左邊的列被複製。

## 二、`validate`：讓 fan-out 變成錯誤

你**預期**的關係是「很多事件對一個人」——many-to-one。把這個預期寫進 `merge`：

```text
== 2. validate 讓 fan-out 變成錯誤 ==
MergeError: Merge keys are not unique in right dataset; not a many-to-one merge
```

`validate="many_to_one"` 會檢查右邊的鍵是否唯一，不是就**直接報錯**，而不是悄悄多出 52 列。第 03 節的 `validate="one_to_one"` 是同一件事。

`validate` 只告訴你「關係不是你以為的那樣」，不告訴你怎麼辦。最常見的錯誤「修法」是 `roster.drop_duplicates("worker_id")`——錯誤消失了，但 W023 的 52 筆事件現在全部掛在**第一列**（乙鋼構）底下，其中 23 筆其實是轉到丙土木之後發生的。**讓錯誤訊息消失，不等於解決問題。**

## 三、依有效期間合併

W023 在名冊有兩列，因為他在 2026-09-14 換了承攬商：

```text
W023,楊美玲,乙鋼構,施工架工,Z4,2026-08-31,2026-09-13
W023,楊美玲,丙土木,施工架工,Z4,2026-09-14,
```

所以名冊的鍵不是 `worker_id`，而是 `worker_id`＋**一段期間**。正確的合併是：事件的日期落在 `valid_from`～`valid_to`（空＝至今）的那一列。

`attach_roster()` 的做法：

1. 先用 `worker_id` 做 `left` 合併（這一步會 fan-out，沒關係）。
2. 留下「沒對到名冊」或「事件日期落在有效期間內」的列。
3. **合併後驗證**：每個 `event_id` 只能出現一次（否則名冊的期間重疊）；每一筆已辨識事件都要對到一列名冊（否則名冊漏了人，或期間有缺口）；總列數必須等於事件數。三者任一不成立就拋例外。

日期用 `event_time` 的前 10 個字元：它是工地當地時間（`+08:00`），名冊的日期也是當地日期。**拿 UTC 的日期比，07:00–07:59 的事件會變成「前一天」**（第 10、11 節），Workshop 會實際踩一次。

```text
== 3. 依有效期間合併 ==
            事件  違規          最早          最晚
contractor                                
乙鋼構         29   2  2026-08-31  2026-09-12
丙土木         23   3  2026-09-14  2026-09-26
            天真合併  依有效期間
contractor             
丙土木          115    113
乙鋼構          204    201
甲營造          105    105
違規合計：天真合併 424、依有效期間 419（已辨識違規 419）
```

- W023 的 52 筆分成 29＋23，日期在 09-13／09-14 乾淨地切開（09-13 是週日，沒有事件）。
- 天真合併的違規合計是 **424**，比實際的 419 多 5——W023 的 5 次違規被乙鋼構和丙土木**各算一次**。多出來的分布是交叉的：乙鋼構多 3（W023 轉到丙土木之後的 3 次違規），丙土木多 2（轉來之前、還在乙鋼構時的 2 次）——每一家都多算了對方那一段。
- **核對方式**：合併後各承攬商的違規加總，必須等於合併前的已辨識違規數。424 ≠ 419，一眼就知道有 fan-out。

## 四、`how` 與 `indicator`：誰不見了

`indicator=True` 會多一欄 `_merge`，標記每一列是 `both`、`left_only` 還是 `right_only`。用 `outer` 加 `indicator`，兩邊消失的人都看得到：

```text
== 4. how 與 indicator：誰不見了 ==
_merge
both          2454
left_only      364
right_only       8
left_only 的 worker_id：['']；right_only：W053…W060
名冊漏了 W041 時 how=inner：2818 → 2387 列；消失 431 筆，其中未辨識 364、W041 67（違規 36）
attach_roster: 67 筆已辨識事件對不到名冊（不在名冊或不在有效期間內），例如 cam-01-20260923-0010
```

（這裡把名冊先 `drop_duplicates("worker_id")`，只為了看「誰對不到誰」，不是為了算承攬商。）

- **`left_only` 364 筆**：全部是 `""`——認不出臉的事件。用 `inner`，它們就從工地的違規統計裡消失；第 12 節算過，這批事件的違規率**比較高**。
- **`right_only` 8 人**：W053–W060。用 `left`，他們不會出現；這是「事件接名冊」的正常結果，但如果你要的是「每個人的狀況」，就要反過來以名冊為主（第 12 節的 `reindex`）。
- **名冊過期的情況**：假設你拿到的名冊漏了 W041（例如他是後來才補登的）。`inner` 安靜地丟掉 431 筆，其中包括 W041 的 **36 次違規**——本資料違規最多的人，在合併後的表裡**不存在**。`attach_roster()` 用 `left` 並檢查「已辨識事件有沒有全部對到」，所以它停下來，告訴你 67 筆對不到。

**`how` 的選擇不是語法問題，是「誰可以消失」的決定**。事件表接參考資料時，幾乎都該用 `left`，然後明確檢查 `left_only` 是不是你預期的那些。

## 五、三方合併：事件 → 事件類型 → 法條原文

第 13 節的規則說明寫著「no_harness → N0060014 第 19 條」。現在把條文原文接上：事件 × `event-types.csv`（用 `event_type`）× `articles.jsonl`（用 `pcode`＋`slug`）。

先看只用 `slug` 會怎樣——`event-types.csv` 和 `articles.jsonl` 都有 `slug` 欄，AI 很常只寫 `on="slug"`：

```text
== 5. 三方合併：事件 → 類型 → 法條原文 ==
只用 slug 接 articles：2818 → 2374 列；'11-1' 對到 1 部、'19' 對到 9 部、'24' 對到 8 部
```

2374 這個數字**比 2818 少**，看起來像「少了一些」，其實是兩個錯疊在一起：

- **fan-out**：`slug` 是「第幾條」，9 部法規都有第 19 條。每一筆 `no_harness` 被複製成 9 列，分別接上勞基法第 19 條、性平法第 19 條……；`restricted_entry` 變 8 列。
- **inner 丟列**：`ppe_ok` 沒有對應法條（`slug` 是空字串），預設的 `how="inner"` 把 2322 筆全部丟掉。

一多一少，結果剛好落在一個「看起來不離譜」的數字上。**只看列數變多或變少不夠，要看差了多少、為什麼。**法條的業務鍵是 `(pcode, slug)`（第 03、09 節），少一個欄位就不是同一個鍵。

`attach_articles()` 用 `(pcode, slug)`、`how="left"`、兩次 `validate="many_to_one"`，再檢查「每一筆違規都找得到條文」：

```text
== 5. 三方合併：事件 → 類型 → 法條原文 ==
只用 slug 接 articles：2818 → 2374 列；'11-1' 對到 1 部、'19' 對到 9 部、'24' 對到 8 部
                                        事件數                             條文
event_type       law_name   article_no                                    
no_harness       營造安全衛生設施標準 第 19 條      170  雇主對於高度二公尺以上之屋頂、鋼梁、開口部分、階梯、樓梯…
restricted_entry 營造安全衛生設施標準 第 24 條       74  雇主對於坡度小於十五度之勞工作業區域，距離開口部分、開放…
no_helmet        營造安全衛生設施標準 第 11-1 條    252  雇主對於進入營繕工程工作場所作業人員，應提供適當安全帽，…
ppe_ok 2322 筆沒有對應法條（不是違規，content 為 NaN）
```

（第一行是上面那個錯誤示範。）每種違規只對到營造安全衛生設施標準的一條；`ppe_ok` 留著，條文欄是 NaN——它不是違規，本來就沒有法條，這是事實不是缺值。條文取自練習站，**可能經刻意修改，不具法律效力**。

## 六、`concat`：上下接，欄名不同就不會對齊

舊教材唯一的合併工具是 `concat`。它把兩張表**上下疊起來**，依**欄名**對齊。廠商儀表板匯出的是第 1 週的同一批事件，但欄名是中文：

```text
== 6. concat：欄名不同就不會對齊 ==
events 第 1 週 (692, 12) ＋ 儀表板 (692, 7) → (1384, 19)
18 欄恰好有 692 個 NaN；例如 event_id 缺 692、事件編號 缺 692
轉成相同欄名後 concat：(1384, 7)；event_id 重複 692 筆——同一週、同一批事件
改用 merge 對帳：{'both': 692, 'left_only': 0, 'right_only': 0}；欄位不一致 {'zone': 0, 'camera_id': 0, 'worker_id': 0, 'event_type': 0, 'event_time': 0, 'confidence': 0}
```

- **欄名沒有一欄相同**（第七段「欄名相同的 0 欄」是程式算的交集），`concat` 就產生 12＋7＝19 欄：上半部 692 列只有英文欄有值，下半部只有中文欄有值。**沒有錯誤**。18 欄恰好缺一半；第 19 欄 `confidence` 缺得更多，因為 cam-08 本來就沒有。
- **欄名對齊了也不對**：`dashboard_as_events()` 把中文欄名、`87%`、`未辨識`、`2026/08/31 07:04` 都轉成事件表的格式後再 `concat`，得到 1384 列——同一筆事件出現兩次。**`concat` 是「同一種東西、更多筆」，例如第 1 週＋第 2 週；兩份來源記錄的是同一批事件時，該用的是 `merge` 對帳。**
- 對帳結果：692 筆一對一全對上，六個欄位**全部一致**（時間比到分鐘，信心度容許 0.005 的誤差，因為儀表板四捨五入到整數百分比）。這才證明「儀表板與原始事件是同一份資料」，之後可以只用一份。

## 七、合併前後列數

課綱的驗收：每一次合併都要交出「合併前後列數」與差異原因。Demo 最後把上面每一步記成一張表：

```text
== 7. 合併前後列數 ==
                                        步驟  合併前   預測  合併後   差異                                                    原因
  events × workers.csv（只用 worker_id, left） 2818 2870 2870   52                                 W023 名冊 2 列：52 筆事件被複製
               events × workers.csv（依有效期間） 2818 2818 2818    0                      attach_roster() 內部核對：每筆事件只對到一段名冊
         events × workers.csv（名冊去重, inner） 2818 2454 2454 -364                              未辨識 364 筆沒有 worker_id 可對
         × event-types × articles（只用 slug） 2818 2374 2374 -444 違規 fan-out（19 對 9 部、24 對 8 部）＋ppe_ok 2322 筆被 inner 丟掉
× event-types × articles（pcode＋slug, left） 2818 2818 2818    0                            attach_articles() 內部核對：無差異
            concat events 第 1 週 ＋ 儀表板（原欄名）  692 1384 1384  692                       欄名相同的 0 欄：12＋7＝19 欄，每列有一邊全是 NaN
預測與實際全部一致：True
```

「預測」欄不是事後抄實際列數：用 `merge` 的步驟都經過 `checked_merge()`——先用 `predict_rows()` 從鍵的次數算出預測，執行後列數不等於預測就拋例外；`concat` 的預測是兩邊列數相加。原因欄的數字（W023 幾列、幾筆事件被複製、哪個 slug 對到幾部、哪種事件被丟掉幾筆）也是從資料算出來的，不是寫死的字串——換一份名冊，原因會跟著變。差異是 0 的那兩列，是**驗證過**的 0：`attach_roster()` 和 `attach_articles()` 都在內部檢查了列數，不相等就停。差異不是 0 的那幾列，每一列都要能用一句話說出原因，而且原因要對得上第一段的預測。

以下為完整 `14_merge_fanout.py`，只讀 `data/`，不寫檔、不連線。

<!-- demo: 14_merge_fanout.py -->
```python
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
```

執行（在本目錄下）：

```bash
python3 14_merge_fanout.py
```

## Workshop：每個承攬商的違規率

### 任務與時間

**35–40 分鐘：先預測。** 老闆要「每個承攬商的違規率（違規 ÷ 已辨識事件）」。在執行任何 `merge` 之前，寫下：只用 `worker_id` 做 `inner` 合併，**甲營造、乙鋼構、丙土木各會有幾列？** 提示：W023 的 52 筆會同時出現在乙鋼構與丙土木。

**40–45 分鐘：執行並核對。** 用 `attach_roster()` 合併，算出三個承攬商的事件數、違規數、違規率。再用天真的 `inner` 合併算一次。兩張表差在哪幾格？各承攬商的事件數加總，應該等於多少？

```python
# Workshop 起手式，本節測試不涵蓋這段
ev = read_events()
ev["violation"] = ev["event_type"].isin(VIOLATIONS)
staff = attach_roster(ev, read_csv("workers.csv"))
table = staff[staff["worker_id"] != ""].groupby("contractor").agg(...)   # 你來寫
```

**45–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫「把事件表和名冊合併，算每個承攬商的違規率」。拿它的程式檢查：它用哪個 `how`？有沒有 `validate`？W023 被算到哪裡？各承攬商事件數加總是 2454 嗎？若它有處理有效期間，再把 `event_time` 換成 UTC 給它跑一次。

### 參考判讀

- 依有效期間（教師實測）：甲營造 817 事件／105 違規（0.129）、乙鋼構 846／201（0.238）、丙土木 791／113（0.143），事件加總 **2454**、違規加總 **419**。
- 天真 `inner`：甲營造 817／105、乙鋼構 **869／204**、丙土木 **820／115**，事件加總 2506。甲營造沒有 W023，所以完全相同；乙鋼構多 23 筆（W023 轉走之後的事件）、丙土木多 29 筆（W023 轉來之前的事件）——**每一家都多算了「不屬於自己的那一段」**。違規率只差千分之三，看起來沒事；但事件數加總 2506 ≠ 2454，核對一下就會發現。
- 常見的 AI 版本是 `pd.merge(events, workers, on="worker_id")`：預設 `inner`、沒有 `validate`、沒有去重。它同時犯了三個錯——沒去重（第 12 節）、未辨識的 364 筆消失、W023 fan-out——但三個錯都不會報錯。
- 若 AI 版本有處理有效期間，但拿 **UTC 日期**比 `valid_from`：教師實測 `attach_roster()` 會停下來，「4 筆已辨識事件對不到名冊（不在名冊或不在有效期間內）」——2026-08-31 早上 7 點多的事件在 UTC 是 08-30，早於所有人的 `valid_from`。沒有做這個檢查的版本，會讓這 4 筆安靜地掉到「沒有承攬商」。
- 名冊的期間若有重疊（例如把 W023 第一列的 `valid_to` 改成 2026-09-20），`attach_roster()` 拋「名冊有效期間重疊：['W023']」。這代表名冊本身有錯，要回頭找人事，不是在 pandas 裡挑一列。

### 驗收

- 交出「合併前後列數」表：至少包含天真合併與依有效期間合併兩列，每列有**預測**、實際、差異與原因。
- 預測要在執行 `merge` **之前**由鍵的出現次數算出（可用 `predict_rows()` 或自己寫），不是把實際列數抄進預測欄；預測與實際一致，不一致時說明你的預測漏了什麼。
- 每個承攬商的事件數加總等於 2454、違規加總等於 419（用 `assert` 寫出來）。
- 能說出為什麼 `roster.drop_duplicates("worker_id")` 讓 `validate` 通過，卻是錯的。
- AI 版本至少指出兩個錯，並說明哪一個會讓數字變大、哪一個會讓數字變小。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，Demo **標準輸出逐字相同**（含 `MergeError` 第一行訊息）；Workshop 參考判讀的數字兩版相同。

> 撰寫時踩到的坑（已處理）：`event-types.csv` 有一欄 `is_violation`（字串 `"true"`／`"false"`）；若事件表也先建了同名的布林欄，合併後會變成 `is_violation_x`／`is_violation_y`，後續 `["is_violation"]` 直接 `KeyError`。Demo 把事件表的布林欄改名為 `violation`。合併前檢查兩邊有沒有同名的非鍵欄位，是值得教的習慣。

**資料**：同第 12 節，合成資料，不代表任何真實工地或承攬商。`dashboard-export.csv` 與 `events.jsonl` 第 1 週（`event_time` 早於 2026-09-07）692 筆一對一對上、六欄一致（教師以 Demo 第 6 段實測）。區域中文名對照取自 `data/events/MANIFEST.json` 的 `zones`。條文取自練習站 `articles.jsonl`，可能經刻意修改，不具法律效力。

**界線**：本節的有效期間合併用「先 fan-out 再篩選」，在名冊 61 列、事件 2818 列時沒有問題；名冊很大、每人很多段期間時，中間結果會很大，那時改用 `pd.merge_asof`（依時間取最近的一列）或在資料庫做。`merge_asof` 本節**沒有實測**，不展開。`right` join 只是 `left` 換邊，本節不另外示範。本節**尚未實班試教**。

**與機器學習課的對齊**：ML 課第 02 節的「事件彙總表」若要帶承攬商、工種等名冊欄位，必須用本節 `attach_roster()` 的有效期間合併；用 `worker_id` 直接接，W023 的事件會重複，切訓練／測試集時同一筆事件可能**同時出現在兩邊**（ML 課第 03 節的洩漏）。此項提醒需 ML 課撰寫者確認是否納入。

**舊教材**：改寫並大幅擴充自 [DataFrame 合併與操作](https://hackmd.io/@yillkid/SJENzeiEc)。保留 `concat` 上下接與 `ignore_index=True`，情境（兩台攝影機的事件接起來）改為「事件表 vs. 儀表板匯出」，並示範欄名不同時的 NaN 與「同一批事件不該 concat」。`subtract` 刪除（第 13 節教師紀錄已說明）。`merge` 的 `how`、`validate`、`indicator`、fan-out、有效期間合併、三方合併、合併前後列數表皆為新增——舊版全課 `merge` 僅 1 次。

**下一節**：第 15 節〈濃縮：LLM 不該看到三萬筆〉——現在每一筆違規都接上了人、承攬商與法條原文，表變得又寬又長。下一節決定哪些東西真的要進 LLM 的 context，而且每一列摘要都要能追回這裡的 `event_id`。
