## Data Clean

#### 1. 撰寫一個 Pandas 的程式去刪除帶有空值的 Row
```python=
import pandas as pd
import numpy as np

df = pd.DataFrame({
'ord_no':[70001,np.nan,70002,70004,np.nan,70005,np.nan,70010,70003,70012,np.nan,70013],
'purch_amt':[150.5,270.65,65.26,110.5,948.5,2400.6,5760,1983.43,2480.4,250.45, 75.29,3045.6],
'ord_date': ['2012-10-05','2012-09-10',np.nan,'2012-08-17','2012-09-10','2012-07-27','2012-09-10','2012-10-10','2012-10-10','2012-06-27','2012-08-17','2012-04-25'],
'customer_id':[3002,3001,3001,3003,3002,3001,3001,3004,3003,3002,3001,3001],
'salesman_id':[5002,5003,5001,np.nan,5002,5001,5001,np.nan,5003,5002,5003,np.nan]})

print("1. 原本的 DataFrame")
print(df)

print("2. 刪除空值後")
result = df.dropna()
print(result)
```

#### 2. 撰寫一個 Pandas 的程式將 DataFrame label `purch_amt` Series 的空欄位，以中位數取代:
```python=
import pandas as pd
import numpy as np
pd.set_option('display.max_rows', None)
#pd.set_option('display.max_columns', None)
df = pd.DataFrame({
'ord_no':[70001,np.nan,70002,70004,np.nan,70005,np.nan,70010,70003,70012,np.nan,70013],
'purch_amt':[150.5,np.nan,65.26,110.5,948.5,np.nan,5760,1983.43,np.nan,250.45, 75.29,3045.6],
'sale_amt':[10.5,20.65,np.nan,11.5,98.5,np.nan,57,19.43,np.nan,25.45, 75.29,35.6],
'ord_date': ['2012-10-05','2012-09-10',np.nan,'2012-08-17','2012-09-10','2012-07-27','2012-09-10','2012-10-10','2012-10-10','2012-06-27','2012-08-17','2012-04-25'],
'customer_id':[3002,3001,3001,3003,3002,3001,3001,3004,3003,3002,3001,3001],
'salesman_id':[5002,5003,5001,np.nan,5002,5001,5001,np.nan,5003,5002,5003,np.nan]})

print("1. 原始 DataFrame:")
print(df)

print("2. 將 purch_amt 的空值以中位數取代 :")
df['purch_amt'].fillna(df['purch_amt'].median(), inplace=True)
print(df)
```

#### 3. 撰寫一個 Pandas 的程式將 DataFrame label `sale_amt` Series 的空欄位，以平均值取代:
```python=
import pandas as pd
import numpy as np
pd.set_option('display.max_rows', None)
#pd.set_option('display.max_columns', None)
df = pd.DataFrame({
'ord_no':[70001,np.nan,70002,70004,np.nan,70005,np.nan,70010,70003,70012,np.nan,70013],
'purch_amt':[150.5,np.nan,65.26,110.5,948.5,np.nan,5760,1983.43,np.nan,250.45, 75.29,3045.6],
'sale_amt':[10.5,20.65,np.nan,11.5,98.5,np.nan,57,19.43,np.nan,25.45, 75.29,35.6],
'ord_date': ['2012-10-05','2012-09-10',np.nan,'2012-08-17','2012-09-10','2012-07-27','2012-09-10','2012-10-10','2012-10-10','2012-06-27','2012-08-17','2012-04-25'],
'customer_id':[3002,3001,3001,3003,3002,3001,3001,3004,3003,3002,3001,3001],
'salesman_id':[5002,5003,5001,np.nan,5002,5001,5001,np.nan,5003,5002,5003,np.nan]})

print("1. 原始 DataFrame:")
print(df)

print("2. 將 purch_amt 的空值以中位數取代 :")
df['purch_amt'].fillna(df['purch_amt'].median(), inplace=True)
print(df)

print("3. 將 sale_amt 的空值以平均值取代 :")
df['sale_amt'].fillna(int(df['sale_amt'].mean()), inplace=True)
print(df)
```


#### 4. 撰寫一個 Pandas 的程式將 DataFrame 中的空值，以眾數的第一個 Series 取代:
```python=
import pandas as pd
import numpy as np
pd.set_option('display.max_rows', None)
#pd.set_option('display.max_columns', None)
df = pd.DataFrame({
'ord_no':[70001,np.nan,70002,70004,np.nan,70005,np.nan,70010,70003,70012,np.nan,70013],
'purch_amt':[150.5,np.nan,65.26,110.5,948.5,np.nan,5760,1983.43,np.nan,250.45, 75.29,3045.6],
'sale_amt':[10.5,20.65,np.nan,11.5,98.5,np.nan,57,19.43,np.nan,25.45, 75.29,35.6],
'ord_date': ['2012-10-05','2012-09-10',np.nan,'2012-08-17','2012-09-10','2012-07-27','2012-09-10','2012-10-10','2012-10-10','2012-06-27','2012-08-17','2012-04-25'],
'customer_id':[3002,3001,3001,3003,3002,3001,3001,3004,3003,3002,3001,3001],
'salesman_id':[5002,5003,5001,np.nan,5002,5001,5001,np.nan,5003,5002,5003,np.nan]})

print("1. 原始的 DataFrame:")
print(df) 

print("2. 將 NaN 的值，以眾數的第一個 Series 來取代:")

result = df.fillna(df.mode().iloc[0])
print(result)
```
