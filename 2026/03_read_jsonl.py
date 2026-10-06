"""第 03 節：接手爬蟲課的 JSONL 與 API 的巢狀 JSON，而且不弄丟來源。"""

import hashlib
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
CRAWL = DATA / "03-crawl" / "N0020012.jsonl"
API = DATA / "03-api" / "N0020012"
API_URL = "https://4-learn.github.io/crawler-playground/v1/api/laws/N0020012/"
PROVENANCE = ["source_url", "fetched_at", "content_hash", "source_version"]


def read_jsonl(path):
    """讀爬蟲課交付的 JSONL：不讓 pandas 猜型別、不讓它改寫時間字串。"""
    df = pd.read_json(path, lines=True, dtype=False, convert_dates=False)
    check_provenance(df)
    return df


def check_provenance(df):
    missing = [c for c in PROVENANCE if c not in df.columns]
    if missing:
        raise ValueError(f"缺少來源欄位 {missing}")
    empty = [c for c in PROVENANCE if df[c].isna().any() or (df[c] == "").any()]
    if empty:
        raise ValueError(f"來源欄位有空值 {empty}")
    no_tz = ~df["fetched_at"].str.contains(r"(?:[+-]\d\d:\d\d|Z)$")
    if no_tz.any():
        raise ValueError(f"fetched_at 沒有時區 {int(no_tz.sum())} 筆，例如 {df.loc[no_tz, 'fetched_at'].iloc[0]!r}")
    actual = df["content"].map(lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest())
    bad = actual != df["content_hash"]
    if bad.any():
        raise ValueError(f"content_hash 與內容不符 {int(bad.sum())} 筆")


def flatten_api(folder, first="page-1.json"):
    """從第一頁開始照 next 走完，把每頁的 articles 攤平成一列一條。"""
    frames, name, seen = [], first, set()
    while name:
        if name in seen:
            raise ValueError(f"next 形成迴圈：{name}")
        seen.add(name)
        page = json.loads((Path(folder) / name).read_text(encoding="utf-8"))
        rows = pd.json_normalize(page, record_path="articles", meta=["pcode", "name", "total"])
        rows["source_url"] = API_URL + name   # 這一列是從哪個網址來的
        frames.append(rows)
        name = page["next"]
    df = pd.concat(frames, ignore_index=True).rename(columns={"name": "law_name"})
    expected = int(df["total"].iloc[0])
    if len(df) != expected:
        raise ValueError(f"API 說 total={expected}，實際攤平 {len(df)} 條")
    return df.drop(columns="total")


if __name__ == "__main__":
    print("== 1. 一行 read_json，再存回去 ==")
    naive = pd.read_json(CRAWL, lines=True)
    print(f"{len(naive)} 列；slug={naive['slug'].dtype}, fetched_at={naive['fetched_at'].dtype}")
    original = [json.loads(line) for line in CRAWL.read_text(encoding="utf-8").splitlines()]
    written = [json.loads(line) for line in naive.to_json(orient="records", lines=True, force_ascii=False).splitlines()]
    changed = sorted({k for o, w in zip(original, written) for k in o if o[k] != w[k]})
    print(f"存回去後 {sum(o != w for o, w in zip(original, written))} 列被改寫，欄位：{changed}")
    print(f"第 1 列 slug {original[0]['slug']!r} → {written[0]['slug']!r}；"
          f"fetched_at {original[0]['fetched_at']!r} → {written[0]['fetched_at']!r}")

    print("\n== 2. 先決定型別，再讀 ==")
    crawl = read_jsonl(CRAWL)
    print(f"{len(crawl)} 列；slug={crawl['slug'].dtype}；來源欄位齊全，content_hash 全數相符")
    print(f"fetched_at 原樣保留：{crawl['fetched_at'].iloc[0]}")

    print("\n== 3. API 的巢狀 JSON ==")
    page1 = pd.read_json(API / "page-1.json")
    print(f"read_json 直接讀第 1 頁：{page1.shape[0]} 列 × {page1.shape[1]} 欄；articles 欄裝的是 {type(page1['articles'].iloc[0]).__name__}")
    api = flatten_api(API)
    print(f"照 next 走完攤平：{len(api)} 列；欄位 {list(api.columns)}")

    print("\n== 4. 兩個來源互相核對 ==")
    api["content_hash"] = api["content"].map(lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest())
    both = crawl.merge(api, on=["pcode", "slug"], suffixes=("_crawl", "_api"), validate="one_to_one")
    same = (both["content_hash_crawl"] == both["content_hash_api"]).sum()
    print(f"以 (pcode, slug) 對上 {len(both)} 條；內容雜湊相同 {same} 條")
    print(both[["slug", "source_url_crawl", "source_url_api"]].tail(2).to_string(index=False))
