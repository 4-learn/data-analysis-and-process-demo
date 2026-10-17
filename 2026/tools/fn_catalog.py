"""程式區塊上方「函式名稱／說明／官方文件連結」表格的唯一資料來源。

- ENTRIES：key → (表格第一欄顯示的寫法, 說明)。key 是官方文件的物件名稱（Sphinx inventory 名），
  或以 `syntax:` 開頭的語法條目。連結由 tools/fn_tables.py 從 DOCS 取得，不在這裡手寫。
- DOCS：key → 官方文件網址（精準到該函式的 reference 頁／錨點）。由 tools/fn_tables.py 的
  `resolve` 從 pandas／Python／NumPy 的 objects.inv 產生並逐一實測（HTTP 200 且錨點存在）後寫入 fn_docs.json。
- 說明只寫「這節用到的用法」，不是完整 API 說明；完整參數請點連結。

學生背景：上過 Python 基礎、MariaDB（sqlite3／mariadb 連線、cursor）、爬蟲（requests、json、pathlib、
hashlib、lambda、csv），沒學過 pandas／NumPy。這些已學過的標準函式庫不列入表格（FAMILIAR）。
"""

# 只預覽、不算「第一次介紹」的節次（第 01 節：「看不懂 pandas 語法沒關係……語法從第 02 節開始」）
PREVIEW_LESSONS = {"01"}

# 前置課程已在函式表裡教過的物件：不當新函式，放進「前面介紹過」並標出課程與節次。
# 依據：爬蟲課 course-plans/crawler-2026/*.md、MariaDB 課 course-materials/mariadb/*.md 的函式表或逐行說明（2026-10-17 查）。
PRIOR = {
    "bytes.decode": "爬蟲 03", "json.loads": "爬蟲 03", "json.dumps": "爬蟲 05", "hashlib.sha256": "爬蟲 15",
    "hashlib.hash.hexdigest": "爬蟲 15", "str.encode": "爬蟲 15", "pathlib.Path": "爬蟲 10",
    "contextlib.closing": "MariaDB 10", "sqlite3.Connection.execute": "MariaDB 10",
}
# 太基礎、不列表的（Python 基礎就會：list／str／set 的最常用方法、讀檔）
FAMILIAR = {
    "list.append", "str.join", "str.strip", "str.split", "str.splitlines", "str.count", "set.add", "dict.get",
    "io.TextIOBase.read", "re.Pattern.pattern", "collections.deque.append", "dict.pop",
}

# 同一個概念、不同物件型別的方法，合併成一列；值是代表的 key（連結用代表 key 的文件）
MERGE = [
    "pandas.DataFrame.loc pandas.Series.loc",
    "pandas.Series.iloc pandas.DataFrame.iloc",
    "pandas.DataFrame.index pandas.Series.index",
    "pandas.Series.sum pandas.DataFrame.sum numpy.ndarray.sum",
    "pandas.Series.any pandas.DataFrame.any numpy.ndarray.any",
    "pandas.Series.all numpy.ndarray.all",
    "pandas.DataFrame.head pandas.Series.head",
    "pandas.Series.isin pandas.Index.isin",
    "pandas.DataFrame.drop_duplicates pandas.Series.drop_duplicates",
    "pandas.DataFrame.duplicated pandas.Series.duplicated",
    "pandas.DataFrame.to_string pandas.Series.to_string",
    "pandas.Series.to_dict pandas.DataFrame.to_dict",
    "pandas.DataFrame.reset_index pandas.Series.reset_index",
    "pandas.DataFrame.sort_values pandas.Series.sort_values",
    "pandas.Series.sort_index pandas.DataFrame.sort_index",
    "pandas.DataFrame.drop pandas.Series.drop",
    "pandas.DataFrame.copy pandas.Series.copy",
    "pandas.Series.astype pandas.DataFrame.astype",
    "pandas.Series.fillna pandas.DataFrame.fillna",
    "pandas.Series.dropna pandas.DataFrame.dropna",
    "pandas.Series.isna pandas.DataFrame.isna pandas.Index.isna",
    "pandas.DataFrame.round pandas.Series.round",
    "pandas.Series.apply pandas.DataFrame.apply",
    "pandas.DataFrame.equals pandas.Series.equals pandas.Index.equals",
    "pandas.DataFrame.reindex pandas.Series.reindex",
    "pandas.Series.replace pandas.DataFrame.replace",
    "pandas.Series.nlargest pandas.DataFrame.nlargest",
    "pandas.DataFrame.explode pandas.Series.explode",
    "pandas.DataFrame.describe pandas.Series.describe",
    "pandas.DataFrame.groupby pandas.Series.groupby",
    "pandas.DataFrame.values pandas.Series.values",
    "pandas.Series.nunique pandas.Index.nunique",
    "pandas.Series.tolist pandas.Index.tolist numpy.ndarray.tolist pandas.api.extensions.ExtensionArray.tolist",
    "pandas.Series.is_unique pandas.Index.is_unique",
    "pandas.Series.dt.dayofweek pandas.DatetimeIndex.dayofweek pandas.Timestamp.dayofweek",
    "pandas.Series.dt.strftime pandas.DatetimeIndex.strftime",
    "pandas.Series.dt.total_seconds pandas.Timedelta.total_seconds",
    "pandas.MultiIndex.from_arrays pandas.MultiIndex",
    "pandas.Series.rename pandas.DataFrame.rename",
    "pandas.Series.notna pandas.DataFrame.notna",
    "pathlib.Path.resolve pathlib.PurePath.parent pathlib.Path.parent",
]
CANON = {}
for _grp in MERGE:
    _g = _grp.split()
    for _x in _g:
        CANON[_x] = _g[0]

# 不單獨成列：accessor 本身（.str／.dt）由其下的方法帶出
SKIP = {"pandas.Series.str", "pandas.Series.dt"}

ENTRIES = {
    # ---------------- 語法（不是函式，但學生沒看過）----------------
    "syntax:col": ("`df[\"欄\"]`／`df[[\"欄1\", \"欄2\"]]`",
                   "取一欄得到 `Series`；給一個 list 取多欄，得到 `DataFrame`。新增欄位也是 `df[\"新欄\"] = 值`"),
    "syntax:mask": ("`df[條件]`（布林遮罩）",
                    "`df[\"zone\"] == \"Z4\"` 會得到一整欄 True／False；放進 `df[...]` 只留下 True 的列。這是 pandas 篩選的基本寫法"),
    "syntax:boolops": ("`&`／`|`／`~`",
                       "布林遮罩的「且／或／非」。pandas 不能用 `and`／`or`／`not`；每個條件要加括號：`(a > 1) & (b == \"x\")`"),
    "syntax:strslice": ("`s.str[a:b]`", "對整欄每個字串做切片，例如 `event_time.str[:10]` 取出日期部分"),
    "syntax:label": ("`s[標籤]`", "從 `Series` 依標籤取一個值，例如 `counts[\"W041\"]`；給布林遮罩則是篩選"),
    "syntax:vector": ("`s1 - s2`、`s / 100`（整欄運算）",
                      "對整欄直接做加減乘除，每一列各算一次，不用寫迴圈；兩欄相減時依標籤對齊"),

    # ---------------- 讀寫 ----------------
    "pandas.read_csv": ("`pd.read_csv(path, dtype=str, keep_default_na=False, encoding=)`",
                        "讀 CSV 成 `DataFrame`。`dtype=str` 每欄都當字串；`keep_default_na=False` 空格保持 `\"\"` 不變 `NaN`；`encoding` 指定編碼"),
    "pandas.read_json": ("`pd.read_json(path, lines=True, dtype=False, convert_dates=False)`",
                         "讀 JSON／JSONL 成 `DataFrame`。`lines=True` 一行一筆（JSONL）；`dtype=False` 不猜型別；`convert_dates=False` 不依欄名自動轉日期"),
    "pandas.read_sql": ("`pd.read_sql(sql, con, params=)`",
                        "執行 SQL，把結果直接變成 `DataFrame`；`params` 是 `?` 佔位符的值（tuple）"),
    "pandas.json_normalize": ("`pd.json_normalize(data, record_path=, meta=)`",
                              "把巢狀 JSON 攤平成表。`record_path` 指定「一列是哪個 list 的元素」；`meta` 指定外層要帶下來的欄位"),
    "pandas.DataFrame.to_json": ("`df.to_json(orient=\"records\", lines=True, force_ascii=False)`",
                                 "`DataFrame` 轉 JSON 字串。這三個參數合起來＝JSONL、一列一個物件、中文不轉成 `\\uXXXX`"),
    "pandas.DataFrame.to_csv": ("`df.to_csv(path=None, index=)`",
                                "`DataFrame` 轉 CSV；沒給路徑就回傳字串。`index=False` 不輸出列號"),
    "pandas.DataFrame.to_string": ("`df.to_string(index=)`",
                                   "把整張表轉成對齊好的文字（`print` 用）；不會像直接 `print(df)` 那樣把中間省略成 `...`"),
    "pandas.DataFrame.to_markdown": ("`df.to_markdown(index=False)`",
                                     "把表格轉成 Markdown 表格字串（需要安裝 `tabulate`）"),
    "pandas.Series.to_dict": ("`s.to_dict()`／`df.to_dict(\"records\")`",
                              "轉成 Python dict；`Series` 是「index → 值」，`df.to_dict(\"records\")` 是「一列一個 dict 的 list」"),
    "pandas.Series.tolist": ("`.tolist()`", "轉成 Python list（`Series`、`Index`、`unique()` 的結果都可以）"),

    # ---------------- 建立物件 ----------------
    "pandas.DataFrame": ("`pd.DataFrame(資料, columns=)`",
                         "建立表格。資料可以是「一列一個 dict 的 list」或「欄名 → 一欄值的 dict」"),
    "pandas.Series": ("`pd.Series(資料, index=, name=, dtype=)`",
                      "建立「一欄」：有 index（標籤）的一維資料。`DataFrame` 的每一欄都是一個 `Series`"),
    "pandas.Index": ("`pd.Index(值, name=)`", "建立一組標籤（列或欄的名字）；常拿來當 `reindex` 的目標"),
    "pandas.MultiIndex.from_arrays": ("`pd.MultiIndex.from_arrays([欄1, 欄2])`",
                                      "把兩欄組成「兩層」的標籤，例如（人, 日）一組；可以拿來跟另一個兩層 index 比對"),
    "pandas.MultiIndex.from_product": ("`pd.MultiIndex.from_product([清單1, 清單2], names=)`",
                                       "產生兩個清單的所有組合（例如每個人 × 每一週），用來補齊沒出現的格子"),
    "pandas.MultiIndex.names": ("`index.names`", "多層 index 每一層的名字"),
    "pandas.MultiIndex.get_level_values": ("`index.get_level_values(層)`", "取出多層 index 某一層的值"),
    "pandas.Timestamp": ("`pd.Timestamp(值)`", "pandas 的「一個時間點」；可以帶時區，可以互相比大小、相減"),
    "pandas.Timedelta": ("`pd.Timedelta(\"1min\")`／`pd.Timedelta(hours=1)`", "一段時間長度；時間相減得到它，也能拿來跟它比大小"),
    "pandas.Grouper": ("`pd.Grouper(key=, freq=)`", "放進 `groupby` 裡，表示「依某個時間欄、每 `freq`（例如 `\"D\"` 一天）分一組」"),
    "pandas.concat": ("`pd.concat([df1, df2], ignore_index=True, axis=)`",
                      "把多個表上下疊起來（`axis=1` 則左右並排）。`ignore_index=True` 重新編列號 0、1、2…"),
    "pandas.crosstab": ("`pd.crosstab(列, 欄)`", "交叉計數表：每個（列值, 欄值）組合出現幾次"),

    # ---------------- 看資料 ----------------
    "pandas.DataFrame.shape": ("`df.shape`", "（列數, 欄數）的 tuple；`df.shape[1]` 是欄數"),
    "pandas.DataFrame.columns": ("`df.columns`", "所有欄名。可以 `for c in df.columns`，也可以 `\"欄\" in df.columns` 檢查有沒有這欄"),
    "pandas.DataFrame.index": ("`df.index`", "列的標籤（預設是 0、1、2…）；篩選後會保留原本的標籤，不會重新編號"),
    "pandas.DataFrame.dtypes": ("`df.dtypes`", "每一欄的型別"),
    "pandas.Series.dtype": ("`s.dtype`", "這一欄的型別：`str`、`int64`、`float64`、`datetime64[…]`、`object`（什麼都可能有）"),
    "pandas.DataFrame.head": ("`df.head(n)`", "前 n 列（預設 5）"),
    "pandas.DataFrame.tail": ("`df.tail(n)`", "最後 n 列"),
    "pandas.DataFrame.info": ("`df.info(buf=)`", "印出每欄的型別與非空值數量；`buf` 指定要寫到哪裡（預設印到螢幕）"),
    "pandas.DataFrame.describe": ("`df.describe(include=, percentiles=)`", "數值欄的摘要統計：個數、平均、標準差、最小、四分位數、最大"),
    "pandas.DataFrame.select_dtypes": ("`df.select_dtypes(\"number\")`", "只留指定型別的欄位"),
    "pandas.DataFrame.empty": ("`df.empty`", "表格是不是一列都沒有（True／False）"),
    "pandas.DataFrame.values": ("`df.values`", "去掉標籤，只留裡面的值（NumPy 陣列）"),
    "pandas.Series.is_unique": ("`.is_unique`", "這一欄（或 index）的值是不是都不重複（True／False）"),
    "pandas.Series.is_monotonic_increasing": ("`s.is_monotonic_increasing`", "這一欄是不是由小到大排好（允許相等）"),
    "pandas.Series.items": ("`s.items()`", "逐一取出（標籤, 值），可以放進 `for` 迴圈"),
    "pandas.Series.get": ("`s.get(標籤, 預設)`", "依標籤取值；沒有這個標籤就回傳預設值，不會報錯"),

    # ---------------- 選取與篩選 ----------------
    "pandas.DataFrame.loc": ("`df.loc[列條件, 欄]`", "依**標籤**或布林條件選列，同時選欄：`df.loc[df[\"x\"] > 1, \"y\"]`。要改值也用它"),
    "pandas.Series.iloc": ("`.iloc[位置]`", "依**位置**（第幾個，從 0 起）取值；`s.iloc[0]` 是第一個，不管它的標籤是什麼"),
    "pandas.Series.isin": ("`s.isin(集合)`", "每個值是不是在集合裡，得到 True／False 一欄，常放進 `df[...]` 篩選"),
    "pandas.Series.between": ("`s.between(a, b)`", "每個值是否 `a ≤ 值 ≤ b`"),
    "pandas.DataFrame.query": ("`df.query(\"欄 == '值' and 欄2 > 1\")`", "用一段字串寫篩選條件；條件裡可以直接寫欄名"),
    "pandas.Series.where": ("`s.where(條件, 其他)`", "條件成立的保留，不成立的換成「其他」（沒給就是 `NaN`）"),
    "pandas.Series.mask": ("`s.mask(條件, 其他)`", "跟 `where` 相反：條件**成立**的換掉，其他保留"),
    "pandas.Series.xs": ("`s.xs(值, level=)`", "從多層 index 中，取出某一層等於某值的那一部分"),
    "pandas.Index.intersection": ("`idx1.intersection(idx2)`", "兩組標籤都有的部分（交集）"),

    # ---------------- 比較、計算 ----------------
    "pandas.Series.eq": ("`s.eq(值)`", "跟 `s == 值` 一樣，得到 True／False 一欄；寫成方法可以接著串 `.sum()`"),
    "pandas.DataFrame.gt": ("`.gt(n)`", "跟 `> n` 一樣，對每一格比較，得到 True／False"),
    "pandas.Series.any": ("`.any()`／`.any(axis=1)`", "是否**至少一個** True。`axis=1` 是每一列各算一次"),
    "pandas.Series.all": ("`.all()`", "是否**全部**都是 True"),
    "pandas.Series.sum": ("`.sum()`", "加總。對 True／False 加總＝數有幾個 True"),
    "pandas.Series.mean": ("`s.mean()`", "平均。`NaN` 會被跳過，不算進分母"),
    "pandas.Series.max": ("`s.max()`", "最大值（字串欄就是字典順序最大）"),
    "pandas.Series.min": ("`s.min()`", "最小值"),
    "pandas.Series.median": ("`s.median()`", "中位數"),
    "pandas.Series.std": ("`s.std()`", "標準差"),
    "pandas.Series.quantile": ("`s.quantile([0.25, 0.75])`", "分位數，例如 0.25 是第一四分位數"),
    "pandas.Series.abs": ("`s.abs()`", "絕對值"),
    "pandas.DataFrame.round": ("`.round(n)`", "四捨五入到小數 n 位"),
    "pandas.Series.idxmax": ("`s.idxmax()`", "最大值所在的**標籤**（不是值本身）"),
    "pandas.Series.nunique": ("`.nunique(dropna=)`", "有幾個不同的值；`dropna=False` 時 `NaN` 也算一種"),
    "pandas.Series.unique": ("`s.unique()`", "不重複的值（依出現順序）"),
    "pandas.Series.value_counts": ("`s.value_counts()`", "每個值出現幾次，由多到少排列"),
    "pandas.Series.diff": ("`s.diff()`", "每一個值減去上一個值（第一個是 `NaN`）"),
    "pandas.Series.shift": ("`s.shift()`", "整欄往下移一格，用來跟「上一列」比較"),
    "pandas.Series.rank": ("`s.rank(method=\"min\", ascending=False)`", "排名；`method=\"min\"` 讓同分的人拿同一個（最好的）名次"),
    "pandas.Series.argsort": ("`s.argsort(kind=\"stable\")`", "排序後每個位置原本是第幾個；`kind=\"stable\"` 相同的值保留原順序"),
    "pandas.Series.nlargest": ("`.nlargest(k, keep=)`", "最大的 k 個；`keep` 決定並列時怎麼取（`\"first\"`、`\"last\"`、`\"all\"`）"),
    "pandas.DataFrame.equals": ("`.equals(另一個)`", "兩個表／欄是否完全相同：值、標籤、**型別**都要一樣"),

    # ---------------- 缺值與型別 ----------------
    "pandas.Series.isna": ("`.isna()`", "每一格是不是缺值（`NaN`／`None`／`NaT`），得到 True／False"),
    "pandas.Series.notna": ("`.notna()`", "跟 `isna()` 相反：不是缺值的為 True"),
    "pandas.Series.fillna": ("`.fillna(值)`", "把缺值換成指定的值"),
    "pandas.Series.dropna": ("`.dropna(subset=)`", "去掉有缺值的列；`subset` 只看指定欄"),
    "pandas.Series.replace": ("`.replace(舊, 新, regex=)`", "把某個值換成另一個值（例如 `\"\"` 換成 `np.nan`）；`regex=True` 時「舊」是正規表示式"),
    "pandas.Series.astype": ("`.astype(型別)`", "轉換型別，例如 `.astype(int)`、`.astype(str)`"),
    "pandas.to_numeric": ("`pd.to_numeric(s, errors=)`", "把字串轉成數字；`errors=\"coerce\"` 會把轉不了的**默默變 `NaN`**"),
    "pandas.api.types.is_datetime64_any_dtype": ("`pd.api.types.is_datetime64_any_dtype(s)`", "這一欄是不是日期時間型別"),
    "numpy.nan": ("`np.nan`", "NumPy 的「缺值」，型別是浮點數"),
    "numpy.inf": ("`np.inf`", "無限大；常當最後一個分組的上限"),

    # ---------------- 排序、去重、改結構 ----------------
    "pandas.DataFrame.sort_values": ("`.sort_values(欄, ascending=, kind=\"stable\")`", "依值排序；`ascending=False` 由大到小；`kind=\"stable\"` 值相同時保留原本順序"),
    "pandas.Series.sort_index": ("`.sort_index()`", "依標籤排序"),
    "pandas.DataFrame.duplicated": ("`.duplicated(欄, keep=)`", "標出重複的列（True／False）。`keep=\"first\"` 第一次出現的不算重複；`keep=False` 所有重複的都標出"),
    "pandas.DataFrame.drop_duplicates": ("`.drop_duplicates(欄, keep=\"first\")`", "去掉重複的列，同一個鍵只留一列"),
    "pandas.DataFrame.drop": ("`.drop(columns=)`／`s.drop(標籤)`", "去掉指定的欄或標籤，回傳新的物件"),
    "pandas.Series.rename": ("`.rename(名稱)`／`df.rename(columns={舊: 新})`", "`Series` 改名稱；`DataFrame` 改欄名"),
    "pandas.DataFrame.reset_index": ("`.reset_index(name=, drop=)`", "把標籤變回一般欄位，列號重新從 0 開始。`drop=True` 直接丟掉舊標籤；`name=` 給 `Series` 的值欄取名"),
    "pandas.DataFrame.set_index": ("`df.set_index(欄)`", "把某一欄當成列的標籤"),
    "pandas.DataFrame.reindex": ("`.reindex(新標籤, fill_value=)`", "照一組指定的標籤重排；原本沒有的標籤補上 `fill_value`（預設 `NaN`）"),
    "pandas.DataFrame.assign": ("`df.assign(新欄=值)`", "加上（或覆蓋）欄位，回傳**新的**表，原表不變"),
    "pandas.DataFrame.insert": ("`df.insert(位置, 欄名, 值)`", "在指定位置插入一欄（直接改原表）"),
    "pandas.DataFrame.copy": ("`.copy()`", "複製一份；之後改它不會動到原本的資料"),
    "pandas.Series.unstack": ("`s.unstack(層, fill_value=)`", "把多層 index 的某一層轉成欄，變成二維表；沒有的格子補 `fill_value`"),
    "pandas.DataFrame.explode": ("`.explode(欄, ignore_index=)`", "某欄的每一格是 list 時，把 list 拆開，一個元素一列"),
    "pandas.DataFrame.itertuples": ("`df.itertuples(index=False, name=)`", "一列一列取出成 tuple。`index=False` 不含列標籤；`name=None` 得到普通 tuple（不給則是可以用 `row.欄名` 取值的具名 tuple）"),
    "pandas.DataFrame.iterrows": ("`df.iterrows()`", "一列一列取出（標籤, 那一列的 `Series`）；慢，只在列很少時用"),

    # ---------------- 套用函式 ----------------
    "pandas.Series.map": ("`s.map(函式或 dict)`", "對每個值套用函式（或依 dict 對照換值），得到新的一欄"),
    "pandas.Series.apply": ("`.apply(函式)`", "對每個值（`DataFrame` 則是每一欄）套用函式"),
    "numpy.select": ("`np.select(條件清單, 結果清單, default=)`", "依序檢查條件，第一個成立的就給對應結果；都不成立給 `default`"),
    "pandas.cut": ("`pd.cut(s, bins, right=, labels=)`", "依指定的分界把數字分組（例如 0–3 低、3–5 中）；`right=False` 是「含左不含右」"),
    "pandas.qcut": ("`pd.qcut(s, q, labels=, retbins=)`", "依**分位數**分組（每組人數差不多）；`retbins=True` 同時回傳實際分界"),

    # ---------------- 分組 ----------------
    "pandas.DataFrame.groupby": ("`df.groupby(欄, sort=, dropna=)`", "依某欄的值分組，後面接 `.size()`、`.sum()`、`.agg()` 算每組。`dropna=False` 時缺值也自成一組（預設會**丟掉**）"),
    "pandas.api.typing.DataFrameGroupBy.size": ("`.groupby(...).size()`", "每組有幾列"),
    "pandas.api.typing.DataFrameGroupBy.nunique": ("`.groupby(...)[欄].nunique()`", "每組裡各欄有幾種不同的值"),
    "pandas.api.typing.SeriesGroupBy.first": ("`.groupby(...)[欄].first()`", "每組的第一個值"),
    "pandas.api.typing.SeriesGroupBy.sum": ("`.groupby(...)[欄].sum()`", "每組加總"),
    "pandas.api.typing.SeriesGroupBy.mean": ("`.groupby(...)[欄].mean()`", "每組平均（跳過缺值）"),
    "pandas.api.typing.SeriesGroupBy.max": ("`.groupby(...)[欄].max()`", "每組最大值"),
    "pandas.api.typing.SeriesGroupBy.nunique": ("`.groupby(...)[欄].nunique()`", "每組有幾種不同的值"),
    "pandas.api.typing.SeriesGroupBy.agg": ("`.groupby(...)[欄].agg(函式)`", "每組套用自訂的彙總函式"),
    "pandas.api.typing.SeriesGroupBy.describe": ("`.groupby(...)[欄].describe()`", "每組各算一次摘要統計"),
    "pandas.api.typing.DataFrameGroupBy.sum": ("`.groupby(...)[[欄1, 欄2]].sum()`", "每組各欄加總"),
    "pandas.api.typing.DataFrameGroupBy.agg": ("`.groupby(...).agg(新欄=(\"欄\", \"函式\"))`", "一次算多種彙總，並替結果欄命名（named aggregation）"),
    "pandas.api.typing.DataFrameGroupBy.cumcount": ("`.groupby(...).cumcount()`", "每列是組內的第幾個（從 0 起）"),
    "pandas.DataFrame.resample": ("`df.resample(\"D\"／\"W-MON\", label=, closed=)`", "依時間 index 每天／每週分組（像時間版的 `groupby`）；`W-MON` 是「到週一為止」的週"),
    "pandas.api.typing.Resampler.size": ("`.resample(...).size()`", "每個時間區間有幾列；**沒有資料的區間會補 0**（跟 `groupby` 不同）"),

    # ---------------- 合併 ----------------
    "pandas.DataFrame.merge": ("`left.merge(right, on=, how=, validate=, indicator=)`",
                               "依共同欄位把兩張表接起來（SQL 的 JOIN）。`how` 是 inner／left；`validate=\"one_to_one\"` 等會在鍵重複時報錯；`indicator=True` 多一欄標出每列來自哪邊"),
    "pandas.errors.MergeError": ("`pd.errors.MergeError`", "`merge` 的 `validate` 檢查不通過時拋出的例外"),

    # ---------------- 字串（.str）----------------
    "pandas.Series.str.contains": ("`s.str.contains(樣式, regex=, na=)`", "每個字串是否包含某段文字或符合正規表示式；`regex=False` 當普通文字找"),
    "pandas.Series.str.startswith": ("`s.str.startswith(前綴)`", "每個字串是否以某段文字開頭"),
    "pandas.Series.str.endswith": ("`s.str.endswith(後綴)`", "每個字串是否以某段文字結尾"),
    "pandas.Series.str.len": ("`s.str.len()`", "每個字串的長度（字元數）"),
    "pandas.Series.str.fullmatch": ("`s.str.fullmatch(樣式, na=)`", "**整個**字串是否完全符合正規表示式（不是只有一部分符合）"),
    "pandas.Series.str.match": ("`s.str.match(樣式)`", "字串**開頭**是否符合正規表示式"),
    "pandas.Series.str.findall": ("`s.str.findall(樣式)`", "每個字串裡所有符合的片段（list）"),
    "pandas.Series.str.count": ("`s.str.count(樣式)`", "每個字串裡出現幾次"),
    "pandas.Series.str.replace": ("`s.str.replace(舊, 新, regex=)`", "每個字串裡的文字替換"),
    "pandas.Series.str.split": ("`s.str.split(分隔, expand=)`", "每個字串依分隔符切開；`expand=True` 切成多欄"),
    "pandas.Series.str.rstrip": ("`s.str.rstrip(字元)`", "去掉每個字串右邊的指定字元"),
    "pandas.Series.str.removesuffix": ("`s.str.removesuffix(後綴)`", "有這個結尾就去掉，沒有就不動"),

    # ---------------- 日期時間（.dt）----------------
    "pandas.to_datetime": ("`pd.to_datetime(s, format=, utc=, errors=)`",
                           "字串轉日期時間。`format` 指定格式（`\"ISO8601\"` 或 `\"%Y%m%d\"`），格式不符就報錯；`utc=True` 統一轉成 UTC"),
    "pandas.to_timedelta": ("`pd.to_timedelta(s, unit=\"D\")`", "數字轉成時間長度，`unit=\"D\"` 表示單位是天"),
    "pandas.Series.dt.tz_convert": ("`s.dt.tz_convert(\"Asia/Taipei\")`", "已經有時區的時間，換算成另一個時區（同一個時刻，換個寫法）"),
    "pandas.Series.dt.tz_localize": ("`s.dt.tz_localize(時區)`", "替**沒有時區**的時間標上時區（宣告它原本就是那個時區的時間）；`None` 則拿掉時區"),
    "pandas.Series.dt.tz": ("`s.dt.tz`", "這一欄的時區；沒有時區是 `None`"),
    "pandas.Timestamp.tzinfo": ("`ts.tzinfo`", "這個時間點的時區；沒有時區是 `None`"),
    "pandas.Series.dt.normalize": ("`s.dt.normalize()`", "把時間改成當天 00:00（保留日期與時區）"),
    "pandas.Series.dt.floor": ("`s.dt.floor(\"D\"／\"h\"／\"min\")`", "無條件捨去到天／小時／分鐘"),
    "pandas.Series.dt.weekday": ("`s.dt.weekday`", "星期幾：週一是 0、週日是 6"),
    "pandas.Series.dt.dayofweek": ("`.dayofweek`", "星期幾：週一是 0、週日是 6（同 `weekday`）"),
    "pandas.Series.dt.hour": ("`s.dt.hour`", "幾點（0–23）"),
    "pandas.Series.dt.date": ("`s.dt.date`", "只取日期部分（Python 的 `date`）"),
    "pandas.Series.dt.strftime": ("`.strftime(\"%Y-%m-%d\")`", "時間轉成指定格式的字串"),
    "pandas.Series.dt.to_period": ("`s.dt.to_period(\"W-SUN\")`", "時間轉成「所在的期間」，例如所在的那一週"),
    "pandas.Series.dt.total_seconds": ("`s.dt.total_seconds()`／`td.total_seconds()`", "時間長度換算成秒數"),

    # ---------------- 標準函式庫（本課新出現的）----------------
    "str.isascii": ("`ch.isascii()`", "這個字元是不是 ASCII（英數、符號）；中文是 False"),
    "str.isdigit": ("`ch.isdigit()`", "這個字元是不是數字"),
    "math.ceil": ("`math.ceil(x)`", "無條件進位成整數"),
    "math.floor": ("`math.floor(x)`", "無條件捨去成整數"),
    "collections.defaultdict": ("`defaultdict(deque)`", "查不到的 key 會自動建立預設值（這裡是空的 `deque`），不會 KeyError"),
    "collections.deque.popleft": ("`q.popleft()`", "`deque`（雙端佇列）從左邊（最舊的）取出一個；比 list 的 `pop(0)` 快"),
    "datetime.datetime.fromisoformat": ("`datetime.fromisoformat(s)`", "ISO 8601 字串（`2026-09-22T14:08:38+08:00`）轉成 `datetime`"),
    "datetime.date.fromisoformat": ("`date.fromisoformat(\"2026-09-27\")`", "`YYYY-MM-DD` 字串轉成 `date`；之後可以用 `.weekday()` 算星期幾（週日是 6）"),
    "datetime.date.weekday": ("`d.weekday()`", "星期幾：週一是 0、週日是 6"),
    "datetime.timedelta.total_seconds": ("`(t1 - t0).total_seconds()`", "兩個時間相減得到時間長度，換算成秒"),
    "io.StringIO": ("`io.StringIO(文字)`", "把一段字串包成「檔案」，可以直接丟給 `pd.read_csv`，或讓函式寫進去"),
    "io.StringIO.getvalue": ("`buf.getvalue()`", "取出寫進 `StringIO` 的全部文字"),
    "re.compile": ("`re.compile(樣式)`", "把正規表示式先編譯好，重複使用"),
    "re.escape": ("`re.escape(文字)`", "把文字裡的特殊符號跳脫，讓它在正規表示式裡被當成普通文字"),
    "warnings.catch_warnings": ("`warnings.catch_warnings(record=True)`", "搭配 `with`：在區塊內把發出的警告收集成 list，而不是印出來"),
    "warnings.simplefilter": ("`warnings.simplefilter(\"always\")`", "設定警告怎麼處理；`\"always\"` 每次都發出（不因重複而略過）"),
    "warnings.filterwarnings": ("`warnings.filterwarnings(\"ignore\", message=, category=)`", "只關掉**符合條件**的那一種警告，其他照常顯示"),
    "sqlite3.connect": ("`sqlite3.connect(\":memory:\")`", "開一個 SQLite 資料庫連線；`\":memory:\"` 建在記憶體、不寫檔"),
    "pathlib.Path": ("`Path(路徑)`", "把字串變成路徑物件，可以用 `/` 接路徑：`Path(\"data\") / \"a.csv\"`"),
    "pathlib.PurePath.parent": ("`path.parent`", "路徑的上一層資料夾"),
    "pathlib.Path.resolve": ("`Path(__file__).resolve().parent`",
                             "`__file__` 是這支程式自己的路徑；`resolve()` 轉成完整路徑，`.parent` 取所在資料夾。從哪裡執行都找得到 `data/`"),
    "pathlib.Path.read_text": ("`path.read_text(encoding=\"utf-8\")`", "把整個檔案讀成一個字串"),
    "pathlib.Path.read_bytes": ("`path.read_bytes()`", "把整個檔案讀成 bytes（還沒解碼），才能自己試不同編碼"),
    "pathlib.Path.glob": ("`folder.glob(\"*.csv\")`", "找出資料夾裡符合樣式的檔案；順序不固定，要自己 `sorted()`"),
    "pathlib.PurePath.name": ("`path.name`", "路徑最後的檔名，例如 `mass-layoff.csv`"),
    "bytes.decode": ("`raw.decode(編碼)`", "bytes 轉字串；解不開會丟 `UnicodeDecodeError`"),
    "json.loads": ("`json.loads(s)`", "JSON 字串 → Python dict／list"),
    "json.dumps": ("`json.dumps(obj, ensure_ascii=False)`", "Python 物件 → JSON 字串；`ensure_ascii=False` 讓中文保持原字"),
    "hashlib.sha256": ("`hashlib.sha256(bytes).hexdigest()`", "算 SHA-256 雜湊，回傳 64 字元的十六進位字串"),
    "hashlib.hash.hexdigest": ("`.hexdigest()`", "雜湊結果轉成十六進位字串"),
    "str.encode": ("`s.encode(\"utf-8\")`", "字串 → bytes；雜湊函式只吃 bytes"),
    "contextlib.closing": ("`with closing(連線) as con:`", "離開 `with` 時一定呼叫 `close()`，出錯也一樣"),
    "sqlite3.Connection.execute": ("`con.execute(sql, params)`", "執行一句 SQL；值用 `?` 佔位，放在 `params`"),
    "sqlite3.Connection.executemany": ("`con.executemany(sql, 多筆資料)`", "同一句 SQL 對多筆資料各執行一次（批次寫入）"),
    "sqlite3.Connection.close": ("`con.close()`", "關閉資料庫連線"),
    "sqlite3.IntegrityError": ("`sqlite3.IntegrityError`", "違反唯一鍵、NOT NULL 等限制時丟出的例外"),
    "dict.items": ("`d.items()`", "逐一取出 dict 的（key, 值），可以放進 `for k, v in d.items()`"),
    "dict.values": ("`d.values()`", "dict 所有的值"),
    "pytest.raises": ("`with pytest.raises(例外, match=):`", "斷言區塊內**一定會**丟出指定的例外（訊息要符合 `match`）；沒丟出測試就失敗"),
    "builtins.repr": ("`repr(x)`", "顯示值的「原始寫法」，字串會帶引號，看得出空白與 `\"\"`"),
    "builtins.reversed": ("`reversed(序列)`", "倒過來的順序"),
    "UnicodeError.reason": ("`exc.reason`", "`UnicodeDecodeError` 的錯誤原因文字"),
}


# 表格「前面介紹過」那一列用的短名稱（沒列的就從 ENTRIES 第一欄自動截）
SHORT = {
    "syntax:col": "df[\"欄\"]", "syntax:mask": "df[條件]", "syntax:boolops": "& | ~", "syntax:strslice": "s.str[a:b]",
    "syntax:label": "s[標籤]", "syntax:vector": "整欄運算",
    "pandas.DataFrame.loc": ".loc[]", "pandas.Series.iloc": ".iloc[]",
    "pandas.Series.to_dict": ".to_dict()", "pandas.DataFrame.drop": ".drop()", "pandas.Series.rename": ".rename()",
    "pandas.Timedelta": "pd.Timedelta", "pandas.MultiIndex.names": "index.names", "pandas.Series.any": ".any()",
    "collections.defaultdict": "defaultdict", "datetime.timedelta.total_seconds": "timedelta.total_seconds()",
    "pytest.raises": "pytest.raises()", "pathlib.Path.resolve": "Path(__file__).resolve().parent",
    "pandas.api.typing.DataFrameGroupBy.agg": "groupby().agg()", "pandas.api.typing.SeriesGroupBy.agg": "groupby()[欄].agg()",
    "pandas.api.typing.DataFrameGroupBy.size": "groupby().size()", "pandas.api.typing.DataFrameGroupBy.nunique": "groupby()[欄].nunique()",
    "pandas.api.typing.SeriesGroupBy.first": "groupby()[欄].first()", "pandas.api.typing.SeriesGroupBy.sum": "groupby()[欄].sum()",
    "pandas.api.typing.SeriesGroupBy.mean": "groupby()[欄].mean()", "pandas.api.typing.SeriesGroupBy.max": "groupby()[欄].max()",
    "pandas.api.typing.SeriesGroupBy.nunique": "groupby()[欄].nunique()", "pandas.api.typing.SeriesGroupBy.describe": "groupby()[欄].describe()",
    "pandas.api.typing.DataFrameGroupBy.sum": "groupby()[[欄]].sum()", "pandas.api.typing.DataFrameGroupBy.cumcount": "groupby().cumcount()",
    "pandas.api.typing.Resampler.size": "resample().size()", "pandas.Series.dt.total_seconds": "s.dt.total_seconds()",
    "pandas.Series.dt.dayofweek": ".dayofweek", "pandas.Series.dt.strftime": ".strftime()",
}

# 程式碼只在註解裡提示、但學生要寫出來的函式：(講義, 區塊內含的文字) → [key]
EXTRA = {
    ("09-validate-idempotent.md", "用 pytest.raises(ValidationError)"): ["pytest.raises"],
}

# 沒執行到的行，靠全課觀察推不準的少數屬性：(講義, 屬性名, 該行包含的文字) → key
STATIC_OVERRIDE = {
    ("18-end-to-end.md", "weekday", "date.fromisoformat(d).weekday()"): "datetime.date.weekday",
}

# Python 文件釘在 3.12（本課要求 3.11+；docs.python.org/3/ 從 3.13 起把內建型別移到 builtins/，預設版本一換舊連結就被轉走）
# inventory 裡沒有、或語法條目：手動指定的官方文件（仍會被 fn_tables.py docs 逐一實測）
MANUAL_DOCS = {
    "syntax:col": "https://pandas.pydata.org/docs/user_guide/indexing.html#basics",
    "syntax:mask": "https://pandas.pydata.org/docs/user_guide/indexing.html#boolean-indexing",
    "syntax:boolops": "https://pandas.pydata.org/docs/user_guide/indexing.html#boolean-operators",
    "syntax:strslice": "https://pandas.pydata.org/docs/user_guide/text.html#indexing-with-str",
    "syntax:label": "https://pandas.pydata.org/docs/user_guide/indexing.html#basics",
    "syntax:vector": "https://pandas.pydata.org/docs/user_guide/basics.html#flexible-binary-operations",
    "pandas.Series.tolist": "https://pandas.pydata.org/docs/reference/api/pandas.Series.tolist.html",
    "builtins.repr": "https://docs.python.org/3.12/library/functions.html#repr",
    "builtins.reversed": "https://docs.python.org/3.12/library/functions.html#reversed",
    "pytest.raises": "https://docs.pytest.org/en/stable/reference/reference.html#pytest.raises",
}
