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
