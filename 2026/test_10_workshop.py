"""第 10 節 Workshop：把本節的驗證寫成 pytest。執行：python3 -m pytest -q test_10_workshop.py
第一個測試已寫好；把兩個 TODO 補完（刪掉 pytest.skip 那一行）。"""

from importlib import import_module

import pytest

demo = import_module("10_validate_idempotent")   # 檔名以數字開頭，改用 import_module 匯入


def test_v1_is_valid():
    demo.validate(demo.read_batch(demo.DATA / "articles.jsonl"))


def test_apply_twice_same_fingerprint():
    pytest.skip("TODO：套用 v2 兩次，比較兩次的 fingerprint() 要相同")


def test_missing_timezone_is_rejected():
    pytest.skip("TODO：把 v2 某一列的 fetched_at 拿掉時區，用 pytest.raises(demo.ValidationError) 證明會被擋")
