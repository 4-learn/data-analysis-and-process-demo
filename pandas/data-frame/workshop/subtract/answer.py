import random
import pandas as pd
 
df1 = pd.DataFrame({"薪資":[100, 100, 100, 100],
                    "差旅":[100, 100, 100, 100],
                    "公關":[100, 100, 100, 100],
                    "加班":[100, 100, 100, 100]},
                    index =["Q1", "Q2", "Q3", "Q4"])
 
df2 = pd.DataFrame({"薪資":[random.randrange(50), random.randrange(50), random.randrange(50), random.randrange(50)],
                    "差旅":[random.randrange(50), random.randrange(50), random.randrange(50), random.randrange(50)],
                    "公關":[random.randrange(50), random.randrange(50), random.randrange(50), random.randrange(50)],
                    "加班":[random.randrange(50), random.randrange(50), random.randrange(50), random.randrange(50)]},
                    index =["Q1", "Q2", "Q3", "Q4"])

while True:
    df1 = df1.subtract(df2)
    
    if(df1.loc["Q4", "薪資"] < 50):
        break

print("公司的薪資目前低於本金 50% 了！")    
print(df1)
