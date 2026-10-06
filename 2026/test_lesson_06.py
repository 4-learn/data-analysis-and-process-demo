import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_lessons import ROOT, load_demo, run_main, pasted_blocks  # noqa: E402
import pandas as pd, pytest  # noqa: E402

LESSON = "06-explore.md"
PANDAS2_DIFFS = [
    ("dtypes：{'object': 7}", "dtypes：{'str': 7}"),
    ("info()：5   信心度     629 non-null    object", "info()：5   信心度     629 non-null    str"),
    ("info()：dtypes: object(7)", "info()：dtypes: str(7)"),
]


@pytest.fixture(scope="module")
def d06():
    return load_demo(LESSON)[2]


@pytest.fixture(scope="module")
def raw(d06):
    return d06["read_raw"](d06["EXPORT"])


def test_06_output_matches_lesson():
    out = run_main(LESSON)
    if int(pd.__version__.split(".")[0]) < 3:
        for old, new in PANDAS2_DIFFS:
            out = out.replace(old, new)
    blocks = [b for b in pasted_blocks(LESSON) if b.startswith("== ")]
    assert blocks
    for b in blocks:
        assert b in out, b[:300]


def test_06_naive_read_has_no_numeric_column_and_describe_falls_back(d06):
    naive = pd.read_csv(d06["EXPORT"])
    assert naive.shape == (692, 7)
    assert naive.select_dtypes("number").empty
    assert naive.describe().index.tolist() == ["count", "unique", "top", "freq"]
    with pytest.raises(ValueError):
        naive.describe(include="number")
    with pytest.raises(TypeError):
        naive["信心度"].mean()


def test_06_default_na_list_eats_NA_but_not_unrecognized(d06, raw):
    naive = pd.read_csv(d06["EXPORT"])
    assert naive["信心度"].isna().sum() == 63 and naive["人員"].isna().sum() == 0
    assert (naive["人員"] == "未辨識").sum() == 92
    assert raw.isna().sum().sum() == 0
    assert (raw["信心度"] == "N/A").sum() == 63


def test_06_coerce_silently_destroys_column(d06):
    naive = pd.read_csv(d06["EXPORT"])
    coerced = pd.to_numeric(naive["信心度"], errors="coerce")
    assert coerced.isna().all()


def test_06_missing_is_concentrated_on_cam08(raw):
    na = raw["信心度"] == "N/A"
    assert set(raw.loc[na, "攝影機"]) == {"cam-08"}
    assert na.sum() == (raw["攝影機"] == "cam-08").sum() == 63
    unknown = raw.loc[raw["人員"] == "未辨識", "區域"].value_counts().to_dict()
    assert unknown == {"出入口": 24, "施工架": 20, "鋼構組立": 28, "開挖區": 20}


def test_06_parse_confidence_values(d06, raw):
    conf = d06["parse_confidence"](raw["信心度"])
    assert conf.notna().sum() == 629 and conf.min() == 0.35 and conf.max() == 0.99
    assert round(conf.mean(), 3) == 0.774 and round(conf.fillna(0).mean(), 3) == 0.704


@pytest.mark.parametrize("value, message", [
    ("87", "無法解讀"), ("0.87", "無法解讀"), ("高", "無法解讀"), ("", "無法解讀"),
    ("120%", "超過 100%"),
])
def test_06_parse_confidence_rejects(d06, value, message):
    with pytest.raises(ValueError, match=message):
        d06["parse_confidence"](pd.Series(["50%", "N/A", value]))


def test_06_dropna_halves_scaffold_zone(d06, raw):
    conf = d06["parse_confidence"](raw["信心度"])
    kept = raw[conf.notna()]
    assert (raw["區域"] == "施工架").sum() == 115 and (kept["區域"] == "施工架").sum() == 52
    viol = lambda d: ((d["區域"] == "施工架") & (d["事件"] != "防護具正確")).sum()  # noqa: E731
    assert viol(raw) == 21 and viol(kept) == 14


def test_06_workshop_observations(raw):
    assert raw["事件編號"].is_unique
    assert raw["發生時間"].is_monotonic_increasing
    assert raw["發生時間"].min() == "2026/08/31 07:04" and raw["發生時間"].max() == "2026/09/05 16:59"
    day = raw["發生時間"].str[:10].value_counts()
    assert len(day) == 6 and day.min() == 107 and day.max() == 126
    assert raw.groupby("區域")["攝影機"].nunique().eq(2).all()
    assert raw["事件"].value_counts().to_dict() == {
        "防護具正確": 575, "未戴安全帽": 61, "高處未使用安全帶": 33, "跨越警示線": 23}
    assert raw["人員"].str.fullmatch(r"W\d{3}|未辨識").all()
    assert raw.loc[raw["人員"] != "未辨識", "人員"].nunique() == 52
    v = raw[raw["事件"] != "防護具正確"]
    assert v["人員"].value_counts().index[0] == "未辨識" and (v["人員"] == "未辨識").sum() == 22
    assert v.loc[v["人員"] != "未辨識", "人員"].value_counts().head(1).to_dict() == {"W018": 10}


def test_06_ai_versions(d06, raw):
    naive = pd.read_csv(d06["EXPORT"])
    with pytest.raises(ValueError, match="'70%'"):
        naive["信心度"].astype(float)
    pct = naive["信心度"].str.replace("%", "").astype(float)
    assert pct.isna().sum() == 63 and round(pct.mean(), 2) == 77.4 and round(pct.fillna(0).mean(), 2) == 70.35
    assert len(naive.dropna()) == 629
    with pytest.raises(ValueError, match="'N/A'"):
        raw["信心度"].str.replace("%", "").astype(float)


def test_06_default_na_probe():
    probe = pd.read_csv(io.StringIO("v\nN/A\nNA\nn/a\nnull\nNULL\nNone\nnan\n-\n未辨識\n無\n"))
    assert probe["v"].isna().tolist() == [True] * 7 + [False] * 3
