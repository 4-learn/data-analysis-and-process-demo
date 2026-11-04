"""Series 入門：三天的未戴安全帽事件數，全部都是教學用假資料。"""
import pandas as pd

counts = pd.Series([0, 2, 1])

print("三天的事件數")
print(counts)

print("哪些天有事件？")
print(counts > 0)

print("只留下有事件的天")
print(counts[counts > 0])
