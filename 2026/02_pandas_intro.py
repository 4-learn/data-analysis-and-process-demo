"""第 02 節：pandas 入門——DataFrame 是什麼、怎麼看、怎麼取欄取列、怎麼算、怎麼存。"""

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
ROSTER = DATA / "events" / "workers.csv"
OUTPUT = Path(__file__).resolve().parent / "output"


def read_roster(path=ROSTER):
    """名冊：每一格都先當字串讀進來；空格保持空字串，不變成 NaN（第 03 節會說明為什麼）。"""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


if __name__ == "__main__":
    print("== 1. 從 list of dict 建一張 DataFrame ==")
    rows = [
        {"worker_id": "W001", "name": "蔡靜宜", "zone": "Z3", "violations": 2},
        {"worker_id": "W002", "name": "李雅婷", "zone": "Z2", "violations": 0},
        {"worker_id": "W003", "name": "王志豪", "zone": "Z1", "violations": 5},
    ]
    small = pd.DataFrame(rows)
    print(small)
    print(f"幾列幾欄 shape={small.shape}；欄名 columns={small.columns.tolist()}")
    print(f"列的標籤 index={small.index.tolist()}")

    print("\n== 2. 讀一個 CSV，先看長相 ==")
    roster = read_roster()
    print(f"shape={roster.shape}")
    print(roster.head(3)[["worker_id", "name", "contractor", "trade", "home_zone"]].to_string())
    print(f"worker_id 不同值 {roster['worker_id'].nunique()} 個，比列數少 1：W023 換了承攬商，名冊有兩列")

    print("\n== 3. 取一欄、取幾欄 ==")
    names = roster["name"]
    print(f"roster['name'] 是 {type(names).__name__}，長度 {len(names)}，前三個 {names.head(3).tolist()}")
    two = roster[["worker_id", "contractor"]]
    print(f"roster[['worker_id', 'contractor']] 是 {type(two).__name__}，shape={two.shape}")

    print("\n== 4. 取列：條件篩選 ==")
    is_z4 = roster["home_zone"] == "Z4"
    print(f"roster['home_zone'] == 'Z4' 是一欄 True／False，True 有 {int(is_z4.sum())} 個")
    z4 = roster[is_z4]
    print(f"roster[條件] 留下 {len(z4)} 列：{z4['worker_id'].head(5).tolist()} …")
    both = roster[(roster["home_zone"] == "Z4") & (roster["contractor"] == "乙鋼構")]
    print(f"兩個條件用 & 接、各自加括號：{len(both)} 列")
    print(f"第 0 列（用位置 iloc）：{roster.iloc[0]['name']}；第 0 列的 trade（用標籤 loc）：{roster.loc[0, 'trade']}")

    print("\n== 5. 數一數、加一欄、排序 ==")
    print(roster["contractor"].value_counts().to_string())
    small["over_3"] = small["violations"] > 3
    print(small.sort_values("violations", ascending=False).to_string(index=False))

    print("\n== 6. 分組計數，存成檔案 ==")
    table = roster.groupby(["contractor", "home_zone"]).size().reset_index(name="人數")
    print(table.head(6).to_string(index=False))
    OUTPUT.mkdir(exist_ok=True)
    out = OUTPUT / "roster_by_contractor.csv"
    table.to_csv(out, index=False)
    back = pd.read_csv(out, dtype=str, keep_default_na=False)
    print(f"寫入 output/{out.name}：{len(table)} 列；讀回來 {back.shape}，人數合計 {table['人數'].sum()}")
