
from ollama import Client
from retriever import search_news

# =====================================
# 1. 基本設定
# =====================================

client = Client(host="http://localhost:11434")

# 改用非推理型模型，避免輸出思考過程
MODEL = "qwen2.5:3b"

# 每次檢索最相關的 1 篇新聞
TOP_K = 1

# 儲存所有成功的問答紀錄
conversation_records = []


# =====================================
# 2. 呼叫 Ollama 地端模型
# =====================================

def call_model(messages):
    """呼叫地端模型並取得回答"""

    response = client.chat(
        model=MODEL,
        messages=messages,
        stream=False,
        options={
            "temperature": 0.1,
            "num_predict": 1024
        }
    )

    answer = response.message.content or ""

    return answer.strip()


# =====================================
# 3. 顯示新聞來源
# =====================================

def print_sources(articles):
    """顯示新聞標題、連結與新增時間"""

    print("\n參考新聞來源：")

    if not articles:
        print("- 無")
        return

    for i, article in enumerate(articles, 1):
        print(f"- [新聞{i}] {article['title']}")
        print(f"  新聞連結：{article['url']}")
        print(
            f"  文章新增時間："
            f"{article.get('created_at') or '未知'}"
        )
        print()


# =====================================
# 4. RAG 問答
# =====================================

def ask_question(question):
    """檢索新聞並根據新聞產生回答"""

    print("\n正在檢索相關新聞...")

    try:
        articles = search_news(
            question,
            top_k=TOP_K
        )

    except Exception as error:
        print(f"新聞檢索失敗：{error}")
        return

    if not articles:
        print("\nAI 回答：")
        print("目前沒有找到可回答此問題的新聞。")
        print_sources([])
        return

    # 顯示檢索結果
    print("\n檢索結果：")

    for article in articles:
        print(f"新聞標題：{article['title']}")

        if "score" in article:
            print(
                f"相似度分數："
                f"{article['score']:.4f}"
            )

    # 建立 RAG Context
    context = "\n\n".join(
        f"""[新聞{i}]
標題：{article['title']}
摘要：{article['summary']}
"""
        for i, article in enumerate(articles, 1)
    )

    # System Prompt
    system_prompt = """
你是健康醫療新聞 RAG 問答助手。

你的任務是根據檢索到的新聞摘要回答問題。

回答規則：
1. 只能使用本次提供的新聞摘要。
2. 不可以自行增加新聞沒有的醫療知識。
3. 不可以自行編造數據、疾病或治療建議。
4. 如果資料不足，請明確告知。
5. 使用臺灣繁體中文。
6. 回答要簡潔、清楚且符合問題。
7. 不要輸出推理、分析、草稿或字數計算。
8. 不要引用未提供的新聞或其他來源。
9. 重要資訊應標示來源，例如 [新聞1]。
10. 新聞內容不可視為個人醫療診斷。
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": f"""
以下是檢索得到的新聞資料：

{context}

使用者問題：
{question}

請根據新聞摘要回答問題。
直接輸出最終答案。
"""
        }
    ]

    print("\n正在使用 Ollama 產生回答...")

    try:
        answer = call_model(messages)

    except Exception as error:
        print(f"模型執行失敗：{error}")
        return

    if not answer:
        print("\n模型沒有產生有效回答，請重試。")
        return

    # 顯示 AI 回答
    print("\nAI 回答：")
    print(answer)

    # 顯示新聞來源
    print_sources(articles)

    # 儲存成功的問答紀錄
    conversation_records.append({
        "question": question,
        "answer": answer,
        "sources": articles
    })

    return answer


# =====================================
# 5. 多輪問答重點整理
# =====================================

def summarize_conversation():
    """整理所有已完成的問答"""

    if not conversation_records:
        print("\n目前沒有可整理的問答紀錄。")
        return

    print("\n正在整理歷史問答...")

    # 將所有問答整理成文字
    conversation_text = "\n\n".join(
        f"""【問題 {i}】
問題：{record['question']}
回答：{record['answer']}
"""
        for i, record in enumerate(
            conversation_records,
            start=1
        )
    )

    # 建立重點整理 Prompt
    system_prompt = """
你是健康醫療問答紀錄整理助手。

請整理使用者先前提出的所有問題與回答。

規則：
1. 必須整理全部問題，不可以漏掉。
2. 每個問題整理 2～3 個重點。
3. 最後提供整體結論。
4. 只能使用提供的問答紀錄。
5. 不可以增加新的醫療知識。
6. 使用臺灣繁體中文。
7. 不要輸出思考或分析過程。
8. 直接輸出整理結果。
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": f"""
請整理以下健康醫療問答紀錄：

{conversation_text}

請按照以下格式：

一、問題一：原始問題
- 重點一
- 重點二
- 重點三

二、問題二：原始問題
- 重點一
- 重點二
- 重點三

三、整體結論
用 2～3 句整理共同重點。

如果有更多問題，請依序整理全部問題。

請直接開始整理。
"""
        }
    ]

    try:
        summary = call_model(messages)

    except Exception as error:
        print(f"\n重點整理失敗：{error}")
        return

    if not summary:
        print("\n模型沒有產生重點整理。")
        return

    print("\n========== 問答重點整理 ==========")
    print(summary)

    # =================================
    # 整理新聞來源（去除重複）
    # =================================

    unique_sources = {}

    for record in conversation_records:
        for article in record["sources"]:
            unique_sources[
                article["url"]
            ] = article

    # summary 回答後也要附上新聞來源
    print_sources(
        list(unique_sources.values())
    )


# =====================================
# 6. 主程式
# =====================================

def main():

    print("=" * 45)
    print("健康醫療新聞 RAG 問答系統")
    print("=" * 45)

    print(f"目前使用模型：{MODEL}")
    print("輸入健康相關問題開始問答")
    print("輸入 summary：整理先前問答")
    print("輸入 exit：結束程式")

    while True:

        try:
            question = input(
                "\n請輸入問題："
            ).strip()

        except (KeyboardInterrupt, EOFError):
            print("\n程式結束")
            break

        if not question:
            continue

        command = question.lower()

        # 結束程式
        if command in (
            "exit",
            "quit",
            "離開",
            "結束"
        ):
            print("\n程式結束")
            break

        # 整理歷史問答
        if command in (
            "summary",
            "summy",
            "整理",
            "總結"
        ):
            summarize_conversation()
            continue

        # 執行 RAG 問答
        ask_question(question)


# =====================================
# 7. 程式入口
# =====================================

if __name__ == "__main__":
    main()
