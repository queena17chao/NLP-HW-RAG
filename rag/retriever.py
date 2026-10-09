
import json
import sqlite3
from pathlib import Path

import faiss
import numpy as np
from ollama import Client

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

client = Client(host="http://localhost:11434")

index = faiss.read_index(str(DATA / "news.index"))

metadata = json.loads(
    (DATA / "news_ids.json").read_text(encoding="utf-8")
)

NEWS_IDS = metadata["news_ids"]
EMBED_MODEL = metadata["model"]

if index.ntotal != len(NEWS_IDS):
    raise ValueError("FAISS 索引與新聞 ID 數量不一致")


def search_news(question, top_k=3):
    response = client.embed(
        model=EMBED_MODEL,
        input=question
    )

    query = np.asarray(
        response.embeddings,
        dtype=np.float32
    )

    faiss.normalize_L2(query)

    scores, positions = index.search(
        query, min(top_k, index.ntotal)
    )

    results = []

    with sqlite3.connect(DATA / "health_news.db") as conn:
        conn.row_factory = sqlite3.Row

        for score, position in zip(scores[0], positions[0]):
            if position < 0:
                continue

            article_id = NEWS_IDS[int(position)]

            row = conn.execute("""
                SELECT id, title, url, summary,
                       published_at, created_at
                FROM news
                WHERE id = ?
            """, (article_id,)).fetchone()

            if row:
                article = dict(row)
                article["score"] = float(score)
                results.append(article)

    return results
