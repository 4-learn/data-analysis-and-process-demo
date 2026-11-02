"""第 09 節 Workshop 課堂題：同一份資料，補 0（A）與 dropna（B）各會讓數字變成怎樣？
已經寫好 A；照著 A 複製一份，改成 B。"""

from importlib import import_module

demo = import_module("09_missing_anomaly")   # 檔名以數字開頭，改用 import_module 匯入


def report(label, df):
    v = demo.is_violation(df)
    z4 = df["zone"] == "Z4"
    print(f"{label}：{len(df)} 列；平均信心度 {df['confidence'].mean():.3f}；Z4 平均 {df.loc[z4, 'confidence'].mean():.3f}；"
          f"違規 {int(v.sum())}；Z4 違規 {int((v & z4).sum())}；Z4 no_harness {int((z4 & (df['event_type'] == 'no_harness')).sum())}")


if __name__ == "__main__":
    events, log, dropped = demo.clean(demo.load_events())      # 已去重、cam-02 已 ÷100
    report("原始", events)

    a = events.copy()
    a["confidence"] = a["confidence"].fillna(0)                 # A：補 0
    report("A 補 0", a)

    # TODO：B = events.dropna(subset=["confidence"])，再 report("B dropna", b)
