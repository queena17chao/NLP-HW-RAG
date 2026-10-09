
from uuid import uuid4
import secrets

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
from ollama import Client
from rag.retriever import search_news


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

client = Client(host="http://localhost:11434")
MODEL = "qwen2.5:3b"

# 示範版：對話暫存在伺服器記憶體
chat_states = {}


def get_state():
    chat_id = session.get("chat_id")

    if not chat_id:
        chat_id = str(uuid4())
        session["chat_id"] = chat_id

    if chat_id not in chat_states:
        chat_states[chat_id] = {
            "turns": [],
            "last_articles": [],
            "summary": None,
            "summary_sources": []
        }

    return chat_states[chat_id]


def call_model(messages):
    response = client.chat(
        model=MODEL,
        messages=messages,
        stream=False,
        options={
            "temperature": 0.1,
            "num_predict": 1024
        }
    )

    answer = (response.message.content or "").strip()

    if not answer:
        raise ValueError("模型沒有產生有效回答")

    return answer


@app.get("/")
def index():
    state = get_state()

    return render_template(
        "index.html",
        turns=state["turns"],
        summary=state["summary"],
        summary_sources=state["summary_sources"]
    )


@app.post("/ask")
def ask():
    state = get_state()

    question = request.form.get(
        "question", ""
    ).strip()

    # Checkbox：勾選時重新檢索
    do_retrieve = "retrieve" in request.form

    if not question:
        flash("請先輸入問題")
        return redirect(url_for("index"))

    try:
        if do_retrieve:
            articles = search_news(
                question,
                top_k=1
            )
        else:
            # 不勾選時沿用上一輪新聞
            articles = state["last_articles"]

        if not articles:
            flash(
                "沒有可使用的新聞，"
                "請勾選「重新檢索新聞」再提問。"
            )
            return redirect(url_for("index"))

        # 建立新聞 Context
        context = "\n\n".join(
            f"""[新聞{i}]
標題：{article['title']}
摘要：{article['summary']}
"""
            for i, article in enumerate(
                articles, start=1
            )
        )

        system_prompt = """
你是健康醫療新聞 RAG 問答助手。

規則：
1. 只能根據提供的新聞摘要回答。
2. 不得自行增加新聞未提及的醫療資訊。
3. 資料不足時，請明確說明。
4. 使用臺灣繁體中文。
5. 直接回答問題，不輸出分析過程。
6. 新聞不可作為個人診斷或治療依據。
"""

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        # 沒有重新檢索時，帶入前兩輪對話
        # 用於回答「那這種情況呢？」等追問
        if not do_retrieve:
            for turn in state["turns"][-2:]:
                messages.append({
                    "role": "user",
                    "content": turn["question"]
                })
                messages.append({
                    "role": "assistant",
                    "content": turn["answer"]
                })

        messages.append({
            "role": "user",
            "content": f"""
以下是本次允許參考的新聞：

{context}

使用者問題：
{question}

請只根據新聞內容回答。
"""
        })

        answer = call_model(messages)

        # 只有成功回答才儲存紀錄
        state["turns"].append({
            "question": question,
            "answer": answer,
            "sources": articles,
            "retrieved": do_retrieve
        })

        state["last_articles"] = articles

        # 新增問答後，舊重點整理失效
        state["summary"] = None
        state["summary_sources"] = []

    except Exception as error:
        flash(f"執行失敗：{error}")

    return redirect(url_for("index"))


@app.post("/summary")
def summarize():
    state = get_state()
    turns = state["turns"]

    if not turns:
        flash("目前沒有可整理的問答紀錄")
        return redirect(url_for("index"))

    conversation = "\n\n".join(
        f"""問題 {i}：{turn['question']}
回答：{turn['answer']}"""
        for i, turn in enumerate(turns, start=1)
    )

    messages = [
        {
            "role": "system",
            "content": """
你是健康新聞問答紀錄整理助手。

請用臺灣繁體中文整理全部問答。

要求：
1. 每個問題分別整理 2～3 個重點。
2. 不得加入紀錄中沒有的資訊。
3. 最後提供整體結論。
4. 不輸出思考過程。
"""
        },
        {
            "role": "user",
            "content": f"""
請整理以下問答紀錄：

{conversation}

請依序整理每個問題，
最後提供 2～3 句整體結論。
"""
        }
    ]

    try:
        summary = call_model(messages)

        unique_sources = {}

        for turn in turns:
            for article in turn["sources"]:
                unique_sources[
                    article["url"]
                ] = article

        state["summary"] = summary
        state["summary_sources"] = list(
            unique_sources.values()
        )

    except Exception as error:
        flash(f"重點整理失敗：{error}")

    return redirect(url_for("index"))


@app.post("/reset")
def reset():
    state = get_state()

    state["turns"] = []
    state["last_articles"] = []
    state["summary"] = None
    state["summary_sources"] = []

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
