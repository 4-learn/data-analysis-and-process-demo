## **情境**

你是一間工程顧問公司的軟體部門工程師，最近接到一個專案需求：

---

### **專案背景**

營建署最近加強工地安全稽查，工地主任每天需要進行安全巡檢，但面臨以下挑戰：

1. **需要拍照存證大量違規情況**：如何有效管理違規影像及其描述成為難點。
2. **需要定期產出統計報表**：違規次數、時間分布、類型等統計耗時且容易出錯。
3. **人工作業耗時且容易出錯**：導致效率低下且質量不穩定。

---

### **使用者需求**

工地主任小明說：

> "每天要巡視 3 個工地，平均一個工地要拍 20 張照片，光是整理照片就花掉我 1-2 小時。最煩的是月底要做報表，要統計每個工地的違規類型和次數，常常加班到很 晚..."

---

### **你的任務**

身為軟體工程師，你決定開發一個 **違規事件分析系統**，目標是：

1. 將 Camera Event（違規影像事件）結構化管理
2. 提供數據分析和統計功能
3. 自動生成分析報告
4. 匯出資料供後續使用

在此任務中，**Pandas** 是數據處理的核心工具，承擔以下重要角色：

- 將 Camera Event 結構化為易於管理的 DataFrame
- 高效處理數據清理、欄位提取與分析
- 為數據可視化、報表生成奠定基礎

---

### **技術需求**

- **Python 基礎架構**：支持數據處理與文件操作
- **Pandas**：用於數據結構化、統計分析與時間序列處理

---

### **Pandas 的角色與用途**

**Pandas** 是整個專案的數據處理核心，其角色如下：

1. **數據結構化**：
   - 將原始的 Camera Event（dict 格式）轉換為 **DataFrame**
   - 結構化的數據有助於後續的清理、分析和視覺化

2. **高效數據操作**：
   - 使用 Pandas 的強大 API 快速進行統計分析
   - 提取日期、時間等關鍵資訊，支持時間序列分析

3. **數據輸出與整合**：
   - 將處理後的數據保存為 CSV
   - 產出統計報表

---

## **輸入資料格式**

Camera Event 的原始格式如下：

```python
raw_events = [
    {
        "image": "IMG_001.jpg",
        "time": "2024-12-31 08:30:00",
        "type": "未戴安全帽",
        "location": "A工地",
    },
    {
        "image": "IMG_002.jpg",
        "time": "2024-12-31 09:15:00",
        "type": "未穿反光背心",
        "location": "A工地",
    },
    {
        "image": "IMG_003.jpg",
        "time": "2024-12-31 10:00:00",
        "type": "未戴安全帽",
        "location": "B工地",
    },
    # ...
]
```

---

## **輸出示例**

### **1. 結構化的違規資料 DataFrame**

**Pandas** 將數據結構化為以下格式，方便分析和視覺化：

```plaintext
=== 結構化的違規資料 DataFrame ===
      image_id           timestamp violation_type location        date  hour    weekday
0  IMG_001.jpg 2024-12-31 08:30:00        未戴安全帽      A工地  2024-12-31     8    Tuesday
1  IMG_002.jpg 2024-12-31 09:15:00       未穿反光背心      A工地  2024-12-31     9    Tuesday
2  IMG_003.jpg 2024-12-31 10:00:00        未戴安全帽      B工地  2024-12-31    10    Tuesday
3  IMG_004.jpg 2024-12-31 14:30:00       施工架未固定      A工地  2024-12-31    14    Tuesday
4  IMG_005.jpg 2024-12-31 15:45:00        未戴安全帽      A工地  2024-12-31    15    Tuesday
```

---

### **2. 統計分析**

**Pandas** 快速統計違規類型與時段分布：

```plaintext
=== 違規類型統計 ===
violation_type
未戴安全帽     3
未穿反光背心    1
施工架未固定    1

=== 工地統計 ===
location
A工地    4
B工地    1

=== 時段分析 ===
hour_range
08-09時    1
09-10時    1
10-11時    1
14-15時    1
15-16時    1
```

---

### **3. 交叉分析**

```plaintext
=== 違規類型 × 工地 ===
location        A工地  B工地
violation_type
施工架未固定        1     0
未戴安全帽          2     1
未穿反光背心        1     0
```

---

### **4. 完整報表**

```plaintext
==================================================
工安違規統計報表
報表產生時間: 2024-12-31 16:00:00
==================================================

📊 違規事件總數: 5 件

📋 違規類型統計:
------------------------------
  未戴安全帽: 3 件 (60.0%)
  未穿反光背心: 1 件 (20.0%)
  施工架未固定: 1 件 (20.0%)

⏰ 時段分析:
------------------------------
  08-09時: 1 件
  09-10時: 1 件
  10-11時: 1 件
  14-15時: 1 件
  15-16時: 1 件

📍 工地統計:
------------------------------
  A工地: 4 件
  B工地: 1 件

==================================================
```

---

## **你需要實作的功能**

請建立一個 `ViolationAnalyzer` 類別，提供以下功能：

```python
# 使用範例
analyzer = ViolationAnalyzer()
analyzer.load_events(raw_events)

# 查看 DataFrame
print(analyzer.df)

# 統計分析
print(analyzer.violation_type_stats())  # 違規類型統計
print(analyzer.location_stats())         # 工地統計
print(analyzer.hourly_stats())           # 時段統計

# 交叉分析
print(analyzer.violation_by_location())  # 違規類型 × 工地

# 報表輸出
print(analyzer.generate_report())        # 完整報表
analyzer.export_csv("violations.csv")    # 匯出 CSV
```

### **提示**

1. 使用 `pd.DataFrame` 將 dict list 轉為結構化資料
2. 使用 `pd.to_datetime()` 處理時間欄位
3. 使用 `.dt.hour`、`.dt.date`、`.dt.day_name()` 提取時間資訊
4. 使用 `.value_counts()` 進行統計
5. 使用 `pd.crosstab()` 進行交叉分析

---

## **解答**

解答請參考：[GitHub - ch-03-pandas-analysis](https://github.com/4-learn/event-driven-alert-system/tree/ch-03-pandas-analysis)

主要檔案：
- `analysis/schemas.py` - 資料結構定義
- `analysis/data_processor.py` - DataFrame 處理
- `analysis/report_generator.py` - 報表生成
- `main.py` - ViolationAnalyzer 整合類別