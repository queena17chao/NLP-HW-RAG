# 健康醫療新聞 RAG 諮詢小幫手

## 1. 專案介紹

本專案以 **RAG（Retrieval-Augmented Generation，檢索增強生成）** 技術建立健康醫療新聞問答系統。

系統透過 Python 爬蟲蒐集「健康醫療網」新聞，將新聞標題、文章全文與來源資訊儲存至 SQLite 資料庫，使用 Ollama 地端大型語言模型產生新聞摘要，再將摘要轉換為向量，建立 FAISS 向量索引。

使用者可以透過 Flask 網頁輸入健康相關問題，系統會檢索相關新聞，由地端 LLM 根據新聞摘要生成回答，並附上新聞標題、網址與資料新增時間。

系統也支援多輪對話、Checkbox 控制是否重新檢索，以及歷史問答重點整理。

**新聞資料來源：** https://www.healthnews.com.tw/

## 2. 使用技術

| 技術 | 用途 |
|---|---|
| Python 3.12 | 主要開發語言 |
| uv | Python 套件與虛擬環境管理 |
| Requests、BeautifulSoup | 新聞網頁爬蟲 |
| Trafilatura | 擷取新聞正文 |
| SQLite | 儲存新聞資料與摘要 |
| Ollama | 執行地端語言模型 |
| Qwen3:4b | 產生新聞摘要 |
| Qwen2.5:3b | RAG 問答與重點整理 |
| EmbeddingGemma | 文字向量化 |
| FAISS | 相似度檢索 |
| Flask | Web 後端 |
| HTML、CSS | 網頁介面 |

## 3. 系統架構

```text
健康醫療網
    │
    ▼
Python 新聞爬蟲
    │
    ▼
data/news.json
    │
    ▼
SQLite 資料庫
(title、content、url、created_at...)
    │
    ▼
Qwen3:4b 產生摘要
(新聞標題 + 文章全文)
    │
    ▼
SQLite summary 欄位
    │
    ▼
EmbeddingGemma
    │
    ▼
FAISS 向量索引
    │
    ▼
使用者於 Flask 網頁提問
    │
    ▼
Checkbox：是否重新檢索？
    │
    ├── 是 → FAISS 搜尋相關新聞
    │
    └── 否 → 沿用上一輪檢索結果
    │
    ▼
Qwen2.5:3b 產生回答
    │
    ▼
顯示回答與新聞來源
    │
    ▼
多輪對話 / 重點整理
```

## 4. 專案資料夾結構

```text
RAG/
├── app.py
├── crawler/
│   └── news_crawler.py
├── database/
│   └── init_db.py
├── summarizer/
│   └── summarize_news.py
├── embedding/
│   └── build_index.py
├── rag/
│   ├── __init__.py
│   ├── retriever.py
│   └── chatbot.py
├── templates/
│   └── index.html
├── data/
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

## 5. 功能說明

### 5.1 新聞爬蟲

使用 Requests、BeautifulSoup 及 Trafilatura 擷取健康醫療網的新聞內容。

目前以「營養飲食」分類的 10 篇新聞作為測試資料。

擷取欄位包含：

- 新聞標題
- 新聞網址
- 文章全文
- 新聞分類
- 發布時間
- 資料新增時間

程式位置：`crawler/news_crawler.py`

執行指令：

```powershell
uv run python crawler/news_crawler.py
```

結果儲存於 `data/news.json`。

### 5.2 SQLite 資料庫

使用 SQLite 儲存爬取的新聞及模型產生的摘要。

資料庫：`data/health_news.db`

資料表：`news`

| 欄位 | 說明 |
|---|---|
| id | 新聞 ID |
| title | 新聞標題 |
| url | 新聞來源網址 |
| content | 文章全文 |
| summary | LLM 產生的摘要 |
| published_at | 原始新聞發布時間 |
| created_at | 資料新增至本機的時間 |
| category | 新聞分類 |

建立資料庫並匯入新聞：

```powershell
uv run python database/init_db.py
```

### 5.3 地端 LLM 文章摘要

使用 Ollama 的 `qwen3:4b` 模型產生文章摘要。

處理流程：

1. 從 SQLite 讀取新聞標題與文章全文。
2. 將標題與全文一起提供給地端 LLM。
3. 由模型生成繁體中文摘要。
4. 將摘要寫回 SQLite 的 `summary` 欄位。

程式位置：`summarizer/summarize_news.py`

執行指令：

```powershell
uv run python summarizer/summarize_news.py
```

### 5.4 Embedding 與 FAISS

使用 `embeddinggemma` 將文章摘要轉換為向量，並使用 FAISS 建立向量索引。

目前使用摘要作為向量化內容，並採用正規化向量搭配內積進行相似度搜尋。

程式位置：

- `embedding/build_index.py`：建立向量索引
- `rag/retriever.py`：搜尋相關新聞

執行指令：

```powershell
uv run python embedding/build_index.py
```

產生的檔案：

- `data/news.index`：FAISS 索引
- `data/news_ids.json`：向量與 SQLite 新聞 ID 的對照資訊

### 5.5 RAG 健康新聞問答

使用 `qwen2.5:3b` 模型進行問答。

使用者提問後，系統會：

1. 將使用者問題向量化。
2. 透過 FAISS 檢索相關新聞。
3. 根據檢索結果取得新聞標題、摘要與來源。
4. 將檢索內容與問題提供給 Qwen2.5:3b。
5. 顯示 AI 回答及相關新聞來源。

目前預設每次檢索最相關的 1 篇新聞（Top 1）。

終端機版本：`rag/chatbot.py`

執行指令：

```powershell
uv run python rag/chatbot.py
```

### 5.6 Flask 網頁介面

使用 Flask 建立互動式問答網站。

**主要功能：**

- 輸入健康相關問題
- AI 根據新聞摘要回答
- 顯示新聞標題、網址及資料新增時間
- Checkbox 控制是否重新檢索
- 支援多輪對話
- 整理歷史問答重點
- 清除對話紀錄

**Checkbox 功能：**

勾選時，系統重新使用 FAISS 搜尋與新問題相關的新聞。

未勾選時，系統沿用上一輪檢索的新聞資訊，並參考近期對話產生回答。

後端程式：`app.py`

前端模板：`templates/index.html`

啟動方式：

```powershell
uv run python app.py
```

開啟瀏覽器：

http://127.0.0.1:5000

## 6. 環境安裝與執行

### Step 1：安裝必要工具

本專案使用：

- Python 3.12
- uv
- Ollama

### Step 2：安裝 Python 套件

於專案根目錄執行：

```powershell
uv sync
```

### Step 3：下載 Ollama 模型

```powershell
ollama pull qwen3:4b
ollama pull qwen2.5:3b
ollama pull embeddinggemma
```

檢查已安裝模型：

```powershell
ollama list
```

執行前請確認 Ollama 服務已啟動。

### Step 4：建立新聞資料庫及向量索引

首次執行時，依序執行：

```powershell
uv run python crawler/news_crawler.py
```

```powershell
uv run python database/init_db.py
```

```powershell
uv run python summarizer/summarize_news.py
```

```powershell
uv run python embedding/build_index.py
```

### Step 5：啟動 RAG 網頁

```powershell
uv run python app.py
```

於瀏覽器開啟：

http://127.0.0.1:5000

即可開始使用健康新聞問答系統。

**注意：** GitHub Repository 不包含本機產生的新聞全文、SQLite 資料庫及 FAISS 索引，首次執行需要按照以上步驟建立資料。

## 7. 問答測試結果

### 測試一：連假健康飲食

**使用者問題：**

連假聚餐時，怎麼吃比較健康？

**FAISS 檢索結果：**

新聞標題：

連假聚餐頻繁影響健康？醫：可「先蔬後肉」、分食共享

新聞連結：

https://www.healthnews.com.tw/article/69872

**測試結果：**

Qwen2.5:3b 成功根據檢索新聞產生回答，包含先蔬後肉、控制飲食份量、分食共享等健康飲食建議，並顯示新聞來源。

### 測試二：腎臟病飲食

**使用者問題：**

腎臟病患者該如何注意飲食與蛋白質攝取？

**FAISS 檢索結果：**

新聞標題：

腎友如何護腎又保肌？飲食選擇、醫療介入、運動策略一次了解

新聞連結：

https://www.healthnews.com.tw/article/69908

**測試結果：**

Qwen2.5:3b 成功根據相關新聞摘要產生回答，整理腎臟病飲食、蛋白質攝取及健康管理重點，並顯示新聞來源。

### 多輪問答與重點整理

完成兩個不同問題後，使用系統的重點整理功能。

終端機版本可輸入：

```text
summary
```

Flask 網頁則可使用重點整理功能。

模型會彙整歷史問答、整理各問題重點與整體結論，並附上使用過的新聞來源資訊。

### 功能驗收

| 測試項目 | 結果 |
|---|---|
| 健康醫療新聞爬蟲 | 通過 |
| SQLite 新聞儲存 | 通過 |
| 地端模型新聞摘要 | 通過 |
| Embedding 向量化 | 通過 |
| FAISS 相關新聞檢索 | 通過 |
| Qwen2.5:3b 生成回答 | 通過 |
| 兩個不同問題測試 | 通過 |
| 多輪問答重點整理 | 通過 |
| 回答附新聞來源資訊 | 通過 |
| Flask 網頁功能 | 通過 |

## 8. 系統限制

1. 目前使用 10 篇新聞作為測試資料，知識涵蓋範圍有限。
2. 向量檢索使用新聞摘要，未直接以文章全文建立索引，因此可能遺漏部分細節。
3. 目前使用 Top 1 檢索，可能無法涵蓋所有相關新聞。
4. 地端 LLM 仍可能產生原始新聞未提及的內容，回答需搭配來源核對。
5. 本系統主要作為健康醫療新聞資訊整理工具，不應取代醫師或營養師的專業建議。

## 9. 資料來源與聲明

**健康醫療網**

https://www.healthnews.com.tw/

本專案僅供課程作業及技術學習使用。

新聞內容之著作權歸原權利人所有。程式提供新聞來源網址供使用者查閱，公開 GitHub Repository 不包含未經授權公開的文章全文資料。

## 10. GitHub Repository

專案程式碼：

https://github.com/queena17chao/NLP-HW-RAG

---

**專案名稱：** 健康醫療新聞 RAG 諮詢小幫手

**核心技術：** Python、Ollama、SQLite、EmbeddingGemma、FAISS、Flask