import pandas as pd

df1 = pd.read_csv('data1.csv')
df2 = pd.read_csv('data2.csv')

series_duplicated_df1 = df1.duplicated()
series_duplicated_df2 = df2.duplicated()

print("Start to checking data1.csv")
for index in range(series_duplicated_df1.size):
    if(series_duplicated_df1[index] == True):
        print("Got duplicate data in index " + str(index) + " start to droping ...")
        df1.drop_duplicates(inplace = True)

print("Start to checking data2.csv")
for index in range(series_duplicated_df2.size):
    if(series_duplicated_df2[index] == True):
        print("Got duplicate data in index " + str(index) + " start to droping ...")
        df2.drop_duplicates(inplace = True)
