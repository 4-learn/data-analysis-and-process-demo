"""第 16 節：同一批資料，用哪種格式、留哪些欄位與列，才放得進 context 預算。"""

import math
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data" / "articles.jsonl"
QUERY = "墜落"
BUDGET = 3000              # 估計 token 上限；實際值依模型而定
KEEP = ["law_name", "article_no", "content", "source_url"]   # LLM 需要的；source_url 用來附出處


def estimate_tokens(text):
    """保守粗估，不是計數：非 ASCII 字元與數字各算 1、其他 ASCII 算 0.5，再乘 1.2 安全係數。"""
    heavy = sum(1 for ch in text if not ch.isascii() or ch.isdigit())
    light = len(text) - heavy
    return math.ceil((heavy + light * 0.5) * 1.2)


def serialize(df, fmt):
    if fmt == "csv":
        return df.to_csv(index=False)
    if fmt == "jsonl-ascii":
        return df.to_json(orient="records", lines=True)
    if fmt == "jsonl":
        return df.to_json(orient="records", lines=True, force_ascii=False)
    if fmt == "markdown":
        return df.to_markdown(index=False)
    raise ValueError(f"未知格式：{fmt}")


def fit_budget(df, budget, columns, rank_by, count=estimate_tokens, fmt="jsonl"):
    """先丟欄、再丟列；條文不截斷。回傳 (要送出的文字, 留下的列, 被丟掉的列)。"""
    missing = [c for c in columns + [rank_by] if c not in df.columns]
    if missing:
        raise ValueError(f"缺少欄位 {missing}")
    ranked = df.sort_values([rank_by, "source_url"], ascending=[False, True])
    slim = ranked[columns]
    kept = len(slim)
    while kept > 0 and count(serialize(slim.head(kept), fmt)) > budget:
        kept -= 1
    if kept == 0:
        raise ValueError(f"預算 {budget} 連一條都放不下，請提高預算或改用摘要")
    return serialize(slim.head(kept), fmt), ranked.head(kept), ranked.iloc[kept:]


if __name__ == "__main__":
    articles = pd.read_json(DATA, lines=True, dtype=False, convert_dates=False)
    hits = articles[articles["content"].str.contains(QUERY, regex=False)].copy()
    hits["hits"] = hits["content"].str.count(QUERY)
    print(f"全部 {len(articles)} 條；含「{QUERY}」{len(hits)} 條\n")

    print("== 1. 同樣 16 列、全部欄位，四種格式 ==")
    for fmt in ("csv", "jsonl-ascii", "jsonl", "markdown"):
        text = serialize(hits.drop(columns="hits"), fmt)
        print(f"{fmt:12} 字元 {len(text):>6,}  估計 token {estimate_tokens(text):>6,}")

    print(f"\n== 2. 先丟欄：只留 {KEEP} ==")
    slim = serialize(hits[KEEP], "jsonl")
    print(f"jsonl        字元 {len(slim):>6,}  估計 token {estimate_tokens(slim):>6,}  （預算 {BUDGET:,}）")

    print("\n== 3. 再丟列：依「墜落」出現次數排序，整條保留或整條丟 ==")
    text, kept, dropped = fit_budget(hits, BUDGET, KEEP, rank_by="hits")
    print(f"送出 {len(kept)} 條，估計 token {estimate_tokens(text):,}：")
    print(kept[["law_name", "article_no", "hits"]].to_string(index=False))
    print(f"丟掉 {len(dropped)} 條（要留紀錄，不是默默消失）：")
    print(", ".join(dropped["law_name"].str[:4] + dropped["article_no"]))
