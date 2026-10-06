# 05｜一筆事件 = 一列；欄位是 schema

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 05 節：一筆事件 = 一列；欄位是 schema。**
> 本節用工地 AI 攝影機的事件檔，看「一個事件一個 DataFrame」與「迴圈裡一列一列 `concat`」這兩種寫法錯在哪裡，再把同一批事件一次變成一張表、一次 `groupby`。順帶處理 index 最常見的兩個誤用：`groupby` 之後忘了 `reset_index`，以及拿一個「以為唯一」的欄位當 index。
> 本節不是 DataFrame API 導覽，也不是 Python list／dict 複習——二維陣列只拿來當五分鐘暖身。讀檔的立場（不讓 pandas 猜型別）沿用第 02、03 節。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 範例程式碼

- [demo：05_event_row.py](https://github.com/4-learn/data-analysis-and-process-demo/blob/master/2026/05_event_row.py)（與本頁 Demo 逐字相同）
- 練習資料與環境說明：[2026/README](https://github.com/4-learn/data-analysis-and-process-demo/tree/master/2026)

## 學習目標與時間

完成後，你能：看一段累積事件的程式碼，指出「這種寫法之後為什麼沒辦法 `groupby`」；把一批 dict 一次轉成 DataFrame 並做計數；說出 Series 是一欄、`groupby` 的結果為什麼沒有欄位；在把某欄設成 index 前先證明它唯一。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–5 分鐘 | 暖身：容器不是語意 | 二維 list 的欄名是 `0, 1, 2` |
| 5–13 分鐘 | 一個事件一個 DataFrame | 200 個表，15 個 `confidence` 是 `object` |
| 13–21 分鐘 | 迴圈裡 `df = pd.concat([df, row])` | 200 列都叫 `0`；複製 20100 列 |
| 21–27 分鐘 | 一批事件一張表 | 一次 `groupby`，`build_table()` 守住欄位 |
| 27–35 分鐘 | Series 與 index 的誤用 | `KeyError`、欄名 `0`、`event_id` 重複 20 個 |
| 35–50 分鐘 | Workshop：判斷寫法、計數、抓 AI 的錯 | 前 500 筆每區違規次數 |

先修：本課第 03、04 節。環境同第 02 節。

## 一、暖身：容器不是語意

事件檔 `data/events/events.jsonl` 一行一個事件，每個事件 12 個欄位：

```text
event_id, site, zone, camera_id, model_version, worker_id,
event_type, confidence, event_time, ingested_at, handled_at, snapshot
```

把前 3 筆的區域、事件類型、信心度抽成二維 list，再交給 pandas：

```text
== 1. 暖身：容器不是語意 ==
二維 list：[['Z3', 'ppe_ok', 0.7], ['Z1', 'ppe_ok', 0.73], ['Z2', 'no_harness', 0.82]]
pd.DataFrame(二維 list) 的欄名：[0, 1, 2]
pd.DataFrame(list of dict) 的欄名：['event_id', 'site', 'zone', 'camera_id'] …
```

二維 list 是「一格一格的值」，**不知道第 1 格是區域**。pandas 只能給它欄名 `0, 1, 2`；之後 `df[1] == "ppe_ok"` 能跑，但半年後沒有人看得懂。list of dict 每一筆都自帶欄名，**欄名就是 schema**：它說「這一欄叫 `zone`，每一列都有」。

這就是本節唯一需要的「陣列」知識。舊講義花兩篇教巢狀迴圈填 3×4 陣列，對本課沒有幫助。

## 二、一個事件一個 DataFrame

收到事件就包成一個 DataFrame，看起來很「物件導向」：

```python
# 示意，本節測試不涵蓋這段
event1 = pd.DataFrame([records[0]])
event2 = pd.DataFrame([records[1]])
```

拿前 200 筆照做（後面第四段有完整程式）：

```text
== 2. 一個事件一個 DataFrame ==
200 個 DataFrame，各 1 列；confidence 的 dtype：{'float64': 185, 'object': 15}
想數每種事件幾次，只能寫迴圈：{'no_harness': 7, 'no_helmet': 18, 'ppe_ok': 169, 'restricted_entry': 6}
事後 pd.concat(frames)：confidence=object
```

三件事：

1. **沒有 `groupby` 可用。** 200 個表各自只有 1 列，`groupby`、`value_counts`、排序、篩選都要「一批」才有意義。想數每種事件幾次，只能回到 Python 迴圈自己數。
2. **型別是每一列各自猜的。** cam-08 跑舊模型、`confidence` 是 `null`（MANIFEST 記載的「沒記錄」）。只有一列時，pandas 看到一個 `None`，猜不出它該是數字，就給 `object`。200 個表裡有 15 個是這樣。
3. **事後補救也救不回來。** 把 200 個小表 `concat` 起來，`confidence` 是 `object`（pandas 3.0.6 實測；2.3.3 是 `float64`，見教師紀錄）。同一欄的型別取決於「當初怎麼切」，而不是資料本身。

## 三、迴圈裡 `df = pd.concat([df, row])`

AI 最常給的「累積」寫法。舊一點的版本寫 `df = df.append(row)`——`append` 在 pandas 2.0 已移除，pandas 3.0.6 和 2.3.3 都是 `AttributeError: 'DataFrame' object has no attribute 'append'`（教師實測）。於是 AI 改成：

```python
# AI 常見寫法，本節測試不涵蓋這段（完整版是 Demo 的 concat_in_loop()）
df = pd.DataFrame()
for rec in records:
    df = pd.concat([df, pd.DataFrame([rec])])
```

```text
== 3. for 迴圈裡 df = pd.concat([df, row]) ==
200 列；concat 呼叫 200 次，累計複製 20100 列（是列數的 100 倍以上）
index 是 0 的列：200 列；index 唯一嗎？False
looped.loc[0] 拿到 200 列，不是 1 列
迴圈累積的 confidence=object；數值欄 select_dtypes('number')=[]
```

**列數是對的，表是壞的：**

- **慢，而且越來越慢。** `concat` 不會「在尾巴加一列」，它每次都產生一張新表、把目前為止的列全部複製一次：1＋2＋…＋200＝20100 列。列數變 10 倍，複製量變約 100 倍。教師在本機量過：200 筆時比一次 `pd.DataFrame(records)` 慢 100 倍以上（實際倍數每台機器不同，所以不貼秒數；測試裡只斷言「慢 10 倍以上」）。
- **200 列的 index 全是 `0`。** 每個單列表的 index 都是 `0`，`concat` 預設照抄。`looped.loc[0]` 想拿「第一筆」，拿到 200 列。沒有錯誤訊息。
- **`confidence` 變成 `object`**，`select_dtypes("number")` 一欄都找不到。第 06 節的 `describe()` 會因此把它當文字欄處理。

「加 `ignore_index=True` 就好了」——index 會修好，但「每次複製整張表」和「型別逐列猜」兩件事都還在。**正確做法不是修迴圈，是不要在迴圈裡長出 DataFrame。**

## 四、一批事件一張表

先把事件收進 list（Python 的 list `append` 很便宜），**最後一次**轉成 DataFrame。`build_table()` 再多做一件事：每一筆的欄位必須剛好是 12 個 schema 欄位，少一個或多一個就停。欄位是契約，不是「有就放、沒有就算了」。

以下為完整 `05_event_row.py`，只讀 `data/events/events.jsonl`，不寫檔、不連線。

<!-- demo: 05_event_row.py -->
```python
"""第 05 節：一筆事件是一列，欄位是 schema；不要一個事件一個 DataFrame。"""

import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
EVENTS = DATA / "events" / "events.jsonl"
SCHEMA = ["event_id", "site", "zone", "camera_id", "model_version", "worker_id",
          "event_type", "confidence", "event_time", "ingested_at", "handled_at", "snapshot"]


def load_records(path, n=None):
    """讀 JSONL 成 list of dict（還不是 DataFrame）。n=None 讀全部。"""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[:n]]


def build_table(records):
    """一批事件 → 一張表。欄位是契約：每一筆的欄位都要剛好是 SCHEMA，否則停下來。"""
    for i, rec in enumerate(records):
        missing = [c for c in SCHEMA if c not in rec]
        extra = [c for c in rec if c not in SCHEMA]
        if missing or extra:
            raise ValueError(f"第 {i} 筆欄位不符 schema：缺少 {missing}，多出 {extra}")
    return pd.DataFrame(records, columns=SCHEMA)


def concat_in_loop(records):
    """反模式：for 迴圈裡 df = pd.concat([df, row])。回傳 (df, concat 次數, 累計複製列數)。"""
    df, calls, copied = pd.DataFrame(), 0, 0
    for rec in records:
        df = pd.concat([df, pd.DataFrame([rec])])
        calls += 1
        copied += len(df)          # 每次 concat 都產生一張新表，把目前為止的列全部複製一次
    return df, calls, copied


def index_by_event_id(df):
    """把 event_id 當 index 之前，先確定它真的唯一；不唯一就停下來，並說出是哪幾個。"""
    dup = df["event_id"].duplicated(keep=False)
    if dup.any():
        ids = df.loc[dup, "event_id"].unique()
        raise ValueError(f"event_id 重複：{len(ids)} 個 id 共 {int(dup.sum())} 列，例如 {ids[0]}")
    return df.set_index("event_id")


if __name__ == "__main__":
    records = load_records(EVENTS, 200)

    print("== 1. 暖身：容器不是語意 ==")
    grid = [[r["zone"], r["event_type"], r["confidence"]] for r in records[:3]]
    print(f"二維 list：{grid}")
    print(f"pd.DataFrame(二維 list) 的欄名：{pd.DataFrame(grid).columns.tolist()}")
    print(f"pd.DataFrame(list of dict) 的欄名：{pd.DataFrame(records[:3]).columns.tolist()[:4]} …")

    print("\n== 2. 一個事件一個 DataFrame ==")
    frames = [pd.DataFrame([r]) for r in records]
    kinds = pd.Series([str(f["confidence"].dtype) for f in frames]).value_counts()
    print(f"{len(frames)} 個 DataFrame，各 {frames[0].shape[0]} 列；confidence 的 dtype：{kinds.to_dict()}")
    counts = {}
    for f in frames:                                   # 沒有 groupby 可用，只能自己數
        t = f["event_type"].iloc[0]
        counts[t] = counts.get(t, 0) + 1
    print(f"想數每種事件幾次，只能寫迴圈：{dict(sorted(counts.items()))}")
    print(f"事後 pd.concat(frames)：confidence={pd.concat(frames, ignore_index=True)['confidence'].dtype}")

    print("\n== 3. for 迴圈裡 df = pd.concat([df, row]) ==")
    looped, calls, copied = concat_in_loop(records)
    print(f"{len(looped)} 列；concat 呼叫 {calls} 次，累計複製 {copied} 列（是列數的 {copied // len(looped)} 倍以上）")
    print(f"index 是 0 的列：{int((looped.index == 0).sum())} 列；index 唯一嗎？{looped.index.is_unique}")
    print(f"looped.loc[0] 拿到 {len(looped.loc[0])} 列，不是 1 列")
    print(f"迴圈累積的 confidence={looped['confidence'].dtype}；"
          f"數值欄 select_dtypes('number')={looped.select_dtypes('number').columns.tolist()}")

    print("\n== 4. list of dict → DataFrame，一次 groupby ==")
    df = build_table(records)
    print(f"{df.shape[0]} 列 × {df.shape[1]} 欄；index 唯一嗎？{df.index.is_unique}；"
          f"confidence={df['confidence'].dtype}，缺值 {int(df['confidence'].isna().sum())} 筆")
    print(df.groupby("event_type").size().to_string())

    print("\n== 5. Series 就是一欄；groupby 的結果也是 Series ==")
    print(f"df['confidence'] 是 {type(df['confidence']).__name__}，dtype={df['confidence'].dtype}")
    print(f"df.iloc[0]（一列）也是 {type(df.iloc[0]).__name__}，但 dtype={df.iloc[0].dtype}——一列裡混了字串和數字")
    by = df.groupby(["zone", "event_type"]).size()
    print(f"groupby 結果：{type(by).__name__}，index={list(by.index.names)}，欄位？沒有")
    try:
        by["event_type"]
    except KeyError as exc:
        print(f"by['event_type'] → KeyError: {exc}")
    print(f"忘了 name：reset_index() 的欄名 {by.reset_index().columns.tolist()}")
    print(by.reset_index(name="次數").head(4).to_string(index=False))

    print("\n== 6. 用 event_id 當 index：先確定它唯一 ==")
    full = build_table(load_records(EVENTS))
    by_id = full.set_index("event_id")
    dup = full["event_id"].duplicated(keep=False)
    print(f"全檔 {len(full)} 列，event_id 不同值 {full['event_id'].nunique()} 個；index 唯一嗎？{by_id.index.is_unique}")
    first = full.loc[dup, "event_id"].iloc[0]
    print(f"by_id.loc[{first!r}] 拿到 {type(by_id.loc[first]).__name__} {by_id.loc[first].shape}，不是一列")
    try:
        index_by_event_id(full)
    except ValueError as exc:
        print(f"index_by_event_id() → ValueError: {exc}")
```

執行（在本目錄下）：

```bash
python3 05_event_row.py
```

第四段輸出：

```text
== 4. list of dict → DataFrame，一次 groupby ==
200 列 × 12 欄；index 唯一嗎？True；confidence=float64，缺值 15 筆
event_type
no_harness            7
no_helmet            18
ppe_ok              169
restricted_entry      6
```

同樣 200 筆、同樣 15 個 `null`：**一次轉換時，pandas 看到的是一整欄**，185 個數字加 15 個缺值，於是 `float64`、缺值是 `NaN`。計數結果和第二段的手寫迴圈一樣——差別是這裡一行、而且接下來 `groupby`、篩選、排序都能直接用。

`confidence` 讀成 `float64` 是因為 JSON 裡它本來就是數字；文字欄位全部原樣保留成字串（`worker_id == ""` 是「辨識不到臉」，不是缺值，第 08 節再談）。

## 五、Series 就是一欄；index 的兩個誤用

```text
== 5. Series 就是一欄；groupby 的結果也是 Series ==
df['confidence'] 是 Series，dtype=float64
df.iloc[0]（一列）也是 Series，但 dtype=object——一列裡混了字串和數字
groupby 結果：Series，index=['zone', 'event_type']，欄位？沒有
by['event_type'] → KeyError: 'event_type'
忘了 name：reset_index() 的欄名 ['zone', 'event_type', 0]
zone event_type  次數
  Z1  no_helmet   9
  Z1     ppe_ok  53
  Z2 no_harness   5
  Z2  no_helmet   4
```

- **一欄是 Series，型別一致。** `df["confidence"]` 全是浮點數，可以比大小、算平均。
- **一列也是 Series，但型別是 `object`。** 一列裡有 `event_id`（字串）也有 `confidence`（數字），只好用最寬的型別裝。這就是「欄位是 schema」的反面：**型別屬於欄，不屬於列**。用 `iterrows()` 一列一列處理事件，就是一直在處理 `object`。
- **`groupby(...).size()` 的結果是 Series，分組鍵在 index 裡，不在欄位裡。** 直接 `by["event_type"]` 會 `KeyError`。要接著篩選、合併、存檔，先 `reset_index()`。
- **忘了給 `name`，計數欄就叫 `0`**（整數，不是字串 `"0"`）。之後 `df["0"]` 找不到、存成 CSV 欄名是 `0`。寫 `reset_index(name="次數")`。

最後一個誤用：**拿「以為唯一」的欄位當 index。**

```text
== 6. 用 event_id 當 index：先確定它唯一 ==
全檔 2838 列，event_id 不同值 2818 個；index 唯一嗎？False
by_id.loc['cam-05-20260910-0016'] 拿到 DataFrame (2, 11)，不是一列
index_by_event_id() → ValueError: event_id 重複：20 個 id 共 40 列，例如 cam-05-20260910-0016
```

`event_id` 名字裡有「id」，看起來是主鍵。但 cam-05 在 09-10 斷線、隔天補傳時**同一批送了兩次**（MANIFEST 記載），20 個 id 各出現兩次。`set_index("event_id")` 不會報錯；之後 `by_id.loc[某個 id]` 有時拿到一列（Series），有時拿到兩列（DataFrame），**同一行程式回傳的型別看資料而定**。

`index_by_event_id()` 在設 index 前先檢查，重複就停並報出例子。這 20 筆該怎麼處理（留第一筆？留最晚收到的？）是第 08、09 節的判斷；這裡只要求：**不要讓 index 假裝它是唯一的。**

> pandas 有 `set_index(..., verify_integrity=True)` 會做同樣檢查，但 pandas 3.0.6 對這個參數發出 `Pandas4Warning`（將移除），建議改查 `index.is_unique`（教師實測）。所以 Demo 自己寫。

## Workshop：判斷寫法，然後一次計數

### 任務與時間

**35–40 分鐘：判斷兩種寫法。** 同事交來兩段程式，都要「統計前 500 筆事件中，未戴安全帽（`no_helmet`）有幾次」：

```python
# 寫法 A——Workshop 題目，本節測試不涵蓋這段
frames = [pd.DataFrame([r]) for r in load_records(EVENTS, 500)]
n = sum(f["event_type"].iloc[0] == "no_helmet" for f in frames)

# 寫法 B
df = build_table(load_records(EVENTS, 500))
n = (df["event_type"] == "no_helmet").sum()
```

兩個 `n` 一樣嗎？如果下一個需求是「每個區域各幾次違規」，哪一種改得動？用一句話說明 A **之後為什麼沒辦法 `groupby`**。

**40–45 分鐘：一次計數。** 用寫法 B 的 `df`，算出前 500 筆中「每個區域的違規事件數」（違規＝`event_type != "ppe_ok"`），結果要是一張有欄名的表（`zone`、`次數`）。再算「違規次數最多的 `worker_id`」，看看第一名是誰。

**45–50 分鐘：抓 AI 的錯。** 請 OpenCode 寫「逐行讀 `events.jsonl`，把每一筆累積到 DataFrame，最後統計每種事件幾次」。拿它的程式驗收：

| 檢查 | 怎麼確認 |
| --- | --- |
| 跑得起來嗎？ | 有 `df.append` 就會 `AttributeError` |
| 計數對嗎？ | 與 `build_table()` 版比較 |
| index 唯一嗎？ | `df.index.is_unique` |
| `confidence` 是數字嗎？ | `df["confidence"].dtype` |
| 有沒有在迴圈裡 `concat`？ | 讀程式 |

### 參考判讀

- 兩個 `n` 都是 **44**（教師實測）。答案一樣，所以「結果對」不能用來判斷寫法對。A 的每個表只有 1 列，「每個區域各幾次」只能再寫一個字典迴圈；B 是 `df[df["event_type"] != "ppe_ok"].groupby("zone").size()` 一行。**A 之後沒辦法 `groupby`，因為 `groupby` 要在「同一張表的同一欄」裡分組，而 A 的事件散在 500 張表裡。**
- 前 500 筆（2026-08-31 07:04～09-04 10:17）每區違規數：Z1 18、Z2 22、Z3 30、Z4 14，合計 84（教師實測）。用 `.reset_index(name="次數")` 才會得到 `zone`、`次數` 兩欄；只寫 `.reset_index()` 計數欄叫 `0`。
- 「違規次數最多的 `worker_id`」若直接 `groupby("worker_id").size()` 取最大，**第一名是空字串 `""`，14 次**——那是 14 筆辨識不到臉的違規，不是一個人。排除空字串後是 W018、W029 各 7 次（並列），W020 4 次。能指出「第一名不是人」比算對數字重要；並列怎麼處理是第 07 節的題目。
- AI 版本常見兩種：舊的 `df.append(row)` 在 pandas 3.0.6 直接 `AttributeError`；新的 `pd.concat([df, row])` 跑得動，前 500 筆 `no_helmet` 一樣 44 次，但 `index.is_unique` 是 `False`（500 列都叫 `0`），pandas 3.0.6 下 `confidence` 是 `object`。**計數對、表是壞的**——下一個需求才會爆。
- 若 AI 版本有 `ignore_index=True`，index 是好的；仍要指出它在迴圈裡複製整張表。修法是把 dict 收進 list、迴圈外一次 `pd.DataFrame(list)`。

### 驗收

- 能重現第四至六段輸出。
- 用一句話說出寫法 A「之後為什麼無法 `groupby`」。
- 每區違規數 Z1 18、Z2 22、Z3 30、Z4 14，且結果欄名是 `zone`、`次數`（不是 `0`）。
- 指出 `worker_id == ""` 不是一個人。
- AI 驗收表五列都有結論；若 AI 版本有迴圈 `concat`，寫出改法。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，差別兩行，皆在第二、三段：

- `事後 pd.concat(frames)：confidence=object` 在 2.3.3 是 `float64`；
- `迴圈累積的 confidence=object；數值欄 select_dtypes('number')=[]` 在 2.3.3 是 `float64`、`['confidence']`。

原因：2.3.3 在 concat 時會略過「全是缺值」的單列表來決定型別（並發 `FutureWarning`，說未來版本不再略過）；3.0.6 已改成不略過，於是 `None` 讓整欄變 `object`。**這正是「型別取決於當初怎麼切」的例子：同一份程式，換 pandas 版本型別就不同**；一次 `pd.DataFrame(records)` 兩版都是 `float64`。測試以 `PANDAS2_DIFFS` 精確替換這兩行。另 2.3.3 的 `df.append` 同樣不存在。

「慢 N 倍」：教師在本機以 `time.perf_counter` 量 200 筆，迴圈 `concat` 比一次轉換慢約 270 倍（3.0.6）／約 200 倍（2.3.3）；800 筆約 490／365 倍（單次量測）。秒數與倍數隨機器變動，**不貼進輸出**；`test_lesson_05.py` 只斷言 200 筆「慢 10 倍以上」。穩定的證據是「累計複製 20100 列」。

**資料**：`data/events/events.jsonl` 前 200 筆（2026-08-31 07:04 起），由 `tools/build_events.py` 以固定種子產生，雜湊記於 `data/events/MANIFEST.json`。全部為合成資料，人員、事件皆虛構，不代表任何真實工地統計。

**界線**：本節不談 `iterrows`／`apply` 的效能（第 13 節）、不處理重複 `event_id` 該留哪一筆（第 08、09 節）、不教 MultiIndex——遇到 `groupby` 多鍵結果一律 `reset_index(name=...)` 攤平。本節**尚未實班試教**。

**舊教材**：濃縮合併 [DataFrame 初體驗](https://hackmd.io/@yillkid/SkhiueRH-l)、[DataFrame Basic](https://hackmd.io/@yillkid/Sylb42oN5)、[一個 event = DataFrame 的一列](https://hackmd.io/@yillkid/SJLW-FU4-g)、[欄位設計](https://hackmd.io/@yillkid/BJcbT2LEbg)、[Series](https://hackmd.io/@yillkid/H16l3-EJq)，暖身取自 [Python 二維陣列](https://hackmd.io/@yillkid/rkeBxdxzZe)、[Python Multi-List](https://hackmd.io/@yillkid/H1idoAcN9)。保留：「一個 event = 一列」「欄位是資料契約」「一列也是 Series」「index 不是分類工具」四個核心主張，以及「寫法 A／B 判斷」的 Workshop 題型（改用真實事件檔，並加上一次計數與 AI 驗收）。刪除：手打 dict literal 的範例、`to_string` 小節、`timestamp/person/event/value` 四欄最小 schema（本課事件檔已有 12 欄真實 schema）、二維陣列巢狀迴圈與 4×4 座位表 Workshop（含 `input()` 互動）。Series 篇的 `pd.to_numeric(errors="coerce")` 清洗移到第 08 節（那裡要談它安靜丟資料）。舊版「`object` dtype 不能做數值判斷」的說法保留其意、改寫成「型別屬於欄，不屬於列」；pandas 3 的文字欄已是 `str`，不再教「文字欄就是 `object`」。

**下一節**：第 06 節〈五分鐘探索法〉——拿到一份沒見過的廠商匯出檔，五分鐘內說出它能不能用。本節第三段那欄被弄成 `object` 的 `confidence`，下一節會以另一種面貌出現：`"87%"`。
