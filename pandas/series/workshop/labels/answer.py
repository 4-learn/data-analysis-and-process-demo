import pandas as pd

list_input = list(input("請輸入 10 個英文或數字，以 , 隔開 : ").split(", "))

list_type = []

for obj in list_input:
    if (obj.isdigit()):
        list_type.append("int")
    else:
        list_type.append("str")

myvar = pd.Series(list_input, index = list_type)
value = input("請輸入你要查詢的型態: ")

print(myvar[value])

