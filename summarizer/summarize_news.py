
import sqlite3
from pathlib import Path
from ollama import Client

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "health_news.db"

client = Client(host="http://localhost:11434")


def generate_summary(title, content):
    prompt = f"""
請根據以下新聞產生繁體中文摘要。

要求：
1. 僅根據文章內容整理，不要捏造資訊。
2. 摘要約 150～250 字。
3. 保留重要健康知識與注意事項。
4. 直接輸出摘要，不需要前言。

新聞標題：{title}

文章全文：
{content}
"""

    response = client.chat(
        model="qwen3:4b",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.2},
        think=False
    )

    return response.message.content.strip()


def main():
    if not DB_PATH.exists():
        print("找不到資料庫，請先執行 init_db.py")
        return

    with sqlite3.connect(DB_PATH) as conn:
        articles = conn.execute("""
            SELECT id, title, content
            FROM news
            WHERE summary IS NULL OR TRIM(summary) = ''
        """).fetchall()

        print(f"待摘要文章：{len(articles)} 篇")

        for article_id, title, content in articles:
            print(f"\n正在處理：{title}", flush=True)

            try:
                summary = generate_summary(title, content)

                if not summary:
                    raise ValueError("模型回傳空摘要")

                conn.execute(
                    "UPDATE news SET summary = ? WHERE id = ?",
                    (summary, article_id)
                )
                conn.commit()

                print(f"摘要完成：{summary[:100]}...")

            except Exception as e:
                print(f"摘要失敗：{e}")


if __name__ == "__main__":
    main()
