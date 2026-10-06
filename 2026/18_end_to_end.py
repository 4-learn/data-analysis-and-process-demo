"""第 18 節：從 events.jsonl 到給 LLM 的摘要——一支可重跑、會擋壞資料的程式。

讀取 → 清理 → 驗證 → 彙總 → 濃縮 → 序列化＋預算檢查。
每一步是一個函式；任何一步發現問題就拋例外，不產出摘要。
"""

import hashlib
import io
import json
import math
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data" / "events"
REQUIRED = ["event_id", "zone", "camera_id", "worker_id", "event_type", "confidence", "event_time", "ingested_at"]
NULLABLE = {"confidence"}          # cam-08 舊模型沒記錄；其他必要欄位一律不准是空值
TOP_K = 3
BURST = 5           # 同一人同一天違規達 5 筆列為異常（看過分布才定的，見第 15 節）
BUDGET = 1500       # 摘要的估計 token 上限（LLM 組給的數字）


class PipelineError(ValueError):
    """資料不符合規格或超出預算：整批擋下，不產出任何摘要。"""


def estimate_tokens(text):
    """第 16 節的保守粗估：非 ASCII 字元與數字各算 1、其他 ASCII 算 0.5，再乘 1.2。"""
    heavy = sum(1 for ch in text if not ch.isascii() or ch.isdigit())
    return math.ceil((heavy + (len(text) - heavy) * 0.5) * 1.2)


# ---------------------------------------------------------------- 1. 讀取

def read_events(source):
    """不讓 pandas 猜型別、不看欄名轉日期（第 02、03 節），讀完立刻檢查欄位與型別。"""
    raw = pd.read_json(source, lines=True, dtype=False, convert_dates=False)
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        raise PipelineError(f"缺少欄位 {missing}")
    for col in REQUIRED:
        if col not in NULLABLE and raw[col].isna().any():     # JSONL 某一行少了這個鍵 → 那一格是 NaN
            raise PipelineError(f"{col} 有空值（某一行少了這個鍵）：第 {raw.index[raw[col].isna()][0] + 1} 行")
    conf = raw["confidence"].dropna()
    not_num = ~conf.map(type).isin([int, float])      # 整欄都是 null 時 pandas 3 讀成 object，所以逐格看
    if not_num.any():
        raise PipelineError(f"confidence 不是數字：第 {not_num.index[not_num][0] + 1} 行 {conf[not_num].iloc[0]!r}")
    raw["confidence"] = raw["confidence"].astype(float)
    for col in set(REQUIRED) - NULLABLE:
        not_str = ~raw[col].map(type).eq(str)
        if not_str.any():
            raise PipelineError(f"{col} 不是字串：第 {raw.index[not_str][0] + 1} 行 {raw.loc[not_str, col].iloc[0]!r}")
    return raw


def read_event_types():
    types = pd.read_csv(DATA / "event-types.csv", dtype=str, keep_default_na=False)
    return set(types["event_type"]), set(types.loc[types["is_violation"] == "true", "event_type"])


# ---------------------------------------------------------------- 2. 清理

def clean(raw):
    """只去掉「重送」：除了 ingested_at 以外完全相同的列。修正 cam-02 的百分比。每一項都記進 audit。"""
    audit = []
    same = [c for c in raw.columns if c != "ingested_at"]
    arrived = pd.to_datetime(raw["ingested_at"], utc=True, format="ISO8601")
    raw = raw.iloc[arrived.argsort(kind="stable")]         # 依到達時間排，「留最先到達」才不看輸入順序
    resend = raw.duplicated(subset=same, keep="first")
    if resend.any():
        audit.append({"step": "去重", "rule": "除 ingested_at 外完全相同，留最先到達的一筆",
                      "rows": int(resend.sum()), "cameras": sorted(raw.loc[resend, "camera_id"].unique())})
    ev = raw[~resend].copy()
    pct = ev["confidence"] > 1
    if pct.any():
        ev.loc[pct, "confidence"] = ev.loc[pct, "confidence"] / 100
        audit.append({"step": "修正", "rule": "confidence > 1 視為百分比，÷100",
                      "rows": int(pct.sum()), "cameras": sorted(ev.loc[pct, "camera_id"].unique())})
    ev["conf_fixed"] = pct
    return ev.reset_index(drop=True), audit


# ---------------------------------------------------------------- 3. 驗證

def validate(ev, known_types, violation_types):
    """業務規則（清理之後）。全部通過才回傳加了 date／week／late／is_violation 的新表。"""
    dup = ev["event_id"].duplicated(keep=False)
    if dup.any():
        raise PipelineError(f"業務鍵 event_id 不唯一（內容不同的同一事件）：{ev.loc[dup, 'event_id'].iloc[0]}")
    for col in ("event_time", "ingested_at"):
        no_tz = ~ev[col].str.contains(r"(?:[+-]\d\d:\d\d|Z)$")
        if no_tz.any():
            raise PipelineError(f"{col} 沒有時區：{ev.loc[no_tz, 'event_id'].iloc[0]} {ev.loc[no_tz, col].iloc[0]!r}")
    unknown = ~ev["event_type"].isin(known_types)
    if unknown.any():
        raise PipelineError(f"未知 event_type {sorted(ev.loc[unknown, 'event_type'].unique())}，白名單 {sorted(known_types)}")
    bad = ev["confidence"].notna() & ~ev["confidence"].between(0, 1)
    if bad.any():
        raise PipelineError(f"confidence 超出 0–1：{ev.loc[bad, 'event_id'].iloc[0]}")
    t = pd.to_datetime(ev["event_time"], format="ISO8601", utc=True).dt.tz_convert("Asia/Taipei")
    arrived = pd.to_datetime(ev["ingested_at"], format="ISO8601", utc=True)
    return ev.assign(
        date=t.dt.strftime("%Y-%m-%d"),
        week=(t.dt.normalize() - pd.to_timedelta(t.dt.weekday, unit="D")).dt.strftime("%Y-%m-%d"),
        late=(arrived - t) > pd.Timedelta(hours=1),
        is_violation=ev["event_type"].isin(violation_types),
    )


# ---------------------------------------------------------------- 4. 彙總

def weekly(ev):
    """每人每週一列。辨識不到臉的事件記在 '(未辨識)' 名下，不丟掉。"""
    v = ev.assign(who=ev["worker_id"].replace("", "(未辨識)"))
    bad = v[v["is_violation"]]
    keys = ["who", "week"]
    table = pd.concat([
        v.groupby(keys).size().rename("events"),
        bad.groupby(keys).size().rename("violations"),
        bad.groupby(keys)["date"].nunique().rename("violation_days"),
        bad.groupby(keys + ["date"]).size().groupby(keys).max().rename("max_per_day"),
    ], axis=1).fillna(0).astype(int).reset_index()
    return table.sort_values(keys, ignore_index=True)


# ---------------------------------------------------------------- 5. 濃縮

def condense(ev, table, audit):
    """十行左右的摘要；每列的 key 可直接 ev.query(key) 回到原始事件，n 必須等於查到的筆數。"""
    rows = []

    def add(kind, item, key, note=""):
        n = len(ev.query(key))
        if n == 0:
            raise PipelineError(f"摘要列追不回任何事件：{key}")
        rows.append({"kind": kind, "item": item, "n": n, "note": note, "key": key})

    people = table[table["who"] != "(未辨識)"].groupby("who")["violations"].sum()
    people = people[people > 0].sort_values(ascending=False, kind="stable")   # 同分依工號，結果才固定
    for who in people.head(TOP_K).index:
        days = int(table.loc[table["who"] == who, "violation_days"].sum())
        add("top_worker", who, f"is_violation and worker_id == '{who}'", f"{days} 天有違規")
    if (ev["is_violation"] & (ev["worker_id"] == "")).any():
        add("unidentified", "(未辨識)", "is_violation and worker_id == ''", "辨識不到臉，不列入排名")
    site = table.groupby("week")[["events", "violations"]].sum()
    if len(site) >= 2:                                  # 只有一週就沒有「週對週」
        last, prev = site.index[-1], site.index[-2]
        rate = site["violations"] / site["events"]
        add("trend", f"week {last}", f"is_violation and week == '{last}'",
            f"前週 {site.loc[prev, 'violations']} 筆；違規率 {rate[prev]:.1%}→{rate[last]:.1%}")
    named = table[table["who"] != "(未辨識)"]          # 未辨識是很多人，單日筆數不代表同一人連續違規
    for _, r in named[named["max_per_day"] >= BURST].iterrows():
        burst = ev[ev["is_violation"] & (ev["worker_id"] == r["who"]) & (ev["week"] == r["week"])]
        day = burst.groupby("date").size().idxmax()
        hit = burst[burst["date"] == day]
        add("anomaly", f"{r['who']} {day}", f"is_violation and worker_id == '{r['who']}' and date == '{day}'",
            f"{hit['event_time'].min()[11:16]}–{hit['event_time'].max()[11:16]} "
            + "、".join(sorted(hit["event_type"].unique())))
    for a in audit:
        if a["step"] == "修正":
            add("data_note", "confidence 修正", "conf_fixed", f"{','.join(a['cameras'])} {a['rule']}")
    if ev["late"].any():
        late = ev[ev["late"]]
        resent = sum(a["rows"] for a in audit if a["step"] == "去重")
        add("data_note", "補傳", "late", f"{','.join(sorted(late['camera_id'].unique()))} 隔天才到；重送 {resent} 筆已去重")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 6. 序列化＋預算

def serialize(summary, budget=BUDGET):
    text = summary.to_json(orient="records", lines=True, force_ascii=False)
    tokens = estimate_tokens(text)
    if tokens > budget:
        raise PipelineError(f"摘要估計 {tokens} token，超過預算 {budget}")
    return text, tokens


def run(source, budget=BUDGET, checks=()):
    """整條管線。checks 是額外的驗證函式（收 ev、不合格就拋 PipelineError）。回傳 (摘要 JSONL, 估計 token, 每人每週表, audit)。"""
    known, violation = read_event_types()
    ev, audit = clean(read_events(source))
    ev = validate(ev, known, violation)
    for check in checks:
        check(ev)
    table = weekly(ev)
    text, tokens = serialize(condense(ev, table, audit), budget)
    return text, tokens, table, audit


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def broken(lines, line_no, **changes):
    """在記憶體中複製一份並弄壞第 line_no 行（不寫檔）。changes 的值為 None 代表刪掉該欄。"""
    out = list(lines)
    rec = json.loads(out[line_no])
    for k, v in changes.items():
        if v is None:
            rec.pop(k, None)
        else:
            rec[k] = v
    out[line_no] = json.dumps(rec, ensure_ascii=False)
    return io.StringIO("\n".join(out) + "\n")


if __name__ == "__main__":
    path = DATA / "events.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()

    print("== 1. AI 的一行版：壞資料照樣產出摘要 ==")
    for label, src in [("原始檔", path),
                       ("第 6 行少了時區", broken(lines, 5, event_time="2026-08-31T07:30:00")),
                       ("第 6 行 event_type='no_vest'", broken(lines, 5, event_type="no_vest"))]:
        df = pd.read_json(src, lines=True)
        top = df[df["event_type"] != "ppe_ok"].groupby("worker_id").size().nlargest(2).to_dict()
        kind = "日期" if pd.api.types.is_datetime64_any_dtype(df["event_time"]) else "文字"
        print(f"{label:24} event_time 是{kind}  違規 {int((df['event_type'] != 'ppe_ok').sum())}  {top}")

    print("\n== 2. 清理與 audit ==")
    known, violation = read_event_types()
    raw = read_events(path)
    ev, audit = clean(raw)
    for a in audit:
        print(a)
    print(f"{len(raw)} 列 → {len(ev)} 列；event_id 唯一：{ev['event_id'].is_unique}")

    print("\n== 3. 驗證通過，彙總成每人每週 ==")
    ev = validate(ev, known, violation)
    table = weekly(ev)
    roster = pd.read_csv(DATA / "workers.csv", dtype=str, keep_default_na=False)
    absent = sorted(set(roster["worker_id"]) - set(table["who"]))
    print(f"{len(table)} 列；違規合計 {table['violations'].sum()}，與事件表 {int(ev['is_violation'].sum())} 筆一致")
    print(f"名冊 {roster['worker_id'].nunique()} 人，表上 {table['who'].nunique() - 1} 人＋(未辨識)；不在表上：{absent[0]}–{absent[-1]} 共 {len(absent)} 人")
    print(table[table["who"].isin(["W041", "(未辨識)"])].to_string(index=False))

    print("\n== 4. 濃縮成摘要，序列化並檢查預算 ==")
    summary = condense(ev, table, audit)
    text, tokens = serialize(summary)
    print(text, end="")
    print(f"{len(summary)} 行、{len(text):,} 字元、估計 {tokens:,} token（預算 {BUDGET:,}）")

    print("\n== 5. 重跑兩次，指紋相同 ==")
    runs = [run(path)[0], run(path)[0], run(io.StringIO("\n".join(reversed(lines)) + "\n"))[0]]
    for label, out in zip(["第 1 次", "第 2 次", "輸入倒序"], runs):
        print(f"{label}  {fingerprint(out)}")

    print("\n== 6. 故意餵壞資料：全部擋下 ==")
    first = json.loads(lines[0])
    cases = [
        ("少了時區", broken(lines, 5, event_time="2026-08-31T07:30:00")),
        ("未知 event_type", broken(lines, 5, event_type="no_vest")),
        ("缺欄位", broken(lines, 5, worker_id=None)),
        ("同 event_id 內容不同", broken(lines, 5, event_id=first["event_id"])),
        ("confidence 是字串", broken(lines, 5, confidence="0.8")),
        ("confidence 超出範圍", broken(lines, 5, confidence=-0.3)),
    ]
    for label, src in cases:
        try:
            run(src)
            print(f"{label:18} 沒擋下！")
        except PipelineError as e:
            print(f"{label:18} 擋下：{e}")
    try:
        run(path, budget=500)
    except PipelineError as e:
        print(f"{'預算只有 500':18} 擋下：{e}")
