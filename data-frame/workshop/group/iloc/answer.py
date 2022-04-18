import pandas as pd

mydict = [[{"name": "stu-0", "score": 51, "delta": -1}, {"name": "stu-1", "score": 64, "delta": -4}, {"name": "stu-2", "score": 63, "delta": 17}, {"name": "stu-3", "score": 66, "delta": -26}], [{"name": "stu-4", "score": 62, "delta": 8}, {"name": "stu-5", "score": 63, "delta": 27}, {"name": "stu-6", "score": 70, "delta": 30}, {"name": "stu-7", "score": 60, "delta": -20}], [{"name": "stu-8", "score": 64, "delta": -4}, {"name": "stu-9", "score": 52, "delta": 38}, {"name": "stu-10", "score": 66, "delta": 34}, {"name": "stu-11", "score": 64, "delta": -44}], [{"name": "stu-12", "score": 55, "delta": 15}, {"name": "stu-13", "score": 60, "delta": -10}, {"name": "stu-14", "score": 52, "delta": 8}, {"name": "stu-15", "score": 69, "delta": 31}]]

df = pd.DataFrame(mydict)

print("1. 全班的 DataFrame 為:\n")
print(df)

print("2. 第 3 班成績為：\n")
print(df.iloc[2])


# 奇數班總分
sumOfodd = 0
for indexDF in range(4):
    if indexDF % 2 != 0:
       # 抓到奇數班級了！
       for indexSeries in range(4):
             # 分數和：奇數班的 [班級, 學生]["分數"]
             sumOfodd = sumOfodd + df.iloc[indexDF, indexSeries]["score"]

print("\n3. 奇數班級的和:" + str(sumOfodd))
