# 02｜CSV、編碼與多檔讀取

> **正文初稿：2026-10-05｜對應新版資料處理與分析第 02 節：CSV、編碼與多檔讀取。**
> 本節把三份「不同人、不同軟體匯出」的 CSV 讀成同一張表。重點不是記住 `read_csv` 的參數，而是看見：**一行 `read_csv` 會讓 pandas 替你猜型別，而它猜錯的時候不會報錯。**
> 本節不是編碼原理課——UTF-8、BOM、Big5 你已在 MariaDB 第 16 節用 `csv.DictReader` 學過，這裡只做 pandas 版本的對照。

[回 18 節課綱](../../course-plans/2026-10-data-analysis-18.md)

## 學習目標與時間

完成後，你能：讀進一份陌生 CSV 並說出每個欄位為什麼是這個型別；處理一份不是 UTF-8 的檔案而不默默換字；讀完一整個資料夾並證明「沒有重複、沒有掉欄位」。

| 時間 | 活動 | 產出 |
| --- | --- | --- |
| 0–8 分鐘 | 一行 `read_csv` 讀三份檔 | 一份報錯、兩份「成功」 |
| 8–18 分鐘 | 「成功」的那兩份錯在哪 | 型別漂移、`1970-01-01`、空欄變 `float64` |
| 18–28 分鐘 | 先決定型別再讀 | `dtype=str`、`keep_default_na=False`、明確日期格式 |
| 28–35 分鐘 | 一個資料夾，不是一個檔案 | `pathlib` ＋ `concat` ＋ 合併後驗證 |
| 35–50 分鐘 | Workshop：第四份檔、以及抓 AI 的錯 | 驗證結果與錯誤分析 |

先修：MariaDB 第 16 節（CSV 匯入品質）、爬蟲第 16 節（交給下游）。環境：Python 3.11 以上、pandas 3.0（見本頁末「教師紀錄」）。

## 一、情境：三份檔案，三個來源

主管丟給你一個資料夾：「這三部法規的條文，合成一張表給 LLM 那組用。」

```text
data/02-exports/
├── labor-standards.csv   勞動基準法       人資用 Excel 另存「CSV UTF-8」
├── mass-layoff.csv       大量解僱勞工保護法 工程師用程式匯出
└── labor-disputes.csv    勞資爭議處理法    十年前的舊系統匯出
```

三份的欄位相同：`pcode, law_name, slug, article_no, chapter, content, modified_date`。資料來自爬蟲課的練習站（9 部法規、749 條），由 `tools/build_fixtures.py` 從固定版本產生，任何人重建都會得到位元組完全相同的檔案。

你請 AI 幫忙，它給你最常見的答案：

```python
df = pd.read_csv("data/02-exports/labor-standards.csv")
```

## 二、一行 `read_csv` 讀三份：一份報錯，兩份「成功」

先看完整程式第一段的輸出（後面第四段有完整程式與執行方式）：

```text
== 1. 一行 read_csv ==
labor-disputes.csv   UnicodeDecodeError: invalid start byte
labor-standards.csv  98 列；slug=str, chapter=str, modified_date=int64
mass-layoff.csv      21 列；slug=int64, chapter=float64, modified_date=int64
```

**報錯的那份反而最安全。** `labor-disputes.csv` 是 Big5（cp950），pandas 預設用 UTF-8 解，第一個中文字就解不開，於是停下來。你知道有問題，也知道問題在哪。

另外兩份「成功」了，這才是麻煩：

| 欄位 | 勞動基準法 | 大量解僱勞工保護法 | 為什麼不一樣 |
| --- | --- | --- | --- |
| `slug` | `str` | `int64` | 勞基法有 `9-1`、`10-1` 這種條次，pandas 只好當字串；大量解僱法剛好全是數字，pandas 就猜成整數 |
| `chapter` | `str` | `float64` | 大量解僱法沒有分章，整欄是空的；空欄被讀成 `NaN`，而 `NaN` 是浮點數 |
| `modified_date` | `int64` | `int64` | `20240731` 長得像數字，就被當成數字 |

**同一個欄位，因為資料內容不同，被猜成不同型別。** 沒有任何錯誤訊息。

順帶一提：`labor-standards.csv` 開頭有 UTF-8 BOM（`EF BB BF`）。MariaDB 第 16 節用 `csv.DictReader` 讀它，第一個欄名會變成 `'\ufeffpcode'`；pandas 的 UTF-8 解碼會自動吃掉 BOM，欄名是乾淨的 `pcode`。這是 pandas 少數「幫你猜對」的地方，但不要因此以為它每次都猜對。

## 三、「成功」的代價：錯在下游才爆

把兩份能讀的合起來，錯誤開始擴散：

```text
== 2. 能讀進來的兩份，合起來 ==
slug dtype=object； slug == '1' 有 1 筆，slug == 1 有 1 筆
modified_date 原值 20150701 → pd.to_datetime() = 1970-01-01 00:00:00.020150701
```

**第一個問題：同一欄混了兩種型別。** 合併後 `slug` 變成 `object`，裡面有字串 `'1'` 也有整數 `1`。你用 `df["slug"] == "1"` 找「第 1 條」，只會找到勞基法那一條，大量解僱法的第 1 條**不見了，而且不會報錯**。之後的 `merge`（第 14 節）會因為 key 型別不一致而對不上。

**第二個問題：日期變成 1970 年。** `pd.to_datetime(20150701)` 把整數當成「從 1970-01-01 起算的奈秒數」，得到 1970 年 1 月 1 日再加 0.02 秒。它**沒有報錯**，只是答案錯了。如果下一步是「找出 2020 年後修正的法規」，這部法規會被安靜地排除。

| 一行 `read_csv` 的結果 | 在哪裡爆 | 會報錯嗎 |
| --- | --- | --- |
| 編碼不對 | `read_csv` 當下 | 會 |
| `slug` 型別漂移 | 篩選、`merge`、去重 | 不會，只是少資料 |
| 空欄變 `float64` | 字串操作、匯出 | 有時會，有時變成 `"nan"` 字串 |
| 日期被當整數 | 時間篩選與彙總（第 10–11 節） | 不會，日期變 1970 |

核心訊息：**型別是讀進來時決定的，不是之後才修的。** 讀進來後再修，你得先知道哪裡錯了；而上表大部分錯誤不會告訴你。

## 四、先決定型別，再讀

做法是**不讓 pandas 猜**：

1. **所有欄位先當字串讀**：`dtype=str`。條次、代碼、郵遞區號、電話這類「長得像數字但不是數字」的欄位，從此不會被誤判。
2. **空字串保持空字串**：`keep_default_na=False`。否則 `""`、`"NA"`、`"null"` 都會被換成 `NaN`。要不要把空字串當缺值，是第 08 節的判斷，不是讀檔時的副作用。
3. **日期給明確格式**：`pd.to_datetime(..., format="%Y%m%d")`。格式不符就報錯，而不是猜一個答案。
4. **編碼只試有限的幾種，都失敗就停**：不用 `errors="replace"`，那會把讀不懂的字換成 `�`，你的資料就默默壞了。
5. **讀完記下來源**：每一列標上來自哪個檔、用哪個編碼讀，之後出錯才追得回去。

`read_folder()` 讀完整個資料夾後，還檢查 `(pcode, slug)` 有沒有重複——三份檔若有人不小心放了兩次，這裡就會擋下來。

以下為完整 `02_read_files.py`，只讀 `data/02-exports/`，不寫任何檔案。

<!-- demo: 02_read_files.py -->
```python
"""第 02 節：把三份不同來源的 CSV 讀成同一張可信的表。"""

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data" / "02-exports"
REQUIRED = ["pcode", "law_name", "slug", "article_no", "chapter", "content", "modified_date"]
ENCODINGS = ("utf-8-sig", "cp950")  # 先試 UTF-8（順便吃掉 BOM），再試 Big5；都不行就停


def naive_read(path):
    """AI 最常給的寫法：一行 read_csv。回傳 (DataFrame 或 None, 說明)。"""
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError as exc:
        return None, f"UnicodeDecodeError: {exc.reason}"
    types = ", ".join(f"{c}={df[c].dtype}" for c in ("slug", "chapter", "modified_date"))
    return df, f"{len(df)} 列；{types}"


def detect_encoding(path):
    raw = Path(path).read_bytes()
    for enc in ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{Path(path).name}: 不是 {' / '.join(ENCODINGS)}，請先問資料提供者用什麼編碼")


def read_export(path):
    """讀一份匯出檔：型別在讀進來時就決定，不留給 pandas 猜。"""
    enc = detect_encoding(path)
    df = pd.read_csv(path, encoding=enc, dtype=str, keep_default_na=False)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"{Path(path).name}: 缺少欄位 {missing}")
    df["modified_date"] = pd.to_datetime(df["modified_date"], format="%Y%m%d")  # 格式不對會直接報錯
    df["source_file"] = Path(path).name
    df["read_encoding"] = enc
    return df


def read_folder(folder):
    files = sorted(Path(folder).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"{folder} 沒有 CSV")
    df = pd.concat([read_export(p) for p in files], ignore_index=True)
    dup = df.duplicated(["pcode", "slug"])
    if dup.any():
        raise ValueError(f"(pcode, slug) 重複 {int(dup.sum())} 筆")
    return df


if __name__ == "__main__":
    print("== 1. 一行 read_csv ==")
    naive = {}
    for p in sorted(DATA.glob("*.csv")):
        naive[p.name], note = naive_read(p)
        print(f"{p.name:20} {note}")

    print("\n== 2. 能讀進來的兩份，合起來 ==")
    both = pd.concat([naive["labor-standards.csv"], naive["mass-layoff.csv"]])
    print(f"slug dtype={both['slug'].dtype}；",
          f"slug == '1' 有 {(both['slug'] == '1').sum()} 筆，slug == 1 有 {(both['slug'] == 1).sum()} 筆")
    raw_date = naive["mass-layoff.csv"]["modified_date"]
    print(f"modified_date 原值 {raw_date.iloc[0]} → pd.to_datetime() = {pd.to_datetime(raw_date).iloc[0]}")

    print("\n== 3. 先決定型別，再讀 ==")
    df = read_folder(DATA)
    print(df.groupby(["source_file", "read_encoding"]).size().to_string())
    print(f"合計 {len(df)} 列；slug dtype={df['slug'].dtype}；chapter 空字串 {(df['chapter'] == '').sum()} 筆")
    print(df.groupby("law_name")["modified_date"].first().dt.date.to_string())
```

執行（在本目錄下）：

```bash
python3 02_read_files.py
```

第三段的關鍵輸出：

```text
== 3. 先決定型別，再讀 ==
source_file          read_encoding
labor-disputes.csv   cp950            67
labor-standards.csv  utf-8-sig        98
mass-layoff.csv      utf-8-sig        21
合計 186 列；slug dtype=str；chapter 空字串 21 筆
law_name
勞動基準法        2024-07-31
勞資爭議處理法      2021-04-28
大量解僱勞工保護法    2015-07-01
```

讀它的方式：

- **186 = 98 ＋ 21 ＋ 67**。三份都讀進來了，列數對得上。
- `slug` 全部是字串，`'9-1'` 和 `'1'` 是同一種東西，篩選與合併都不會漏。
- `chapter` 空字串 21 筆，正好是大量解僱法的 21 條。它沒有分章，**這是事實，不是缺值**；保留空字串，讓第 08 節去判斷。
- 日期都在合理年份。
- `mass-layoff.csv` 被標成 `utf-8-sig`，但它其實沒有 BOM：`utf-8-sig` 解碼「有 BOM 就去掉、沒有也照常讀」，所以這個標記代表「以 UTF-8 讀成功」，**不代表檔案有 BOM**。若你需要知道有沒有 BOM，要直接看前三個位元組。

## 五、為什麼不用「自動偵測編碼」套件？

`chardet`、`charset-normalizer` 會猜編碼，但它是**猜**——短檔案、全是常用字的檔案，Big5 與 GBK 很容易互相誤判，猜錯時讀出來的是另一套中文字，不會報錯。本節的做法刻意保守：只接受你預期的兩種，其他一律停下來問人。

`detect_encoding()` 也有界線：一份檔案若**同時**能被 UTF-8 和 Big5 合法解碼（例如全是英數），它會回 UTF-8。對英數而言兩者結果相同，所以這不會造成錯誤；但這代表它是「排除法」，不是「辨識」。

## Workshop：第四份檔，以及抓 AI 的錯

### 任務與時間

**35–42 分鐘：第四份檔。** 把下列程式存成 `make_fourth.py` 並執行，它會在 `data/02-exports/` 產生一份新的匯出檔 `extra.csv`：

```python
# make_fourth.py — Workshop 用，本節測試不涵蓋這段
from pathlib import Path
import pandas as pd

src = Path("data/02-exports/mass-layoff.csv")
df = pd.read_csv(src, dtype=str, keep_default_na=False)
df.head(3).to_csv("data/02-exports/extra.csv", index=False)
```

重新執行 `02_read_files.py`。預測會發生什麼、實際發生什麼，並說明 `read_folder()` 擋下它的那一行為什麼存在。做完後**刪除** `extra.csv`（否則之後每次執行都會停在同一個錯誤）。

**42–50 分鐘：抓 AI 的錯。** 把下列需求丟給 OpenCode（或任何 LLM），取得它的程式碼：

> 「讀 `data/02-exports/` 底下所有 CSV，合併成一個 DataFrame，找出 `slug` 是 1 的條文。」

用本節學到的檢查驗收它的答案：

| 檢查 | 怎麼確認 | AI 的版本通過嗎 |
| --- | --- | --- |
| 三份都讀得進來？ | 列數是否為 186 | |
| `slug` 只有一種型別？ | `df["slug"].map(type).value_counts()` | |
| 「slug 是 1」找到幾條？ | 應為 3（每部法規各 1 條） | |
| 日期是否合理？ | 最早、最晚的 `modified_date` | |
| 重複放檔會被擋嗎？ | 放回 `extra.csv` 再跑一次 | |

### 參考判讀

- `extra.csv` 的三列與大量解僱法前三條 `(pcode, slug)` 相同，`read_folder()` 會以 `(pcode, slug) 重複 3 筆` 停下。若沒有那行檢查，合併結果是 189 列，下游的每條統計都會多算。
- 常見的 AI 答案會把 `encoding` 寫成 `"utf-8"` 然後在 Big5 那份報錯；修正版本常改成 `encoding_errors="ignore"` 或 `"replace"`，**那是把錯誤藏起來，不是修好**。實測 `encoding_errors="replace"`：67 列全部讀得進來、沒有報錯，但 **67 列的 `content` 都含 `�`**，法規名稱變成 `�Ҹꪧĳ�B�z�k`。
- 就算 AI 替 Big5 那份指定了 `cp950`、其他用預設讀取，合併後 `slug` 是 165 個字串＋21 個整數。實測 `== 1` 找到 **1** 條、`== "1"` 找到 **2** 條；正確答案是 **3** 條，差額就是型別漂移。列數 186 是對的——**列數對，不代表內容對。**
- 同一份 AI 版本的 `modified_date` 最小值是 `20150701`、最大值是 `20240731`：看起來合理，因為它們是**整數**，比大小剛好成立。一旦轉成日期就變 1970 年。
- 「找出 slug 是 1」本身就有歧義：`slug` 是網址用的代號，`article_no` 才是「第 1 條」。能指出這一點，比寫對程式更重要。

### 驗收

- 能重現第三段輸出：186 列、`slug` 為字串、三部法規日期正確。
- 能用一句話說明「為什麼一行 `read_csv` 的錯誤不會報錯」，並舉出本節至少兩個例子。
- `extra.csv` 實驗：說出預測、實際結果，以及擋下它的那行程式。
- AI 驗收表五欄都有填，且至少指出一個 AI 版本的問題（或證明它都通過了）。

## 教師紀錄與下一步

**實測**：2026-10-05，Ubuntu 20.04，Python 3.11.8，pandas 3.0.6、numpy 2.4.6。本頁所有輸出為該環境實際執行貼上（**本機實測**）。另以 Python 3.10.15／pandas 2.3.3 執行：程式同樣成功，差別只有字串欄位的 dtype 顯示為 `object` 而非 `str`（pandas 3.0 預設啟用字串型別）。**本節尚未實班試教。**

**資料**：`data/02-exports/` 由 `tools/build_fixtures.py` 從 [4-learn/crawler-playground](https://github.com/4-learn/crawler-playground)（MIT）固定 commit `15279335` 產生，來源 SHA-256 與產物雜湊記在 `data/MANIFEST.json`。條文取自練習站，可能經刻意修改以供練習，不具法律效力。

**界線**：本節不教 `read_excel`——課綱原排在本節，但 Excel 的型別問題（日期序號、合併儲存格、多工作表）足以自成一節，硬塞會讓本節的核心訊息變淡。目前處置：**移到第 04 節前段或列為附錄**，待老師決定。

**舊教材**：舊版沒有任何讀檔章節（`read_csv` 全課 0 次）；本節為新增。

**下一節**：第 03 節〈JSON／JSONL 與巢狀結構〉讀 `data/articles.jsonl`——爬蟲課交付的格式，含 `source_url`、`fetched_at`、`content_hash`、`source_version` 四個來源欄位。
