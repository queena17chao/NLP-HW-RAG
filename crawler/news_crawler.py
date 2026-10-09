
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
import trafilatura
from bs4 import BeautifulSoup

BASE_URL = "https://www.healthnews.com.tw"
CATEGORY_URL = (
    "https://www.healthnews.com.tw/channel/"
    "f72c8a39-1105-2663-255a-b925ad108bac/"
)
MAX_ARTICLES = 10
OUTPUT_FILE = Path("data/news.json")

session = requests.Session()
session.headers.update({
    "User-Agent": "HealthRAGCourseProject/1.0"
})


def get_html(url):
    response = session.get(url, timeout=20)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def get_article_links():
    """從營養飲食分類取得新聞連結"""
    html = get_html(CATEGORY_URL)
    soup = BeautifulSoup(html, "html.parser")

    links = []
    seen = set()

    for a in soup.select('a[href*="/article/"]'):
        url = urljoin(BASE_URL, a.get("href", ""))
        path = urlparse(url).path

        if not re.fullmatch(r"/article/\d+/?", path):
            continue

        if url not in seen:
            links.append(url)
            seen.add(url)

        if len(links) >= MAX_ARTICLES:
            break

    return links


def parse_article(url, article_id):
    """擷取單篇新聞"""
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1")
    if not title_tag:
        raise ValueError("找不到文章標題")

    title = title_tag.get_text(" ", strip=True)

    content = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        favor_precision=True
    )

    if not content or len(content) < 100:
        raise ValueError("文章正文擷取失敗")

    metadata = trafilatura.extract_metadata(html)
    published_at = metadata.date if metadata else None

    if not published_at:
        match = re.search(
            r"20\d{2}[-/]\d{2}[-/]\d{2}",
            soup.get_text(" ", strip=True)
        )
        published_at = match.group(0) if match else None

    return {
        "id": article_id,
        "title": title,
        "url": url,
        "content": content,
        "summary": None,
        "published_at": published_at,
        "created_at": datetime.now(
            ZoneInfo("Asia/Taipei")
        ).isoformat(timespec="seconds"),
        "category": "營養飲食"
    }


def main():
    links = get_article_links()
    print(f"找到 {len(links)} 篇新聞連結")

    articles = []

    for url in links:
        try:
            article = parse_article(
                url, len(articles) + 1
            )
            articles.append(article)
            print(f"成功：{article['title']}")

        except Exception as error:
            print(f"失敗：{url}，原因：{error}")

        time.sleep(2)

    OUTPUT_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            articles,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(f"\n完成！成功取得 {len(articles)} 篇")
    print(f"資料位置：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()
