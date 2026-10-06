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
