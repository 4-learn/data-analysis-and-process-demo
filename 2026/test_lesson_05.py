import sqlite3
import sys
import warnings
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "05-sql-or-pandas.md"
PANDAS2_DIFFS = [
    ("law_name=object, n=int64, avg_len=float64, no_chapter=float64, fetched_at=object",
     "law_name=str, n=int64, avg_len=float64, no_chapter=float64, fetched_at=str"),
]


def test_05_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert len(blocks) == 5
    for b in blocks:
        assert b in out, b[:300]


@pytest.fixture(scope="module")
def d05():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def articles():
    return pd.read_json(ROOT / "data" / "articles.jsonl", lines=True, dtype=False, convert_dates=False)


@pytest.fixture()
def con(d05, articles):
    c = d05["build_db"](articles)
    yield c
    c.close()


def test_05_schema_matches_crawler_16_columns(d05, con):
    cols = [r[1] for r in con.execute("PRAGMA table_info(law_articles)")]
    assert cols == ["id", "pcode", "law_name", "slug", "article_no", "chapter", "content",
                    "source_url", "content_hash", "fetched_at", "updated_at"]
    assert "source_version" not in cols
    info = {r[1]: (r[3], r[4]) for r in con.execute("PRAGMA table_info(law_articles)")}
    assert info["chapter"] == (1, "''")  # NOT NULL DEFAULT ''，空字串不是 NULL
    assert all(info[c][0] == 1 for c in cols if c != "id")
    assert con.execute("SELECT COUNT(*) FROM law_articles WHERE chapter IS NULL").fetchone()[0] == 0


def test_05_build_db_rejects_missing_columns(d05, articles):
    with pytest.raises(ValueError, match=r"缺少欄位 \['content_hash'\]"):
        d05["build_db"](articles.drop(columns="content_hash"))


def test_05_duplicate_load_is_atomic(d05, con, articles):
    batch = pd.concat([articles.head(2).assign(slug=["新1", "新2"]), articles.head(1)])
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        d05["load"](con, batch)
    assert con.execute("SELECT COUNT(*) FROM law_articles").fetchone()[0] == 749


def test_05_sql_groupby_equals_pandas_and_jsonl(con, articles):
    in_sql = pd.read_sql("SELECT pcode, COUNT(*) AS n FROM law_articles GROUP BY pcode ORDER BY pcode", con)
    from_file = articles.groupby("pcode").size().reset_index(name="n")
    assert in_sql["n"].tolist() == from_file["n"].tolist()
    assert in_sql["n"].sum() == 749 and len(in_sql) == 9


def test_05_params_block_injection_and_quotes(d05, con):
    find = d05["find_articles"]
    assert len(find(con, "N0060014", "墜落")) == 15
    assert len(find(con, "N0060014' OR '1'='1", "墜落")) == 0
    assert len(find(con, "N0060014'", "墜落")) == 0
    assert len(find(con, "N0060014", "it's")) == 0
    assert len(d05["naive_find"](con, "N0060014' OR '1'='1", "墜落")) == 190
    with pytest.raises(pd.errors.DatabaseError, match="unrecognized token"):
        d05["naive_find"](con, "N0060014'", "墜落")


def test_05_column_whitelist(d05, con):
    with pytest.raises(ValueError, match="不允許的欄位"):
        d05["find_articles"](con, "N0060014", "墜落", columns=("pcode", "content; DROP TABLE law_articles"))
    assert con.execute("SELECT COUNT(*) FROM law_articles").fetchone()[0] == 749


def test_05_like_wildcard_not_escaped_by_params(d05, con):
    # 參數化擋注入，不擋 LIKE 萬用字元（講義第四段第 3 點、Workshop 參考判讀）
    assert len(d05["find_articles"](con, "N0060014", "%")) == 189


def test_05_filter_first_vs_pull_all(d05, con):
    everything = pd.read_sql("SELECT * FROM law_articles", con)
    before = d05["find_articles"](con, "N0060014", "墜落")
    assert d05["transfer_bytes"](everything) // d05["transfer_bytes"](before) == 33  # 33.7 → 印成 34
    assert round(d05["transfer_bytes"](everything) / d05["transfer_bytes"](before)) == 34


def test_05_workshop_reference_numbers(con):
    a = pd.read_sql("SELECT pcode, MAX(LENGTH(content)) AS max_len FROM law_articles GROUP BY pcode ORDER BY pcode", con)
    b = pd.read_sql("SELECT pcode, content FROM law_articles", con)
    b = b.assign(max_len=b["content"].str.len()).groupby("pcode", as_index=False)["max_len"].max()
    assert a.equals(b) and a["max_len"].max() == 935
    g = pd.read_sql("SELECT pcode, NULLIF(chapter, '') AS chapter, COUNT(*) AS n FROM law_articles "
                    "GROUP BY pcode, chapter", con)
    assert (len(g), g["n"].sum()) == (76, 749)
    d = pd.read_sql("SELECT pcode, NULLIF(chapter, '') AS chapter FROM law_articles", con)
    assert d.groupby(["pcode", "chapter"]).size().sum() == 728
    assert len(d.groupby(["pcode", "chapter"], dropna=False).size()) == 76


def test_05_placeholder_mistakes(con):
    with pytest.raises(pd.errors.DatabaseError, match="Incorrect number of bindings"):
        pd.read_sql("SELECT slug FROM law_articles WHERE pcode = ? AND content LIKE '%?%'", con,
                    params=("N0060014", "墜落"))
    assert len(pd.read_sql("SELECT slug FROM law_articles WHERE pcode = ? AND content LIKE '%?%'", con,
                           params=("N0060014",))) == 0


def test_05_sqlite_connection_does_not_warn(con):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        pd.read_sql("SELECT 1 AS x", con)
