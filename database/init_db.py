
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "data" / "news.json"
DB_PATH = ROOT / "data" / "health_news.db"


def main():
    with JSON_PATH.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL,
                summary TEXT,
                published_at TEXT,
                created_at TEXT NOT NULL,
                category TEXT
            )
        """)

        for article in articles:
            conn.execute("""
                INSERT INTO news (
                    title, url, content, summary,
                    published_at, created_at, category
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    published_at = excluded.published_at,
                    category = excluded.category
            """, (
                article["title"],
                article["url"],
                article["content"],
                article.get("summary"),
                article.get("published_at"),
                article["created_at"],
                article.get("category")
            ))

        conn.commit()

        total = conn.execute(
            "SELECT COUNT(*) FROM news"
        ).fetchone()[0]

        print(f"成功讀取 JSON：{len(articles)} 篇")
        print(f"資料庫目前共有：{total} 篇新聞")
        print(f"資料庫位置：{DB_PATH}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
