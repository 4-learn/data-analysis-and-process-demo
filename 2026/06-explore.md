# 06｜五分鐘探索法：這份資料能不能用？

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 06 節：五分鐘探索法：這份資料能不能用？**
> 本節拿一份你沒見過的廠商儀表板匯出檔，用 `shape`／`columns`／`dtypes`／`info`／`describe`／`value_counts`／`isna` 照固定順序看一遍，五分鐘內說出：它有什麼、哪裡會騙你、缺了什麼、缺得有沒有規律。
> 本節不是 EDA 或視覺化課——不畫圖、不找洞察、不下工地安全結論。也不做清理：清理是第 08 節的判斷，本節只負責在動手之前**把現況看清楚、寫下來**。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：拿到一份陌生 CSV，五分鐘內交出「已確認的觀察」與「目前不能回答的問題」，並區分哪些是觀察、哪些是推測；指出 `describe()` 什麼時候什麼都沒告訴你；在決定怎麼處理缺值之前，先說出缺值分布在哪裡。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–5 分鐘 | 情境：廠商丟來一份匯出檔 | 探索順序：先結構、後內容、最後缺值 |
| 5–12 分鐘 | 先看結構 | 692 × 7，七欄全是 `str` |
| 12–18 分鐘 | `describe()` 預設只摘要數值欄 | 這份檔一個數值欄都沒有 |
| 18–25 分鐘 | 數字被讀成字串、誰被當成缺值 | `"87%"`、`"N/A"` 會變 NaN、`"未辨識"` 不會 |
| 25–35 分鐘 | 缺值分布先於處理決策 | 63 個 N/A 全在 cam-08；`dropna` 砍掉施工架一半 |
| 35–50 分鐘 | Workshop：五個觀察、三個問題 | 一頁探索報告 |

先修：本課第 02、05 節。互動探索建議用 `python -i 06_explore.py`（跑完留在直譯器裡，`naive`、`raw` 都還在）或 IPython；不用 notebook。

## 一、情境：廠商丟來一份匯出檔

工地主任從 AI 攝影機廠商的儀表板按了「匯出」，寄給你 `data/events/dashboard-export.csv`：「第一週的資料，看看能不能用。」

你**沒有**這份檔的欄位說明，也還不知道它跟第 05 節的 `events.jsonl` 是什麼關係。「能不能用」不是一個感覺，而是幾個能回答的問題：

| 順序 | 看什麼 | 工具 | 回答 |
| --- | --- | --- | --- |
| 1 | 結構 | `shape`、`columns`、`dtypes`、`info()` | 幾列幾欄？每欄是什麼型別？ |
| 2 | 內容 | `describe()`、`value_counts()`、`min`／`max` | 值長什麼樣？有幾種？範圍多大？ |
| 3 | 缺值 | `isna()`、可疑字串計數、依其他欄分組 | 缺多少？缺在哪裡？有沒有規律？ |

**先結構、後內容、最後缺值**，而且每一步都只看、不改。看到問題就記下來，不要邊看邊修——邊看邊修的結果，是你最後說不清楚原始檔長什麼樣。

## 二、先看結構

AI 給的第一步通常是一行 `read_csv` 加 `head()`。`head()` 只給你前 5 列，**它長得正常不代表整份正常**。先看整體（後面第五段有完整程式）：

```text
== 1. 先看結構：一行 read_csv 之後 ==
shape=(692, 7)
columns=['事件編號', '區域', '攝影機', '人員', '事件', '信心度', '發生時間']
dtypes：{'str': 7}
info()：5   信心度     629 non-null    str
info()：dtypes: str(7)
```

- **692 列 × 7 欄**，中文欄名。檔案開頭有 UTF-8 BOM，pandas 的 UTF-8 解碼會吃掉它，第一個欄名是乾淨的 `事件編號`（第 02 節講過）。
- **七欄全是 `str`。** 「信心度」聽起來是數字、「發生時間」聽起來是時間，pandas 都沒有這樣認為。
- `info()` 的 Non-Null Count：其他欄都是 692，**只有「信心度」是 629**——有 63 筆被當成缺值。是什麼被當成缺值？第四段回答。

（完整的 `info()` 會列出七欄，這裡只挑出「信心度」那行與最後一行；Demo 的 `info_lines()` 做的就是這件事。）

## 三、`describe()` 預設只摘要數值欄——這份一欄都沒有

`describe()` 的預設行為是「只摘要數值欄」。那一個數值欄都沒有的時候呢？

```text
== 2. describe() 預設只摘要數值欄——這份一欄都沒有 ==
         區域     攝影機   人員     事件  信心度
count   692     692  692    692  629
unique    4       8   53      4   59
top     出入口  cam-01  未辨識  防護具正確  80%
freq    232     120   92    575   23
describe(include='number') → ValueError
```

實測 pandas 3.0.6：**全部是字串欄時，`describe()` 退回「文字摘要」**——`count`／`unique`／`top`／`freq`，沒有平均、沒有標準差、沒有最大最小值。如果你預期看到 `mean`，它不會報錯，只是**安靜地給你另一種表**。明確要求 `include="number"` 才會報 `ValueError`。

（為了版面，上表拿掉了「事件編號」與「發生時間」兩欄；它們的 `unique` 分別是 692 與 616。）

這張文字摘要其實很有用，只是要會讀：

- **區域 4 種、攝影機 8 台、事件 4 種**：跟第 05 節事件檔的結構一致（4 區、每區 2 台）。
- **人員 53 種，最常見的是「未辨識」，92 次。** 一個「人」出現最多次，而它不是人。
- **信心度 59 種、最常見 `"80%"`**——這是字串的眾數，不是數值的眾數。看到 `%` 就知道它不會被當數字。

## 四、數字被讀成字串；誰被當成缺值

```text
== 3. 數字被讀成字串 ==
信心度.mean() → TypeError
pd.to_numeric(errors='coerce')：692 筆裡 692 筆變 NaN，平均=nan
字串比大小：最小 '35%'，最大 '99%'，'5%' > '10%' 是 True
```

三種「看起來能用」的處理，三種結果：

1. **`mean()` 報錯**——最好的情況，你知道有問題。
2. **`pd.to_numeric(errors="coerce")`：692 筆全部變 NaN，沒有錯誤。** 這是 AI 很常給的「修正」。`"87%"` 不是數字，`coerce` 就把它換成 NaN；整欄變 NaN，平均是 `nan`，程式照樣往下跑。
3. **字串比大小**：最小 `'35%'`、最大 `'99%'`，**剛好對**——因為這份檔的信心度剛好都是兩位數（35%～99%）。`'5%' > '10%'` 是 `True`：字串是一個字一個字比的，`'5'` 大於 `'1'`。哪天出現個位數或 `100%`，排序就錯了，而且不會報錯。看起來沒問題，可能只是這份資料剛好沒踩到——跟第 02、03 節同一件事。

再來是 `info()` 裡那 63 筆：

```text
== 4. 哪些字被當成缺值：'N/A' 會，'未辨識' 不會 ==
預設讀法 isna()：{'信心度': 63}；人員=='未辨識' 92 筆
同一套預設規則：{'N/A': True, 'NA': True, 'n/a': True, 'null': True, 'NULL': True, 'None': True, 'nan': True, '-': False, '未辨識': False, '無': False}
read_raw()：isna 合計 0；各欄可疑字串：
     ''  'N/A'  '未辨識'  '-'
人員    0      0     92    0
信心度   0     63      0    0
```

- `read_csv` 預設有一張「這些字串代表缺值」的清單：`N/A`、`NA`、`n/a`、`null`、`NULL`、`None`、`nan`、空欄位等（前七個上面逐一實測；空欄位教師另測，同樣變 NaN）。**`信心度 == "N/A"` 的 63 筆因此變成 NaN。**
- **`"未辨識"`、`"-"`、`"無"` 不在清單上**，保持原樣。所以「人員」欄 `isna()` 是 0——但有 92 筆是「辨識不到臉」。
- 同樣是「這格沒有正常的值」，**一個被 pandas 算成缺值，一個沒有。決定它的是那張清單，不是資料的意思。** 只看 `isna()` 的人會說「人員欄沒有缺值」。

探索時改用 `read_raw()`：`dtype=str, keep_default_na=False`（第 02 節的讀法），**沒有任何東西被換成 NaN**（`isna` 合計 0），再自己數可疑字串。這張表才是這份檔真正的缺值樣貌：信心度 63 個 `N/A`、人員 92 個 `未辨識`、沒有空字串。

## 五、缺值分布先於處理決策

知道「缺多少」還不夠，要知道「缺在哪裡」。

以下為完整 `06_explore.py`，只讀 `data/events/dashboard-export.csv`，不寫檔、不連線。

<!-- demo: 06_explore.py -->
```python
"""第 06 節：五分鐘探索法——拿到一份沒見過的匯出檔，先看結構、再看內容、最後看缺值。"""

import io
import re
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
EXPORT = DATA / "events" / "dashboard-export.csv"
PERCENT = re.compile(r"\d{1,3}%")


def read_raw(path):
    """探索用的讀法：全部當字串、不替你把任何字換成 NaN。"""
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def info_lines(df, keys):
    """df.info() 印給人看；這裡只挑出含 keys 的幾行（去掉行尾空白）。"""
    buf = io.StringIO()
    df.info(buf=buf)
    return [line.strip() for line in buf.getvalue().splitlines() if any(k in line for k in keys)]


def token_counts(df, tokens):
    """每個「看起來像缺值」的字串，在每一欄出現幾次。只列出有出現的。"""
    table = pd.DataFrame({repr(t): (df == t).sum() for t in tokens})
    return table[table.sum(axis=1) > 0]


def parse_confidence(s):
    """'87%' → 0.87；'N/A' → NaN；其他任何寫法都停下來，不猜。"""
    ok = s.str.fullmatch(PERCENT.pattern) | (s == "N/A")
    if not ok.all():
        bad = s[~ok]
        raise ValueError(f"信心度有無法解讀的值 {len(bad)} 筆，例如 {bad.iloc[0]!r}")
    value = pd.to_numeric(s.where(s != "N/A").str.removesuffix("%")) / 100
    if (value > 1).any():
        raise ValueError(f"信心度超過 100% 有 {int((value > 1).sum())} 筆")
    return value


if __name__ == "__main__":
    print("== 1. 先看結構：一行 read_csv 之後 ==")
    naive = pd.read_csv(EXPORT)
    print(f"shape={naive.shape}")
    print(f"columns={naive.columns.tolist()}")
    print(f"dtypes：{naive.dtypes.astype(str).value_counts().to_dict()}")
    for line in info_lines(naive, ["信心度", "dtypes:"]):
        print(f"info()：{line}")

    print("\n== 2. describe() 預設只摘要數值欄——這份一欄都沒有 ==")
    print(naive.drop(columns=["事件編號", "發生時間"]).describe().to_string())
    try:
        naive.describe(include="number")
    except ValueError as exc:
        print(f"describe(include='number') → {type(exc).__name__}")

    print("\n== 3. 數字被讀成字串 ==")
    try:
        naive["信心度"].mean()
    except TypeError as exc:
        print(f"信心度.mean() → {type(exc).__name__}")
    coerced = pd.to_numeric(naive["信心度"], errors="coerce")
    print(f"pd.to_numeric(errors='coerce')：{len(coerced)} 筆裡 {int(coerced.isna().sum())} 筆變 NaN，平均={coerced.mean()}")
    text = naive["信心度"].dropna()
    print(f"字串比大小：最小 {text.min()!r}，最大 {text.max()!r}，'5%' > '10%' 是 {'5%' > '10%'}")

    print("\n== 4. 哪些字被當成缺值：'N/A' 會，'未辨識' 不會 ==")
    print(f"預設讀法 isna()：{naive.isna().sum()[lambda s: s > 0].to_dict()}；人員=='未辨識' {int((naive['人員'] == '未辨識').sum())} 筆")
    probe = pd.read_csv(io.StringIO("v\nN/A\nNA\nn/a\nnull\nNULL\nNone\nnan\n-\n未辨識\n無\n"))
    print(f"同一套預設規則：{dict(zip(['N/A', 'NA', 'n/a', 'null', 'NULL', 'None', 'nan', '-', '未辨識', '無'], probe['v'].isna()))}")
    raw = read_raw(EXPORT)
    print(f"read_raw()：isna 合計 {int(raw.isna().sum().sum())}；各欄可疑字串：")
    print(token_counts(raw, ["", "N/A", "未辨識", "-"]).to_string())

    print("\n== 5. 缺值分布先於處理決策 ==")
    na = raw["信心度"] == "N/A"
    print(f"信心度 N/A 依攝影機：{raw.loc[na, '攝影機'].value_counts().to_dict()}；cam-08 全部 {int((raw['攝影機'] == 'cam-08').sum())} 筆")
    unknown = raw["人員"] == "未辨識"
    print(f"人員 未辨識 依區域：{raw.loc[unknown, '區域'].value_counts().sort_index().to_dict()}")
    conf = parse_confidence(raw["信心度"])
    print(f"parse_confidence()：{conf.notna().sum()} 筆數值，範圍 {conf.min()}～{conf.max()}，平均 {conf.mean():.3f}；補 0 後平均 {conf.fillna(0).mean():.3f}")
    kept = raw[conf.notna()]
    zone = pd.DataFrame({"全部": raw["區域"].value_counts(), "dropna 後": kept["區域"].value_counts()})
    zone["違規（全部）"] = raw.loc[raw["事件"] != "防護具正確", "區域"].value_counts()
    zone["違規（dropna 後）"] = kept.loc[kept["事件"] != "防護具正確", "區域"].value_counts()
    print(zone.to_string())

    print("\n== 6. 轉好型別之後，describe 才有東西 ==")
    print(raw.assign(信心度=conf).describe().round(3).to_string())
    day = raw["發生時間"].str[:10].value_counts().sort_index()
    print(f"發生時間 {raw['發生時間'].min()}～{raw['發生時間'].max()}；每天筆數 {day.to_dict()}")
```

執行（在本目錄下）：

```bash
python3 06_explore.py        # 或 python -i 06_explore.py，跑完留在直譯器繼續探索
```

第五段輸出：

```text
== 5. 缺值分布先於處理決策 ==
信心度 N/A 依攝影機：{'cam-08': 63}；cam-08 全部 63 筆
人員 未辨識 依區域：{'出入口': 24, '施工架': 20, '鋼構組立': 28, '開挖區': 20}
parse_confidence()：629 筆數值，範圍 0.35～0.99，平均 0.774；補 0 後平均 0.704
       全部  dropna 後  違規（全部）  違規（dropna 後）
區域                                       
出入口   232       232      26            26
開挖區   188       188      38            38
鋼構組立  157       157      32            32
施工架   115        52      21            14
```

讀它的方式：

- **63 個 `N/A` 全部來自 cam-08，而 cam-08 的 63 筆全部是 `N/A`。** 缺值不是隨機散落，是「一台攝影機完全沒有這個欄位」。這是**觀察**。「cam-08 的設備或模型不輸出信心度」是**推測**——這份匯出檔裡沒有任何欄位能證實它（第 05 節的事件檔有 `model_version`，那是另一份資料）。
- **「未辨識」四個區域都有**（20～28 筆），不像 `N/A` 那樣集中在一處。它跟信心度的 `N/A` 是不同性質的缺。
- **補 0 會把平均從 0.774 拉到 0.704**：63 筆「沒記錄」被當成「信心度 0%」。
- **`dropna()` 刪掉的不是 63 筆「壞資料」，是施工架一半的事件**：115 → 52；施工架的違規 21 → 14，少了三分之一。如果下一步是「哪個區域違規最多」，施工架被系統性地低估，而且是因為**攝影機型號**，不是因為工地狀況。

所以：**先看分布，再決定怎麼處理。** 這三個選項（補 0、刪掉、保留 NaN）哪個對，取決於「缺值代表什麼」，那是第 08 節的主題。本節只要求你在動手之前，能說出上面這張表。

`parse_confidence()` 是本節唯一的「轉型」：`"87%"` → `0.87`、`"N/A"` → NaN，**其他任何寫法都停下來**（例如 `"87"`、`"0.87"`、`"高"`），而不是像 `errors="coerce"` 那樣安靜變 NaN。轉好之後：

```text
== 6. 轉好型別之後，describe 才有東西 ==
           信心度
count  629.000
mean     0.774
std      0.140
min      0.350
25%      0.670
50%      0.790
75%      0.880
max      0.990
發生時間 2026/08/31 07:04～2026/09/05 16:59；每天筆數 {'2026/08/31': 117, '2026/09/01': 112, '2026/09/02': 126, '2026/09/03': 107, '2026/09/04': 110, '2026/09/05': 120}
```

現在 `describe()` 預設只摘要「信心度」一欄（它是唯一的數值欄），其他六欄被安靜地略過——這次是**另一個方向**的「預設只摘要數值欄」。`count` 是 629 不是 692：`describe()` 的統計自動排除 NaN，表上看不出有 63 筆被排除，要自己跟 `shape` 對照。

時間欄仍是字串，`min`／`max` 能用是因為 `YYYY/MM/DD HH:MM` 這種固定寬度格式的字串順序剛好等於時間順序。範圍 08-31（週一）到 09-05（週六），6 天、每天 107～126 筆。轉成真正的時間是第 10–11 節的事。

## Workshop：五個觀察、三個問題

### 任務與時間

**35–45 分鐘：探索報告。** 用 `python -i 06_explore.py`（或自己從 `read_raw()` 開始），交一份報告：

```text
已確認的觀察（每條附：用哪個指令、看到什麼數字）
1.
2.
3.
4.
5.

目前不能回答的問題（每條附：缺什麼資訊才能回答、該問誰）
1.
2.
3.
```

規則：**觀察**必須是「任何人跑同一個指令都會得到的事實」；凡是「因為…所以…」「應該是…」都是**推測**，要嘛放進問題，要嘛標明「推測」。

**45–50 分鐘：抓 AI 的錯。** 把這份 CSV 丟給 OpenCode，請它「探索這份資料並計算平均信心度與每區違規數」。檢查它的程式：

| 檢查 | 怎麼確認 |
| --- | --- |
| 信心度怎麼轉的？ | `errors="coerce"` 會讓 692 筆全變 NaN；`.str.replace("%", "")` 能用但要檢查 `N/A` 去哪了 |
| 平均信心度是多少？ | 應為 0.774（或 77.4%）、基於 629 筆；若是 0.704 代表補了 0 |
| 有沒有 `dropna()`？ | 每區違規數施工架應為 21；若是 14 代表被 `dropna()` 砍了 |
| 「人員」欄有沒有缺值？ | AI 若只看 `isna()` 會說 0 |
| 報告裡有沒有推測當事實？ | 例如「cam-08 故障」 |

### 參考判讀

可以列為**已確認觀察**的例子（教師實測，皆可由 Demo 或一行指令重現）：

- 692 列 × 7 欄，七欄讀進來都是字串；`事件編號` 692 個不重複。
- 發生時間 2026/08/31 07:04～2026/09/05 16:59，6 天，每天 107～126 筆；檔案依發生時間由早到晚排序（`raw["發生時間"].is_monotonic_increasing` 為 `True`）。
- 4 個區域、8 台攝影機，每區恰好 2 台（`raw.groupby("區域")["攝影機"].nunique()`）。
- 事件 4 種：防護具正確 575、未戴安全帽 61、高處未使用安全帶 33、跨越警示線 23。
- 信心度 629 筆為 `NN%`，範圍 35%～99%；63 筆為 `N/A`，**全部且只有** cam-08。
- 人員 92 筆為「未辨識」，四區都有；其餘 52 個不同的 `W` 編號（W 加三位數字）。

應列為**不能回答的問題**的例子：

- cam-08 為什麼沒有信心度？是設備型號、設定，還是匯出程式的問題？（問廠商；本檔沒有設備型號欄。）
- 「未辨識」的人是誰？同一個人被多次未辨識嗎？（本檔無法回答，可能永遠無法回答。）
- 信心度是什麼的信心度——事件類型判斷，還是人臉辨識？門檻多少才會被記錄？（問廠商。）
- 發生時間是哪個時區？只到分鐘，同一分鐘多筆時誰先誰後？（問廠商；第 10 節會談。）
- 這是全部事件，還是儀表板有篩選過？第一週週日沒有資料，是停工還是沒匯出？

常見把推測寫成觀察的錯：「cam-08 故障」「施工架違規比較少」（`dropna` 之後才會這樣看）、「W018 最常違規」（不排除「未辨識」時，違規次數第一名是「未辨識」22 筆；排除後 W018 10 筆，但「未辨識」裡可能有 W018）。

AI 版本的實測結果：

- `pd.to_numeric(df["信心度"], errors="coerce")`：692 筆全 NaN、平均 `nan`、無錯誤。
- `df["信心度"].astype(float)`：`ValueError: could not convert string to float: '70%'`——會報錯，比 `coerce` 安全。
- `df["信心度"].str.replace("%", "").astype(float)`：得到 63 個 NaN、平均 77.4（百分比單位）。這個能用，因為 `N/A` 在讀檔時已經被預設清單變成 NaN——**它是靠讀檔的副作用才沒報錯**。若改成 `keep_default_na=False` 讀，`"N/A"` 會讓 `astype(float)` 報錯。
- 補 0 後平均 70.35；`df.dropna()` 剩 629 列、施工架 52 列。

### 驗收

- 能重現第五段輸出，說出 63 個 `N/A` 的分布。
- 報告有 5 個觀察、3 個問題；每個觀察附指令與數字；沒有把推測寫成觀察。
- 能說出「`describe()` 在這份檔上為什麼沒有 `mean`」以及「轉型之後為什麼 `count` 是 629」。
- AI 驗收表五列都有結論，並指出至少一個 AI 版本的問題（或證明它都通過）。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行，差別只在第一段三行：字串欄 dtype 顯示為 `object` 而非 `str`（`dtypes：{'object': 7}`、`info()` 該行為 `object`、`dtypes: object(7)`）。測試以 `PANDAS2_DIFFS` 精確替換。

其他版本差異（不在 Demo 輸出中，教師另外實測）：

- `describe(include="number")` 在無數值欄時，兩版都拋 `ValueError`，但訊息不同：3.0.6 為 `No columns match the specified include or exclude data types`，2.3.3 為 `No objects to concatenate`。Demo 只印例外類別。
- 全為字串欄時 `describe()` 的 `top`：若某欄每個值都只出現一次（如「事件編號」），兩版挑出的 `top` 不同（3.0.6 為第一筆，2.3.3 為另一筆）。這是 Demo 把「事件編號」拿掉的原因之一——**並列時的 `top` 不可依賴**。
- `info()` 的 memory usage：3.0.6 印 `38.0 KB`，2.3.3 印 `38.0+ KB`（`object` 欄不深算）。Demo 不印這行。
- 字串欄 `mean()` 兩版都 `TypeError`，訊息不同。Demo 只印例外類別。
- 2.3.3 的 `object` 欄含 NaN 時 `.max()` 會 `TypeError`；Demo 先 `dropna()` 再比，兩版一致。

**資料**：`data/events/dashboard-export.csv` 由 `tools/build_events.py` 產生：第 05 節 `events.jsonl` 中 `event_time` 早於 2026-09-06 的事件、依 `event_id` 去重、依發生時間排序，欄名中文化，`confidence` 轉成百分比字串，null 寫 `N/A`，空 `worker_id` 寫「未辨識」。教師另外核對：692 個事件編號與事件檔第一週去重後的 692 個 id 完全相同，發生時間逐筆一致。**這些是教師知道、學生在本節不該假設知道的事**——Workshop 的「不能回答的問題」正是建立在「只看這份檔」的前提上。全部為合成資料。

**界線**：本節不做清理、不做時間轉換、不跨檔比對。`ydata-profiling` 這類一鍵 EDA 只提一句（教師未在本環境實測）：不論工具多完整，它拿到的都是**讀進來之後**的 DataFrame，讀檔時被換成 NaN 或沒被換的，它無從得知。課綱「待確認事項」中「第 06 節要不要擴」尚未定案，本稿依目前規格只做最小分析。本節**尚未實班試教**。

**舊教材**：無。舊版 `describe` 全課 0 次；本節為新增，沒有可改寫的舊講義。

**下一節**：第 07 節〈欄位選取、布林篩選與 Top-K〉——回到 `events.jsonl`，從「看」走到「挑」：篩出某區某時段的違規、找出違規最多的前三名，以及缺值在比較中為什麼兩邊都不算。
