# 2026 改版：資料處理與分析（pandas 3）

勞動部 AI 大數據人才養成班「Python 資料處理與分析（2026 改版）」的上課示範程式與練習資料。
本資料夾與上層舊版（`numpy/`、`pandas/`、`plot/`、`workshop/`）互不相干；舊版內容保留不動。

- 講義（HackMD Book）：（發布後補上）

## 環境

Ubuntu LTS、**Python 3.11 以上**（pandas 3.0 的要求）。

```bash
cd 2026
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 01_position.py          # 每支都可以直接執行，只讀 data/、不寫檔、不連網
python3 -m pytest -q            # 驗證：講義貼的輸出與實際執行結果逐字相同
```

以 Python 3.10／pandas 2.3.3 執行也能跑，但部分輸出不同（字串欄顯示 `object`、chained assignment 與混合時區行為不同）；差異逐條列在各測試的 `PANDAS2_DIFFS`。

## 目錄

| 檔案 | 節次 | 主題 |
|---|---|---|
| `01_position.py` | 01 | 這門課在 AI 系統中的位置 |
| `02_read_files.py` | 02 | CSV、編碼與多檔讀取 |
| `03_read_jsonl.py` | 03 | JSON／JSONL 與巢狀結構：接手爬蟲課的輸出 |
| `04_sql_or_pandas.py` | 04 | 該在資料庫做，還是拉進 pandas？ |
| `05_event_row.py` | 05 | 一筆事件 = 一列；欄位是 schema |
| `06_explore.py` | 06 | 五分鐘探索法：這份資料能不能用？ |
| `07_select_filter.py` | 07 | 欄位選取、布林篩選與 Top-K |
| `08_missing_anomaly.py` | 08 | 缺值與異常：判斷「能不能信」 |
| `09_validate_idempotent.py` | 09 | 資料驗證與冪等：壞資料要被擋下，重跑要一樣 |
| `10_event_vs_ingest.py` | 10 | 事件發生時間 vs 資料到達時間 |
| `11_datetime_resample.py` | 11 | to_datetime、時區與期間彙總 |
| `12_groupby_denominator.py` | 12 | 彙總：分母是什麼、漏掉了誰 |
| `13_derived_rules.py` | 13 | 衍生欄位與可稽核規則 |
| `14_merge_fanout.py` | 14 | 跨來源合併與 fan-out |
| `15_condense.py` | 15 | 濃縮：LLM 不該看到三萬筆 |
| `16_context_budget.py` | 16 | 序列化與 context 預算 |
| `17_text_corpus.py` | 17 | 文字語料：切塊、多值與去識別 |
| `18_end_to_end.py` | 18 | 從 JSONL 到 LLM 可讀摘要 |

## 練習資料：`data/`

- `articles.jsonl`、`02-exports/`、`03-*`、`09-batches/`：來自爬蟲課練習站 [crawler-playground](https://github.com/4-learn/crawler-playground)（MIT）固定 commit，由 `tools/build_fixtures.py` 產生。條文**可能經刻意修改，不具法律效力**。
- `events/`：**合成**的工地 AI 攝影機事件、人員名冊、虛驚通報，由 `tools/build_events.py` 以固定種子產生。**人名、電話、工號、事件全部虛構**，不代表任何真實工地。
- 每個檔案的位元組數與 SHA-256 記在 `MANIFEST.json`；重建結果位元組相同。

## 給老師

`NN-*.md` 是講義原稿（與 HackMD 同內容），測試從這裡擷取 Demo 並比對貼上的輸出；`.py` 由 `tools/export_demo_repo.py` 從講義逐字取出，請改講義、再重新匯出，不要直接改 `.py`。
