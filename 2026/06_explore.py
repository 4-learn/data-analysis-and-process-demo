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
