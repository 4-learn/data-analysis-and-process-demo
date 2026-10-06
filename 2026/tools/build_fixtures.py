"""教師用：從爬蟲練習站的原始資料，產生本課的離線練習檔。

只用 Python 標準函式庫（學生不需要執行這支；產物已放在 data/）。

來源：4-learn/crawler-playground（MIT），固定 commit，下載後驗證 SHA-256。
產物：
  data/articles.jsonl      749 條，欄位比照爬蟲課第 16 節〈交給下游〉，含四個來源欄位
  data/02-exports/*.csv    三份「不同人、不同軟體匯出」的 CSV，給第 02 節練習讀檔
  data/03-api/N0020012/    練習站 v1 API 的兩頁原始 JSON（巢狀、分頁），與線上位元組相同，給第 03 節
  data/03-crawl/N0020012.jsonl  爬蟲課第 05／14 節那種「一部法規一個檔」的交付，給第 03 節
  data/09-batches/v2-changes.jsonl  練習站第 2 版的增量交付（修改 4、新增 1），給第 09 節
  data/09-batches/v2-laws.json      練習站 v2 API 的法規總覽（含各法條文數），與線上位元組相同，給第 09 節
  data/MANIFEST.json       產物雜湊、來源 commit 與產生環境

同一份來源每次產生的檔案位元組完全相同，講義裡貼的輸出不會因重建而改變。

    python3 tools/build_fixtures.py            # 需要網路（只抓一次 raw JSON）
    python3 tools/build_fixtures.py --source laws.v1.json   # 已有來源檔時離線產生
"""

import argparse
import csv
import hashlib
import io
import json
import platform
import sys
import urllib.request
from pathlib import Path

COMMIT = "15279335fad7ea22399794efd178d55e7a16d8da"
SOURCE_URL = f"https://raw.githubusercontent.com/4-learn/crawler-playground/{COMMIT}/data/laws.v1.json"
SOURCE_SHA256 = "9a5404def3432701b29aee7bc72569782e5726f4e2b4ee54dba4350da1a8c1ce"
SITE = "https://4-learn.github.io/crawler-playground"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# 第 02 節的三份匯出：刻意對應真實辦公室會遇到的三種情況。
#   - 勞動基準法：Excel 存的「CSV UTF-8」，帶 BOM；slug 有 9-1 這種條次
#   - 大量解僱勞工保護法：工程師用程式匯出，UTF-8 無 BOM；slug 全是數字
#   - 勞資爭議處理法：舊系統匯出，Big5（cp950）
EXPORTS = [
    ("labor-standards.csv", "N0030001", "utf-8-sig"),
    ("mass-layoff.csv", "N0020012", "utf-8"),
    ("labor-disputes.csv", "N0020007", "cp950"),
]
# 第 03 節：選一部會分頁的小法規（21 條 → 20＋1），API 結構照抄練習站 build.py 的 build_v1_api()
API_PCODE = "N0020012"
API_PAGE_SIZE = 20

# 第 09 節：練習站第 2 版的刻意變動，照抄 crawler-playground build.py 的 V2_MODIFY／V2_DELETE／V2_ADD
V2_MODIFY = [("N0030001", "24"), ("N0030001", "38"), ("N0060001", "6"), ("N0030014", "15")]
V2_DELETE = [("N0020012", "21")]
V2_FAKE_SENTENCE = "（本句為爬蟲練習站第 2 版虛構修正，用於練習變動偵測，非真實法條。）"
V2_ADD = {"pcode": "N0030001", "after": "86", "slug": "86-1", "article_no": "第 86-1 條",
          "content": "本條為爬蟲練習站第 2 版虛構新增之條文，用於練習偵測新增資料，非真實法條。"}
V2_FETCHED_AT = "2026-10-12T04:00:00+00:00"  # 模擬的第二次交付時間（固定值，不是實際抓取時間）

EXPORT_FIELDS = ["pcode", "law_name", "slug", "article_no", "chapter", "content", "modified_date"]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_source(path: str | None) -> tuple[dict, bytes]:
    if path:
        raw = Path(path).read_bytes()
    else:
        with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
            raw = resp.read()
    actual = sha256(raw)
    if actual != SOURCE_SHA256:
        raise SystemExit(f"來源雜湊不符：預期 {SOURCE_SHA256}，實得 {actual}。來源已變，請先人工確認再改 COMMIT。")
    return json.loads(raw.decode("utf-8")), raw


def article_row(law: dict, a: dict, fetched_at: str, version: str = "v1") -> dict:
    url = (f"{SITE}/v1/laws/{law['pcode']}/articles/{a['slug']}.html" if version == "v1"
           else f"{SITE}/v2/laws/{law['pcode']}/a/{a['slug']}.html")
    return {
        "pcode": law["pcode"],
        "law_name": law["name"],
        "slug": a["slug"],
        "article_no": a["article_no"],
        "chapter": a["chapter"],
        "content": a["content"],
        "source_url": url,
        "fetched_at": fetched_at,
        "content_hash": sha256(a["content"].encode("utf-8")),
        "source_version": version,
    }


def jsonl(rows: list[dict]) -> bytes:
    return ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n").encode("utf-8")


def build_articles(src: dict, only: str | None = None) -> bytes:
    fetched_at = src["source"]["fetched_at"]  # 固定值，讓產物可重現
    return jsonl([article_row(law, a, fetched_at)
                  for law in src["laws"] if only in (None, law["pcode"]) for a in law["articles"]])


def build_api_pages(src: dict, pcode: str) -> dict[str, bytes]:
    """與練習站 build_v1_api() 相同的結構與序列化方式（indent=1、ensure_ascii=False）。"""
    law = next(x for x in src["laws"] if x["pcode"] == pcode)
    arts = law["articles"]
    chunks = [arts[i:i + API_PAGE_SIZE] for i in range(0, len(arts), API_PAGE_SIZE)]
    pages = {}
    for n, chunk in enumerate(chunks, 1):
        obj = {
            "version": 1, "pcode": law["pcode"], "name": law["name"], "page": n,
            "total_pages": len(chunks), "total": len(arts),
            "next": f"page-{n + 1}.json" if n < len(chunks) else None,
            "articles": [{k: a[k] for k in ("slug", "article_no", "chapter", "section", "content")} for a in chunk],
        }
        pages[f"03-api/{pcode}/page-{n}.json"] = (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    return pages


def build_v2_changes(src: dict) -> bytes:
    """增量交付：只含 v2 修改與新增的條文。刪除不會出現在增量檔裡——這正是第 09 節要討論的。"""
    laws = {law["pcode"]: law for law in src["laws"]}
    rows = []
    for pcode, slug in V2_MODIFY:
        a = dict(next(x for x in laws[pcode]["articles"] if x["slug"] == slug))
        a["content"] = a["content"] + "\n" + V2_FAKE_SENTENCE
        rows.append(article_row(laws[pcode], a, V2_FETCHED_AT, "v2"))
    target = laws[V2_ADD["pcode"]]
    after = next(x for x in target["articles"] if x["slug"] == V2_ADD["after"])
    new = {k: V2_ADD[k] for k in ("slug", "article_no", "content")} | {"chapter": after["chapter"]}
    rows.append(article_row(target, new, V2_FETCHED_AT, "v2"))
    return jsonl(rows)


def build_v2_summary(src: dict) -> bytes:
    """與練習站 build_v2() 的 api/laws.json 相同：條文數已反映 v2 的刪除與新增。"""
    counts = {law["pcode"]: len(law["articles"]) for law in src["laws"]}
    counts[V2_ADD["pcode"]] += 1
    for pcode, _ in V2_DELETE:
        counts[pcode] -= 1
    obj = {"version": 2, "items": [
        {"code": l["pcode"], "title": l["name"], "updated": l["modified_date"], "articles": counts[l["pcode"]]}
        for l in src["laws"]]}
    return (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def build_export(src: dict, pcode: str, encoding: str) -> bytes:
    law = next(x for x in src["laws"] if x["pcode"] == pcode)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=EXPORT_FIELDS, lineterminator="\r\n")
    w.writeheader()
    for a in law["articles"]:
        w.writerow({
            "pcode": law["pcode"], "law_name": law["name"], "slug": a["slug"],
            "article_no": a["article_no"], "chapter": a["chapter"],
            "content": a["content"], "modified_date": law["modified_date"],
        })
    return buf.getvalue().encode(encoding)  # cp950 存不下的字會在這裡直接報錯，不默默替換


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", help="已下載的 laws.v1.json；省略則從固定 commit 下載")
    args = ap.parse_args()

    src, _ = load_source(args.source)
    outputs = {"articles.jsonl": build_articles(src)}
    for name, pcode, enc in EXPORTS:
        outputs[f"02-exports/{name}"] = build_export(src, pcode, enc)
    outputs.update(build_api_pages(src, API_PCODE))
    outputs[f"03-crawl/{API_PCODE}.jsonl"] = build_articles(src, only=API_PCODE)
    outputs["09-batches/v2-changes.jsonl"] = build_v2_changes(src)
    outputs["09-batches/v2-laws.json"] = build_v2_summary(src)

    for rel, data in outputs.items():
        (DATA / rel).parent.mkdir(parents=True, exist_ok=True)
        (DATA / rel).write_bytes(data)

    manifest = {
        "kind": "teacher-fixture",
        "source": {"repo": "4-learn/crawler-playground", "commit": COMMIT, "license": "MIT",
                   "url": SOURCE_URL, "sha256": SOURCE_SHA256,
                   "upstream": src["source"]["name"], "upstream_update_date": src["source"]["api_update_date"]},
        "caveat": "條文取自練習站，可能經刻意修改以供練習，不具法律效力。fetched_at 為練習站抓取官方 API 的時間，不是學生爬取時間。"
                  f"09-batches 的 fetched_at（{V2_FETCHED_AT}）是模擬的第二次交付時間；內容依練習站 build.py 的 V2_MODIFY／V2_ADD 產生。",
        "exports": [{"file": f"02-exports/{n}", "pcode": p, "encoding": e} for n, p, e in EXPORTS],
        "files": {rel: {"bytes": len(d), "sha256": sha256(d)} for rel, d in sorted(outputs.items())},
        "environment": {"python": platform.python_version(), "generator": "tools/build_fixtures.py"},
    }
    (DATA / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for rel, d in sorted(outputs.items()):
        print(f"{rel:32} {len(d):>8} bytes  {sha256(d)[:12]}")


if __name__ == "__main__":
    sys.exit(main())
