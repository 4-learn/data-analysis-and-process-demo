"""第 17 節：條文語料的長度分布與切塊、多值欄位的 explode、通報文字的去識別。"""

import math
import re
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
CHUNK = 450        # 字元；由第 2 段的分布決定（p95 ≈ 427，取整到 450）
PHONE = re.compile(r"\(?0\d{1,3}\)?[- ]?\d{3,4}-?\d{3,4}")
WORKER_ID = re.compile(r"W\d{3}")


def estimate_tokens(text):
    """沿用第 16 節的保守粗估：非 ASCII 字元與數字各算 1、其他 ASCII 算 0.5，再乘 1.2。"""
    heavy = sum(1 for ch in text if not ch.isascii() or ch.isdigit())
    return math.ceil((heavy + (len(text) - heavy) * 0.5) * 1.2)


def read_articles():
    return pd.read_json(DATA / "articles.jsonl", lines=True, dtype=False, convert_dates=False)


def pack_lines(text, size=CHUNK):
    """依換行（項、款）切開，再把相鄰的行裝進不超過 size 的塊；單一行超過 size 才會單獨成塊。"""
    chunks, cur = [], ""
    for line in text.split("\n"):
        candidate = line if not cur else cur + "\n" + line
        if len(candidate) <= size or not cur:
            cur = candidate
        else:
            chunks.append(cur)
            cur = line
    chunks.append(cur)
    return chunks


def chunk_articles(articles, size=CHUNK):
    """一列一塊；每塊帶回到原條文的座標（pcode、slug、序號）與 source_url。"""
    out = articles[["pcode", "law_name", "slug", "article_no", "source_url", "content"]].copy()
    out["chunk"] = out["content"].map(lambda t: pack_lines(t, size))
    out["n_chunks"] = out["chunk"].map(len)
    out = out.explode("chunk", ignore_index=True)
    out["chunk_no"] = out.groupby(["pcode", "slug"]).cumcount() + 1
    out["chunk_id"] = out["pcode"] + "#" + out["slug"] + "-" + out["chunk_no"].astype(str)
    rebuilt = out.groupby(["pcode", "slug"], sort=False)["chunk"].agg("\n".join)
    original = articles.set_index(["pcode", "slug"])["content"].loc[rebuilt.index]
    if not (rebuilt == original).all():
        raise ValueError("切塊後接不回原文")
    return out.drop(columns="content")


def link_articles(reports, articles):
    """related_articles 是 list：explode 成一列一個引用，拆成 pcode／slug 接回條文。空 list 會變成 NaN，先標出來。"""
    refs = reports[["report_id", "related_articles"]].explode("related_articles")
    no_ref = refs["related_articles"].isna()
    refs = refs[~no_ref].copy()
    bad = ~refs["related_articles"].str.fullmatch(r"N\d{7}#\d+(?:-\d+)?")
    if bad.any():
        raise ValueError(f"related_articles 格式不對：{refs.loc[bad, 'related_articles'].iloc[0]!r}")
    refs[["pcode", "slug"]] = refs["related_articles"].str.split("#", expand=True)
    linked = refs.merge(articles[["pcode", "slug", "law_name", "article_no"]], on=["pcode", "slug"],
                        how="left", validate="many_to_one", indicator=True)
    missing = linked["_merge"] != "both"
    if missing.any():
        raise ValueError(f"引用的條文不存在：{linked.loc[missing, 'related_articles'].iloc[0]!r}")
    return linked.drop(columns="_merge"), int(no_ref.sum())


def deidentify(reports, roster_names):
    """名冊比對換掉人名、regex 換掉電話；回傳新表，不改原表。"""
    names = sorted(set(roster_names), key=len, reverse=True)
    pattern = "|".join(map(re.escape, names))
    out = reports.copy()
    out["text"] = out["text"].str.replace(pattern, "〔姓名〕", regex=True).str.replace(PHONE, "〔電話〕", regex=True)
    return out


def residuals(df, columns, roster_names):
    """去識別之後再掃一次：還有幾列可能指回某個人。只掃得到「已知的樣子」，掃不到名冊外的人名。"""
    names = "|".join(map(re.escape, sorted(set(roster_names), key=len, reverse=True)))
    found = {}
    for col in columns:
        s = df[col].astype(str)
        found[f"{col}：名冊人名"] = int(s.str.contains(names).sum())
        found[f"{col}：像電話的數字"] = int(s.str.contains(r"\d{3,4}[- ]?\d{3,4}").sum())
        found[f"{col}：工號"] = int(s.str.contains(WORKER_ID).sum())
    return found


def mid_line_cuts(text, size=CHUNK):
    """每 size 字一刀時，有幾刀不是落在換行上。"""
    return sum(text[p - 1] != "\n" and text[p] != "\n" for p in range(size, len(text), size))


if __name__ == "__main__":
    articles = read_articles()
    length = articles["content"].str.len()

    print("== 1. 條文長度分布（字元） ==")
    print(length.describe().round(1).to_string())
    q = length.quantile([0.5, 0.9, 0.95, 0.99]).map(math.ceil)    # 無條件進位：p95=427 代表 95% 的條文 ≤427 字
    print("分位數（進位）：" + "、".join(f"p{round(p * 100)} {v}" for p, v in q.items()))
    longest = articles.assign(chars=length).nlargest(5, "chars")
    print(longest[["law_name", "article_no", "chars"]].to_string(index=False))

    print("\n== 2. chunk size 要多大？ ==")
    for label, size in [("p90", q[0.9]), ("p95", q[0.95]), ("本節採用", CHUNK), ("p99", q[0.99])]:
        over = int((length > size).sum())
        print(f"{label:6} {size:>4} 字：{over:>3} 條（{over / len(articles):.1%}）超過、要切；"
              f"一塊估計最多 {estimate_tokens('字' * size)} token")

    print("\n== 3. 切塊：直接每 450 字一刀 vs 依換行裝箱 ==")
    fixed = articles["content"].map(lambda t: [t[i:i + CHUNK] for i in range(0, len(t), CHUNK)]).explode()
    mid_line = int(articles["content"].map(mid_line_cuts).sum())
    print(f"每 {CHUNK} 字一刀：{len(fixed)} 塊；{mid_line} 刀切在一行的中間")
    lines = articles["content"].str.split("\n").explode()
    print(f"每一行一塊：{len(lines)} 塊；中位數 {lines.str.len().median():.0f} 字，"
          f"最短 {lines.str.len().min()} 字（例如 {lines[lines.str.len() == lines.str.len().min()].iloc[0]!r}）")
    chunks = chunk_articles(articles)
    size = chunks["chunk"].str.len()
    split = int((chunks.drop_duplicates(["pcode", "slug"])["n_chunks"] > 1).sum())
    print(f"依換行裝箱 ≤{CHUNK}：{len(chunks)} 塊，{split} 條被切成多塊；最長 {size.max()} 字，每塊都接得回原文")
    print(chunks.loc[chunks["pcode"].eq("N0060014") & chunks["slug"].eq("59"), ["chunk_id", "article_no"]]
          .assign(chars=size, first=chunks["chunk"].str[:18]).to_string(index=False))
    later = chunks[chunks["chunk_no"] > 1]
    kuan = later["chunk"].str.match(r"[一二三四五六七八九十]+、")          # 款：一、二、
    mu = later["chunk"].str.match(r"（[一二三四五六七八九十]+）")           # 目：（一）（二）
    xiang = later["chunk"].str.match(r"(?:前|第[一二三四五六七八九十]+)\S*項")  # 前項、前三項、第一項
    print(f"第 2 塊以後共 {len(later)} 塊：{int((kuan | mu).sum())} 塊以款或目開頭（款 {int(kuan.sum())}、目 {int(mu.sum())}），"
          f"看不到前面的「應依下列規定辦理」；{int(xiang.sum())} 塊以「前項／第 N 項」開頭，看不到它指的那一項")
    broken = chunks[chunks["chunk"].str.count("┌") != chunks["chunk"].str.count("└")]
    print(f"表格被切成兩半的塊：{sorted(set(broken['pcode'] + '#' + broken['slug']))}")

    print("\n== 4. 多值欄位：explode 的列膨脹 ==")
    reports = pd.read_json(DATA / "events" / "near-miss-reports.jsonl", lines=True, dtype=False, convert_dates=False)
    as_text = reports["related_articles"].str.split("#")
    print(f"把 list 欄當字串：.str.split('#') 得到 {int(as_text.isna().sum())}/{len(reports)} 個 NaN；"
          f"tags.str.contains('墜落') 加總 = {reports['tags'].str.contains('墜落').sum()}，沒有錯誤訊息")
    tags = reports.explode("tags")
    both = tags.explode("related_articles")
    print(f"通報 {len(reports)} 筆 → explode tags {len(tags)} 列 → 再 explode related_articles {len(both)} 列")
    print(f"「墜落」：explode 兩次後數到 {int((both['tags'] == '墜落').sum())} 列；實際是 {int(reports['tags'].map(lambda t: '墜落' in t).sum())} 筆通報")
    linked, no_ref = link_articles(reports, articles)
    print(f"related_articles：{len(linked)} 個引用接回條文，全部對上；另有 {no_ref} 筆通報是空 list（explode 後變 NaN）")
    print(linked.groupby(["related_articles", "article_no"]).size().rename("引用次數").to_string())

    print("\n== 5. 去識別：換掉了什麼、還剩什麼 ==")
    roster = pd.read_csv(DATA / "events" / "workers.csv", dtype=str, keep_default_na=False)
    extra = pd.DataFrame([  # 在記憶體中加兩筆名冊外的通報（不寫檔）
        {"report_id": "X001", "reporter": "陳志明", "text": "水電包商的張美華師傅在二樓開口旁作業未扣安全帶，聯絡電話0912345678。"},
        {"report_id": "X002", "reporter": "陳志明", "text": "外部稽核發現開口護欄缺口，請洽 (02)2345-6789 安衛室。"},
    ])
    sample = pd.concat([reports[["report_id", "reporter", "text"]], extra], ignore_index=True)
    clean = deidentify(sample, roster["name"])
    print(f"人名替換 {int(clean['text'].str.count('〔姓名〕').sum())} 處、電話替換 {int(clean['text'].str.count('〔電話〕').sum())} 處")
    print("殘留掃描（列數）：", residuals(clean, ["text", "reporter"], roster["name"]))
    outside = clean.loc[~clean["reporter"].isin(roster["name"]), "reporter"]
    print(f"reporter 欄共 {len(clean)} 列：名冊掃描抓到 {len(clean) - len(outside)} 列，另 {len(outside)} 列不在名冊、掃不到："
          f"{sorted(set(outside))}（{'、'.join(clean.loc[outside.index, 'report_id'])}）")
    guess = f"[{''.join(sorted(set(roster['name'].str[0])))}][\u4e00-\u9fff]{{2}}"   # 「名冊姓氏＋兩個字」
    hits = articles["content"].str.findall(guess).explode().dropna()
    print(f"改用「姓氏＋兩字」regex 掃條文語料：誤判 {len(hits)} 處，例如 {hits.value_counts().index[:3].tolist()}")
    for rid in ["R036", "X001", "X002"]:
        print(f"{rid}：{clean.loc[clean['report_id'] == rid, 'text'].iloc[0]}")
