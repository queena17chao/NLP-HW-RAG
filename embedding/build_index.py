
import json
import sqlite3
from pathlib import Path

import faiss
import numpy as np
from ollama import Client

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

DB_PATH = DATA_DIR / "health_news.db"
INDEX_PATH = DATA_DIR / "news.index"
IDS_PATH = DATA_DIR / "news_ids.json"

MODEL = "embeddinggemma"
client = Client(host="http://localhost:11434")


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError("找不到 SQLite 資料庫")

    with sqlite3.connect(DB_PATH) as conn:
        articles = conn.execute("""
            SELECT id, title, summary
            FROM news
            WHERE summary IS NOT NULL
              AND TRIM(summary) != ''
            ORDER BY id
        """).fetchall()

    if not articles:
        print("沒有可向量化的摘要，請先執行摘要程式")
        return

    print(f"準備向量化 {len(articles)} 篇新聞")

    vectors = []
    news_ids = []

    for article_id, title, summary in articles:
        # 作業要求：將文章摘要轉換成向量
        response = client.embed(
            model=MODEL,
            input=summary
        )

        vector = np.asarray(
            response.embeddings[0],
            dtype=np.float32
        )

        vectors.append(vector)
        news_ids.append(article_id)

        print(f"完成向量化：{title}", flush=True)

    matrix = np.ascontiguousarray(
        np.vstack(vectors),
        dtype=np.float32
    )

    # 正規化後，以內積計算餘弦相似度
    faiss.normalize_L2(matrix)

    dimension = matrix.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(matrix)

    faiss.write_index(index, str(INDEX_PATH))

    IDS_PATH.write_text(
        json.dumps({
            "model": MODEL,
            "news_ids": news_ids
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n向量索引建立成功！")
    print(f"新聞數量：{index.ntotal}")
    print(f"向量維度：{dimension}")
    print(f"索引位置：{INDEX_PATH}")


if __name__ == "__main__":
    main()
