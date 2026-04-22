import requests
import re
from bs4 import BeautifulSoup
from db.connection import get_conn
from crawler.seeds import SEED_URLS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

STOP_WORDS = {
    "the","is","at","on","and","a","an","to","in","of","it","for",
    "with","this","that","was","are","as","be","by","or","but","not",
    "from","have","had","has","will","its","we","you","he","she",
    "they","our","your","their"
}

def crawl(seed_url: str, max_pages: int = 5):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT url FROM pages")
    already_crawled = {row[0] for row in cursor.fetchall()}

    queue   = [seed_url]
    visited = set(already_crawled)
    new_count = 0

    while queue and new_count < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue

        try:
            print(f"  Crawling: {url}")
            response = requests.get(url, timeout=10, headers=HEADERS)

            if "text/html" not in response.headers.get("Content-Type", ""):
                visited.add(url)
                continue

            soup   = BeautifulSoup(response.text, "html.parser")
            title  = soup.title.string.strip() if soup.title else url
            text   = soup.get_text(separator=" ").lower()
            clean  = re.sub(r"[^a-z\s]", "", text)
            tokens = clean.split()

            if len(tokens) < 20:
                visited.add(url)
                continue

            word_counts = {}
            for word in tokens:
                if word not in STOP_WORDS and len(word) > 2:
                    word_counts[word] = word_counts.get(word, 0) + 1

            cursor.execute(
                "INSERT INTO pages (url, title, content, word_count) VALUES (%s, %s, %s, %s)",
                (url, title, text, len(tokens))
            )
            conn.commit()
            page_id = cursor.lastrowid

            for word, count in word_counts.items():
                cursor.execute(
                    """INSERT INTO word_index (word, page_id, count) VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE count = count + VALUES(count)""",
                    (word, page_id, count)
                )
            conn.commit()

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("http") and href not in visited:
                    queue.append(href)

            visited.add(url)
            new_count += 1
            print(f"    ✓ {len(word_counts)} words | {len(tokens)} tokens")

        except Exception as e:
            print(f"    ✗ {e}")
            visited.add(url)

    conn.close()
    print(f"  → {new_count} new pages indexed.\n")


if __name__ == "__main__":
    from db.setup import init_db
    print("🗄  Setting up DB...")
    init_db()

    print("\n🕷  Crawling...\n")
    for url in SEED_URLS:
        print(f"{'='*55}\n🌐 {url}\n{'='*55}")
        crawl(url, max_pages=5)

    print("✅ Done! Run app to search.")