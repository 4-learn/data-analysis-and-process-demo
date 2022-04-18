import json
# 一些參數
numbersOfStudents = 16

# 最後要列印出來的陣列
listOutput = []
listAnswer = []

# 原始成績
listInput = [{"score": 51}, {"score": 64}, {"score": 63}, {"score": 66}, {"score": 62}, {"score": 63}, {"score": 70}, {"score": 60}, {"score": 64}, {"score": 52}, {"score": 66}, {"score": 64}, {"score": 55}, {"score": 60}, {"score": 52}, {"score": 69}]

# 產生班級座位表
for index in range(numbersOfStudents):
    dictStudentName = {"name": "stu-" + str(index), "score":listInput[index]["score"]}
    listOutput.append(dictStudentName)

# 輸入分數
for index in range(numbersOfStudents):
    value = input("請輸入學生 " + "stu-" + str(index) + " 的成績: ")
    dictStu = listOutput[index]
    dictStu["delta"] = int(value) - int(dictStu["score"])

# 轉為 2 (4x4) 維矩陣
indexCounts = 0
for rowIndex in range(4):
    listData = []
    for columnIndex in range(4):
        listData.append(listOutput[indexCounts])
        indexCounts = indexCounts + 1
    listAnswer.append(listData)

print(json.dumps(listAnswer))
