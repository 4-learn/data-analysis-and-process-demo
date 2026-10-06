import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "17-text-corpus.md"
PANDAS2_DIFFS = []  # 2.3.3 實測逐字相同


def test_17_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d17():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def articles(d17):
    return d17["read_articles"]()


@pytest.fixture(scope="module")
def reports(d17):
    return pd.read_json(d17["DATA"] / "events" / "near-miss-reports.jsonl", lines=True, dtype=False, convert_dates=False)


@pytest.fixture(scope="module")
def roster(d17):
    return pd.read_csv(d17["DATA"] / "events" / "workers.csv", dtype=str, keep_default_na=False)


def test_17_chunks_roundtrip_and_respect_size(d17, articles):
    for size in (300, 450, 500):
        chunks = d17["chunk_articles"](articles, size)
        assert chunks["chunk_id"].is_unique
        rebuilt = chunks.groupby(["pcode", "slug"], sort=False)["chunk"].agg("\n".join)
        assert (rebuilt == articles.set_index(["pcode", "slug"])["content"].loc[rebuilt.index]).all()
        # 單行超過 size 才可能超過；本語料最長一行 202 字
        assert chunks["chunk"].str.len().max() <= size
        # 不超過 size 的條文一定整條一塊
        short = articles.loc[articles["content"].str.len() <= size, ["pcode", "slug"]]
        n = chunks.drop_duplicates(["pcode", "slug"]).merge(short, on=["pcode", "slug"])["n_chunks"]
        assert (n == 1).all() and len(n) == len(short)


def test_17_chunk_size_table_claims(d17, articles):
    """〈參考判讀〉的比較表。"""
    rows = {}
    for size in (300, 450, 500):
        c = d17["chunk_articles"](articles, size)
        later = c[c["chunk_no"] > 1]
        kuan = later["chunk"].str.match(r"[一二三四五六七八九十]+、")
        mu = later["chunk"].str.match(r"（[一二三四五六七八九十]+）")
        xiang = later["chunk"].str.match(r"(?:前|第[一二三四五六七八九十]+)\S*項")
        rows[size] = (len(c), int((c.drop_duplicates(["pcode", "slug"])["n_chunks"] > 1).sum()),
                      int((kuan | mu).sum()), int(kuan.sum()), int(mu.sum()), int(xiang.sum()),
                      int(c["chunk"].str.len().max()))
    assert rows == {300: (860, 91, 50, 40, 10, 20, 300), 450: (780, 30, 16, 15, 1, 3, 447),
                    500: (773, 24, 12, 10, 2, 3, 500)}


def test_17_orphan_line_separates_kuan_mu_and_xiang():
    """原版把款（一、）與目（（一））都算成「款」，也沒算「前項」開頭的塊：輸出必須分開列。"""
    out = run_main(LESSON)
    assert "16 塊以款或目開頭（款 15、目 1）" in out
    assert "3 塊以「前項／第 N 項」開頭" in out
    assert "塊以「款」開頭" not in out


def test_17_distribution_claims(articles):
    length = articles["content"].str.len()
    assert length.max() == 935 and length.min() == 4 and length.median() == 121
    assert (length > 450).sum() == 30 and (length <= length.mean()).mean() > 0.6
    p95 = length.groupby(articles["law_name"]).quantile(0.95).round()
    assert p95["營造安全衛生設施標準"] == 524 and p95["勞工退休金條例"] == 294
    g = length[articles["pcode"] == "N0060014"]
    assert (g > 450).sum() == 12 and len(g) == 189


def test_17_fixed_cut_lands_mid_line(d17, articles):
    assert int(articles["content"].map(d17["mid_line_cuts"]).sum()) == 31
    assert d17["mid_line_cuts"]("a" * 449 + "\n" + "b" * 100) == 0     # 剛好切在換行上不算


def test_17_explode_fanout_and_link(d17, articles, reports):
    assert len(reports.explode("tags")) == 82
    both = reports.explode("tags").explode("related_articles")
    assert len(both) == 106 and (both["tags"] == "墜落").sum() == 16
    assert reports["tags"].map(lambda t: "墜落" in t).sum() == 8
    linked, no_ref = d17["link_articles"](reports, articles)
    assert len(linked) == 42 and no_ref == 6 and linked["article_no"].notna().all()
    # list 欄被當字串：靜默 NaN（兩版相同）
    assert reports["related_articles"].str.split("#").isna().all()


def test_17_link_articles_rejects(d17, articles, reports):
    bad = reports.copy()
    bad.at[1, "related_articles"] = ["N0060014#999"]
    with pytest.raises(ValueError, match="引用的條文不存在"):
        d17["link_articles"](bad, articles)
    bad.at[1, "related_articles"] = ["N0060014-19"]
    with pytest.raises(ValueError, match="格式不對"):
        d17["link_articles"](bad, articles)


def test_17_deidentify_and_residuals(d17, reports, roster):
    clean = d17["deidentify"](reports, roster["name"])
    assert clean["text"].str.count("〔姓名〕").sum() == 67 and clean["text"].str.count("〔電話〕").sum() == 15
    assert reports["text"].str.contains("〔").sum() == 0                 # 不改原表
    found = d17["residuals"](clean, ["text", "reporter"], roster["name"])
    assert found["text：名冊人名"] == 0 and found["text：像電話的數字"] == 0
    assert found["text：工號"] == 7 and found["reporter：名冊人名"] == 40


def test_17_reporter_outside_roster_is_visible(d17, reports, roster):
    """X001、X002 的通報人不在名冊：名冊掃描只數到 40／42，Demo 必須把這 2 列印出來，正文不得再說「40 列全是名冊人名」。"""
    out = run_main(LESSON)
    assert "reporter 欄共 42 列：名冊掃描抓到 40 列，另 2 列不在名冊、掃不到：['陳志明']（X001、X002）" in out
    assert "'reporter：名冊人名': 40" in out
    text = (ROOT / LESSON).read_text(encoding="utf-8")
    assert "40 列全是名冊上的人名" not in text
    assert "陳志明" not in set(roster["name"]) and reports["reporter"].isin(roster["name"]).all()


@pytest.mark.parametrize("phone", ["0900-873-763", "0912345678", "(02)2345-6789", "02-2345-6789"])
def test_17_phone_formats(d17, roster, phone):
    df = pd.DataFrame({"text": [f"請洽{phone}安衛室"]})
    assert d17["deidentify"](df, roster["name"])["text"].iloc[0] == "請洽〔電話〕安衛室"


def test_17_roster_cannot_catch_unknown_names(d17, roster, articles):
    df = pd.DataFrame({"text": ["水電包商的張美華師傅", "李雅婷（工號 W002）"]})
    out = d17["deidentify"](df, roster["name"])["text"].tolist()
    assert out == ["水電包商的張美華師傅", "〔姓名〕（工號 W002）"]
    assert "張" not in set(roster["name"].str[0])
    guess = f"[{''.join(sorted(set(roster['name'].str[0])))}][\u4e00-\u9fff]{{2}}"
    assert len(articles["content"].str.findall(guess).explode().dropna()) == 85


def test_17_pack_lines_never_truncates(d17):
    """單一行超過 size：整行成一塊，不截斷（截斷會讓「但書」消失）。"""
    text = "短\n" + "長" * 30 + "\n尾"
    assert d17["pack_lines"](text, 10) == ["短", "長" * 30, "尾"]
    assert d17["pack_lines"]("甲\n乙\n丙", 3) == ["甲\n乙", "丙"]


def test_17_roundtrip_guard(articles):
    """chunk_articles() 的接回核對要有牙齒：換一個會掉內容的切法，必須報錯。"""
    ns = load_demo(LESSON)[2]
    ns["pack_lines"] = lambda text, size: text.split("\n")[:1]
    with pytest.raises(ValueError, match="接不回原文"):
        ns["chunk_articles"](articles)


def test_17_longer_names_replaced_first(d17):
    df = pd.DataFrame({"text": ["王明華與王明一起作業"]})
    out = d17["deidentify"](df, ["王明", "王明華"])["text"].iloc[0]
    assert out == "〔姓名〕與〔姓名〕一起作業"
