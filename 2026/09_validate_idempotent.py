"""第 09 節：壞資料要被擋下，同一批資料重跑要一樣。"""

import hashlib
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
KEY = ["pcode", "slug"]                      # 業務鍵：一部法規的一條條文
COLUMNS = ["pcode", "law_name", "slug", "article_no", "chapter", "content",
           "source_url", "fetched_at", "content_hash", "source_version"]
REQUIRED = [c for c in COLUMNS if c != "chapter"]   # 沒分章的法規 chapter 就是空的：那是事實，不是缺值
VERSIONS = {"v1", "v2"}


class ValidationError(ValueError):
    """驗證失敗就讓流程停下來；不是印一行 warning 然後繼續。"""


def read_batch(path):
    return pd.read_json(path, lines=True, dtype=False, convert_dates=False)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate(df):
    """一次列出所有問題（而不是只報第一個），任何一項不過就拋 ValidationError。"""
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValidationError(f"缺少欄位 {missing}")
    checks = {
        "必填欄位有空值": df[REQUIRED].isna().any(axis=1) | (df[REQUIRED] == "").any(axis=1),
        "pcode 格式": ~df["pcode"].str.fullmatch(r"N\d{7}", na=False),
        "slug 格式": ~df["slug"].str.fullmatch(r"\d+(?:-\d+)?", na=False),
        "article_no 與 slug 不一致": df["article_no"] != "第 " + df["slug"] + " 條",
        "source_version 不在白名單": ~df["source_version"].isin(VERSIONS),
        "fetched_at 沒有時區": ~df["fetched_at"].str.contains(r"(?:[+-]\d\d:\d\d|Z)$", na=False),
        "content_hash 與內容不符": df["content"].fillna("").map(sha) != df["content_hash"],
        "業務鍵重複": df.duplicated(KEY, keep=False),
    }
    problems = []
    for rule, bad in checks.items():
        if bad.any():
            first = df.loc[bad, KEY].iloc[0]
            problems.append(f"{rule}：{int(bad.sum())} 筆，例如 {first['pcode']}/{first['slug']}")
    if problems:
        raise ValidationError("；".join(problems))
    return df


def fingerprint(df):
    """整張表的指紋：同樣內容（不論列的順序）得到同樣的值，用來證明重跑結果一致。"""
    text = df.sort_values(KEY)[COLUMNS].to_json(orient="records", lines=True, force_ascii=False)
    return sha(text)[:12]


def apply_batch(current, batch):
    """以業務鍵 upsert：較新的 fetched_at 勝出；較舊或相同的重送不改變任何東西。"""
    validate(batch)
    old = current.set_index(KEY)
    report = {"新增": 0, "更新": 0, "略過（不比現有新）": 0}
    for row in batch.itertuples(index=False):
        key = (row.pcode, row.slug)
        if key not in old.index:
            report["新增"] += 1
            continue
        mine = old.loc[key]
        t_new = pd.Timestamp(row.fetched_at)
        t_old = pd.Timestamp(mine["fetched_at"])
        if t_new == t_old and row.content_hash != mine["content_hash"]:
            raise ValidationError(f"{key[0]}/{key[1]} 同一時間點有兩種內容，無法判斷誰對")
        report["更新" if t_new > t_old else "略過（不比現有新）"] += 1
    combined = pd.concat([current, batch], ignore_index=True)
    combined["_t"] = pd.to_datetime(combined["fetched_at"], utc=True, format="ISO8601")
    result = (combined.sort_values(KEY + ["_t"], kind="stable")
              .drop_duplicates(KEY, keep="last")
              .drop(columns="_t")
              .sort_values(KEY, kind="stable")
              .reset_index(drop=True))
    return validate(result), report


def reconcile(current, summary_path):
    """增量檔裝不下「刪除」：拿來源的條文總數對帳，對不上的列出來交給人判斷。"""
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    expected = pd.Series({i["code"]: i["articles"] for i in summary["items"]}, name="來源條文數")
    actual = current.groupby("pcode").size().rename("本地條文數")
    table = pd.concat([expected, actual], axis=1).fillna(0).astype(int)
    return table[table["來源條文數"] != table["本地條文數"]]


if __name__ == "__main__":
    v1 = validate(read_batch(DATA / "articles.jsonl"))
    v2 = read_batch(DATA / "09-batches" / "v2-changes.jsonl")
    print(f"v1 全量 {len(v1)} 條（驗證通過）；v2 增量 {len(v2)} 條，指紋 {fingerprint(v1)}\n")

    print("== 1. 天真的合併：concat ＋ drop_duplicates ==")
    once = pd.concat([v1, v2], ignore_index=True)
    twice = pd.concat([once, v2], ignore_index=True)
    print(f"concat 一次 {len(once)} 列，同一批再跑一次 {len(twice)} 列")
    first = once.drop_duplicates(KEY, keep="first")
    last = once.drop_duplicates(KEY, keep="last")
    replay = pd.concat([last, v1], ignore_index=True).drop_duplicates(KEY, keep="last")
    for label, df in [("keep='first'", first), ("keep='last'", last), ("keep='last' 後又重送 v1", replay)]:
        print(f"{label:20} {len(df)} 列；含 v2 修正的條文 {int((df['source_version'] == 'v2').sum())} 條")

    print("\n== 2. 壞資料要被擋下 ==")
    bad = v2.copy()
    bad.loc[0, "fetched_at"] = "2026-10-12 12:00:00"         # 少了時區
    bad.loc[1, "content"] = bad.loc[1, "content"] + "。"     # 改了內容卻沒重算雜湊
    bad = pd.concat([bad, bad.tail(1)], ignore_index=True)   # 同一條送了兩次
    try:
        apply_batch(v1, bad)
    except ValidationError as exc:
        print("ValidationError:", exc)

    print("\n== 3. 套用增量，然後重跑 ==")
    cur, report = apply_batch(v1, v2)
    print(f"第 1 次：{len(cur)} 條，{report}，指紋 {fingerprint(cur)}")
    cur2, report = apply_batch(cur, v2)
    print(f"第 2 次：{len(cur2)} 條，{report}，指紋 {fingerprint(cur2)}")
    cur3, report = apply_batch(cur2, v1)
    print(f"重送 v1：{len(cur3)} 條，{report}，指紋 {fingerprint(cur3)}")

    print("\n== 4. 對帳：增量檔看不到的刪除 ==")
    print(reconcile(cur3, DATA / "09-batches" / "v2-laws.json").to_string())
