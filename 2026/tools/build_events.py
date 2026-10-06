"""教師用：產生本課的合成「工地 AI 攝影機事件」練習資料（第 01、05–08、10–15、17–18 節共用）。

只用 Python 標準函式庫；固定亂數種子，**同一版 Python 每次產生的位元組完全相同**（已於 3.10／3.11 比對）。
全部為合成資料：人名、電話、事件都是虛構的，不對應任何真實工地或人員。

產物（data/events/）：
  events.jsonl          工地 AI 攝影機事件，一行一筆，**檔案順序 = 到達順序**（不是發生順序）
  workers.csv           人員名冊（含沒有任何事件的人，以及一位中途換承攬商、出現兩列的人）
  event-types.csv       事件類型對照：中文名稱、是否違規、對應法條（pcode＋slug，可接 articles.jsonl）
  dashboard-export.csv  廠商儀表板匯出的同一批事件（第 1 週）：中文欄名、百分比字串、斜線日期
  near-miss-reports.jsonl  主管填寫的虛驚事件通報（自由文字，含人名與電話；第 17 節去識別練習）
  MANIFEST.json         產物雜湊與刻意埋入的狀況清單

刻意埋入、講義會用到的狀況（全部記在 MANIFEST 的 "planted"）：
  - event_time 是工地當地時間（+08:00）；ingested_at 是伺服器收到的時間（UTC）。
    07:00–07:59 的事件在 UTC 是「前一天」。
  - cam-05 在 2026-09-10 10:00 後斷線（cam-06 停機保養），當天的事件隔天早上才補傳，而且**補傳了兩次**（同 event_id 兩列）。
  - cam-08 跑舊模型 ppe-v2，**不輸出 confidence**（缺值＝沒記錄）。
  - cam-02 韌體在 2026-09-15～17 把 confidence 輸出成百分比（例如 87.0，**異常＝bug**）。
  - W041 在 2026-09-22 於施工架被偵測到大量未掛安全帶（**異常＝真的出事，不能清掉**）。
  - 辨識不到臉時 worker_id 為空（事件仍然發生了）。
  - handled_at：違規被主管處理的時間；沒處理是空值（缺值＝沒發生）；非違規事件也是空值（缺值＝不適用）。
  - 週日停工，沒有任何事件。

    python3 tools/build_events.py
"""

import csv
import hashlib
import io
import json
import platform
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "events"
SEED = 20261005
TPE = timezone(timedelta(hours=8))
START = date(2026, 8, 31)          # 週一
DAYS = 27                          # 到 2026-09-26（週六）；週日停工
SITE = "示範工地"

ZONES = {  # zone: (中文, 攝影機, 會出現的事件與基礎機率)
    "Z1": ("出入口", ["cam-01", "cam-02"], {"no_helmet": 0.10}),
    "Z2": ("鋼構組立", ["cam-03", "cam-04"], {"no_helmet": 0.06, "no_harness": 0.10}),
    "Z3": ("開挖區", ["cam-05", "cam-06"], {"no_helmet": 0.05, "restricted_entry": 0.08}),
    "Z4": ("施工架", ["cam-07", "cam-08"], {"no_helmet": 0.05, "no_harness": 0.12}),
}
EVENT_TYPES = [  # event_type, 中文, is_violation, pcode, slug, 依據摘要
    ("ppe_ok", "防護具正確", False, "", "", ""),
    ("no_helmet", "未戴安全帽", True, "N0060014", "11-1", "進入營繕工程工作場所應正確戴用安全帽"),
    ("no_harness", "高處未使用安全帶", True, "N0060014", "19", "高度二公尺以上有墜落之虞且防護設備開啟時應使用安全帶"),
    ("restricted_entry", "跨越警示線", True, "N0060014", "24", "作業進行中應禁止勞工跨越警示線"),
]
CONTRACTORS = {"甲營造": ["Z1", "Z3"], "乙鋼構": ["Z2", "Z4"], "丙土木": ["Z3", "Z1"]}
TRADES = {"Z1": "物料搬運", "Z2": "鋼構工", "Z3": "開挖工", "Z4": "施工架工"}
SURNAMES = "陳林黃張李王吳劉蔡楊許鄭謝郭洪曾邱廖賴徐"
GIVEN = ["志明", "淑芬", "建宏", "雅婷", "俊傑", "美玲", "家豪", "怡君", "冠宇", "佩珊",
         "宗翰", "惠如", "承恩", "欣怡", "柏翰", "郁婷", "彥廷", "靜宜", "國華", "秀英"]


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def iso_local(dt: datetime) -> str:
    return dt.astimezone(TPE).isoformat(timespec="seconds")


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def build_workers(rng: random.Random) -> list[dict]:
    names, rows = set(), []
    contractors = list(CONTRACTORS)
    for i in range(1, 61):
        while True:
            name = rng.choice(SURNAMES) + rng.choice(GIVEN)
            if name not in names:
                names.add(name)
                break
        contractor = contractors[(i - 1) % 3]
        zone = CONTRACTORS[contractor][rng.random() < 0.3]
        rows.append({"worker_id": f"W{i:03d}", "name": name, "contractor": contractor,
                     "trade": TRADES[zone], "home_zone": zone,
                     "valid_from": "2026-08-31", "valid_to": ""})
    # W023 在 09-14 從甲營造轉到丙土木：名冊有兩列（第 14 節 fan-out）
    w23 = next(r for r in rows if r["worker_id"] == "W023")
    w23["valid_to"] = "2026-09-13"
    rows.insert(rows.index(w23) + 1, dict(w23, contractor="丙土木", valid_from="2026-09-14", valid_to=""))
    # W041 是施工架工（第 08 節的真實異常）
    w41 = next(r for r in rows if r["worker_id"] == "W041")
    w41.update(contractor="乙鋼構", trade=TRADES["Z4"], home_zone="Z4")
    return rows


def build_events(rng: random.Random, workers: list[dict]) -> tuple[list[dict], dict]:
    active = {}
    for w in workers:
        active.setdefault(w["worker_id"], w)          # 第一列即可決定工區
    ids = list(active)
    absent_all = set(ids[-8:])                        # W053–W060：新進／內勤，整段期間沒有任何事件
    propensity = {wid: 1.0 for wid in ids}
    for wid in ("W007", "W018", "W029", "W041", "W044"):
        propensity[wid] = 3.5                         # 屢次違規者（第 07、12、13 節）
    rows, seq = [], {}

    def emit(cam, zone, wid, etype, t_event, delay_s, *, model="ppe-v3", conf=None):
        day = t_event.astimezone(TPE).strftime("%Y%m%d")
        seq[(cam, day)] = seq.get((cam, day), 0) + 1
        eid = f"{cam}-{day}-{seq[(cam, day)]:04d}"
        violation = etype != "ppe_ok"
        if conf is None and model == "ppe-v3":
            conf = round(rng.uniform(0.35, 0.99) if violation else rng.uniform(0.60, 0.99), 2)
        handled = ""
        if violation and conf is not None and conf >= 0.6 and rng.random() < 0.7:
            handled = iso_local(t_event + timedelta(minutes=rng.randint(4, 55)))
        if violation and model == "ppe-v2" and rng.random() < 0.6:
            handled = iso_local(t_event + timedelta(minutes=rng.randint(4, 55)))
        rows.append({
            "event_id": eid, "site": SITE, "zone": zone, "camera_id": cam, "model_version": model,
            "worker_id": wid, "event_type": etype, "confidence": conf,
            "event_time": iso_local(t_event), "ingested_at": iso_utc(t_event + timedelta(seconds=delay_s)),
            "handled_at": handled, "snapshot": f"snapshots/{cam}/{eid}.jpg",
        })
        return rows[-1]

    for d in range(DAYS):
        day = START + timedelta(days=d)
        if day.weekday() == 6:
            continue
        detections = []
        for wid in ids:
            if wid in absent_all or rng.random() < 0.12:
                continue
            zone = active[wid]["home_zone"] if rng.random() < 0.85 else rng.choice(sorted(ZONES))
            for _ in range(rng.choice([1, 1, 2, 2, 2, 3, 3, 4])):
                detections.append((zone, wid))
        for _ in range(rng.randint(10, 22)):         # 辨識不到臉的偵測
            detections.append((rng.choice(sorted(ZONES)), ""))
        for zone, wid in detections:
            hour = rng.choices(range(7, 17), weights=[6, 10, 10, 9, 4, 8, 10, 10, 9, 6])[0]
            t = datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), rng.randint(0, 59), tzinfo=TPE)
            cam = rng.choice(ZONES[zone][1])
            if zone == "Z3" and day == date(2026, 9, 10):
                cam = "cam-05"                        # cam-06 當天停機保養，開挖區只剩 cam-05
            etype = "ppe_ok"
            p = propensity.get(wid, 1.6)
            for kind, base in ZONES[zone][2].items():
                if rng.random() < base * p:
                    etype = kind
                    break
            model = "ppe-v2" if cam == "cam-08" else "ppe-v3"
            conf = None
            if cam == "cam-02" and date(2026, 9, 15) <= day <= date(2026, 9, 17):
                conf = float(rng.randint(40, 99))     # 韌體 bug：百分比
            if cam == "cam-08":
                conf = None
            delay = rng.randint(1, 20)
            if cam == "cam-05" and day == date(2026, 9, 10) and hour >= 10:
                resend = datetime(2026, 9, 11, 9, 5, 0, tzinfo=TPE)
                delay = int((resend - t).total_seconds()) + rng.randint(0, 50)
            emit(cam, zone, wid, etype, t, delay, model=model, conf=conf)
    # W041 在 09-22 下午的施工架：同一段時間被連續偵測未掛安全帶（真的危險，不是雜訊）
    for k in range(18):
        t = datetime(2026, 9, 22, 14, 2 + k * 3, rng.randint(0, 59), tzinfo=TPE)
        emit("cam-07", "Z4", "W041", "no_harness", t, rng.randint(1, 20), conf=round(rng.uniform(0.78, 0.97), 2))
    # cam-05 的補傳被送了兩次：同一批 event_id，第二次晚 14 分鐘
    resent = [dict(r) for r in rows if r["camera_id"] == "cam-05" and r["event_time"].startswith("2026-09-10T1")
              and int(r["event_time"][11:13]) >= 10]
    for r in resent:
        r["ingested_at"] = iso_utc(datetime.fromisoformat(r["ingested_at"]) + timedelta(minutes=14))
    rows.extend(resent)
    rows.sort(key=lambda r: (r["ingested_at"], r["event_id"]))  # 檔案順序＝到達順序
    planted = {
        "period_local": f"{START.isoformat()}..{(START + timedelta(days=DAYS - 1)).isoformat()}，週日停工",
        "never_seen_workers": sorted(absent_all),
        "repeat_offenders": sorted(w for w, p in propensity.items() if p > 1),
        "roster_duplicate_key": "W023（2026-09-14 轉承攬商，名冊兩列）",
        "late_batch": "cam-05 2026-09-10 10:00 後斷線（cam-06 停機保養），事件於 2026-09-11 09:05（+08:00）補傳",
        "duplicate_resend": f"同一批補傳 {len(resent)} 筆送了兩次（event_id 相同，ingested_at 晚 14 分鐘）",
        "confidence_not_recorded": "cam-08（model_version=ppe-v2）confidence 一律為 null",
        "confidence_percent_bug": "cam-02 2026-09-15～17 confidence 為 40–99 的百分比",
        "true_anomaly": "W041 2026-09-22 14:02 起 cam-07 連續 18 筆 no_harness",
        "unidentified": "worker_id 空字串＝辨識不到臉，事件仍然發生",
        "handled_at_empty": "違規未處理＝沒發生；ppe_ok＝不適用",
    }
    return rows, planted


def build_dashboard_export(events: list[dict]) -> bytes:
    """廠商儀表板匯出：只有第 1 週、中文欄名、confidence 變成「87%」、沒有 confidence 的寫「N/A」。"""
    zone_zh = {z: v[0] for z, v in ZONES.items()}
    type_zh = {e[0]: e[1] for e in EVENT_TYPES}
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(["事件編號", "區域", "攝影機", "人員", "事件", "信心度", "發生時間"])
    first_week = sorted((e for e in events if e["event_time"] < "2026-09-06"), key=lambda e: e["event_time"])
    seen = set()
    for e in first_week:
        if e["event_id"] in seen:
            continue
        seen.add(e["event_id"])
        c = e["confidence"]
        conf = "N/A" if c is None else (f"{c:.0f}%" if c > 1 else f"{c * 100:.0f}%")
        t = datetime.fromisoformat(e["event_time"]).strftime("%Y/%m/%d %H:%M")
        w.writerow([e["event_id"], zone_zh[e["zone"]], e["camera_id"], e["worker_id"] or "未辨識",
                    type_zh[e["event_type"]], conf, t])
    return buf.getvalue().encode("utf-8-sig")


def build_reports(rng: random.Random, workers: list[dict]) -> list[dict]:
    """主管的虛驚事件通報：自由文字，刻意含人名、電話與工號（全部虛構）。"""
    people = [w for w in workers if w["valid_to"] == ""]
    templates = [
        ("{zone}有一位作業人員（{name}）在{place}作業時沒有扣上安全帶，經現場提醒後改善。{extra}", ["墜落", "安全帶"], ["N0060014#19"]),
        ("{name}（工號 {wid}）在{zone}進場時未戴安全帽，由警衛攔下。{extra}", ["安全帽", "進場管制"], ["N0060014#11-1"]),
        ("開挖區警示線被移動約一公尺，{name}跨越警示線取工具。已請領班重新設置。{extra}", ["警示線", "開挖"], ["N0060014#24"]),
        ("施工架第三層護欄被暫時拆除以吊料，{name}與另一位同仁在未使用安全帶下作業約十分鐘。{extra}", ["墜落", "施工架", "安全帶"], ["N0060014#19", "N0060014#17"]),
        ("下雨後{place}地面濕滑，{name}差點滑倒，未受傷。{extra}", ["滑倒"], []),
        ("吊料時有人站在吊掛物下方，{name}即時喊停。{extra}", ["吊掛", "物體飛落"], ["N0060014#144"]),
    ]
    places = ["二樓樓板開口旁", "鋼梁上", "施工構臺", "樓梯口", "擋土支撐旁"]
    extras = ["", "", "如有疑問請聯絡領班 {boss}，電話 {phone}。", "已口頭告知 {name} 本人。",
              "{boss}表示會在明天早會宣導。", "通報人：{boss}（{phone}）。"]
    rows = []
    for i in range(1, 41):
        tpl, tags, refs = templates[rng.randrange(len(templates))]
        w, boss = rng.choice(people), rng.choice(people)
        zone = ZONES[w["home_zone"]][0]
        extra = rng.choice(extras).format(boss=boss["name"], phone=f"0900-{rng.randint(100, 999)}-{rng.randint(100, 999)}",
                                          name=w["name"])
        text = tpl.format(zone=zone, name=w["name"], wid=w["worker_id"], place=rng.choice(places), extra=extra)
        day = START + timedelta(days=rng.randrange(DAYS))
        if day.weekday() == 6:
            day -= timedelta(days=1)
        t = datetime(day.year, day.month, day.day, rng.randint(7, 16), rng.randint(0, 59), tzinfo=TPE)
        rows.append({"report_id": f"R{i:03d}", "reported_at": iso_local(t), "reporter": boss["name"],
                     "zone": w["home_zone"], "text": text, "tags": tags, "related_articles": refs})
    rows.sort(key=lambda r: r["reported_at"])
    return rows


def to_csv(rows: list[dict], fields: list[str]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def jsonl(rows: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")


def main() -> None:
    rng = random.Random(SEED)
    workers = build_workers(rng)
    events, planted = build_events(rng, workers)
    reports = build_reports(rng, workers)
    types = [{"event_type": t, "label_zh": zh, "is_violation": str(v).lower(), "pcode": p, "slug": s, "basis": b}
             for t, zh, v, p, s, b in EVENT_TYPES]
    outputs = {
        "events.jsonl": jsonl(events),
        "workers.csv": to_csv(workers, list(workers[0])),
        "event-types.csv": to_csv(types, list(types[0])),
        "dashboard-export.csv": build_dashboard_export(events),
        "near-miss-reports.jsonl": jsonl(reports),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (OUT / name).write_bytes(data)
    manifest = {
        "kind": "synthetic-fixture", "seed": SEED, "site": SITE,
        "caveat": "全部為合成資料：人名、電話、工號、事件皆虛構；法條對應僅供練習，不是法律意見。",
        "zones": {z: {"name": v[0], "cameras": v[1]} for z, v in ZONES.items()},
        "planted": planted,
        "counts": {"events_rows": len(events), "events_unique_ids": len({e["event_id"] for e in events}),
                   "workers_rows": len(workers), "reports": len(reports)},
        "files": {n: {"bytes": len(d), "sha256": sha256(d)} for n, d in sorted(outputs.items())},
        "environment": {"python": platform.python_version(), "generator": "tools/build_events.py"},
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for n, d in sorted(outputs.items()):
        print(f"{n:26} {len(d):>8} bytes  {sha256(d)[:12]}")
    print(json.dumps(manifest["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
