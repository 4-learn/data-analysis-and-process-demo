import pandas as pd

boxes = {'Color': ['Green','Green','Green','Blue','Blue','Red','Red','Red'],
         'Shape': ['Rectangle','Rectangle','Square','Rectangle','Square','Square','Square','Rectangle'],
         'Price': [10,15,5,5,10,15,15,5]
        }

counts_buy = int(input("請輸入您要買幾個箱子: "))
list_order = []

for index in range(counts_buy):
    obj = {"color":"", "shape":""}
    obj["color"] = input(str(index+1) + " 號箱子，請輸入顏色: ")
    obj["shape"] = input(str(index+1) + " 號箱子，請輸入形狀: ")
    list_order.append(obj)


# 依照規則，過濾出箱子
df = pd.DataFrame(boxes, columns= ['Color','Shape','Price'])

list_selected = []
for index in range(counts_buy):
    selected = df.loc[df['Color'] == list_order[index]["color"]]
    selected = selected.loc[df['Shape'] == list_order[index]["shape"]]
    list_selected.append(selected)

# 印出可購買的清單
print("適合您的商品清單為:")
result = pd.concat(list_selected)
print(result)
