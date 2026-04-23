import requests
import re
import feedparser
from bs4 import BeautifulSoup
from db.connection import get_conn
from crawler.seeds import SEED_URLS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
from langdetect import detect

def is_english(text):
    try:
        return detect(text) == "en"
    except:
        return False
STOP_WORDS = {
    "the","is","at","on","and","a","an","to","in","of","it","for",
    "with","this","that","was","are","as","be","by","or","but","not",
    "from","have","had","has","will","its","we","you","he","she",
    "they","our","your","their"
}

# ── Auto-seed sources ────────────────────────────────────────────
RSS_FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://www.reddit.com/r/programming/.rss",
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index",
]

GOOGLE_TOPICS = [
    "latest tech news",
    "python programming",
    "machine learning research",
]
# ────────────────────────────────────────────────────────────────


def fetch_seeds_from_rss() -> list[str]:
    urls = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if hasattr(entry, "link"):
                    urls.append(entry.link)
            print(f"  ✓ RSS: {feed.feed.get('title', feed_url)} → {len(feed.entries)} URLs")
        except Exception as e:
            print(f"  ✗ RSS {feed_url} → {e}")
    return urls


def fetch_seeds_from_google(topic: str) -> list[str]:
    urls = []
    try:
        search_url = f"https://www.google.com/search?q={topic.replace(' ', '+')}"
        soup = BeautifulSoup(requests.get(search_url, headers=HEADERS, timeout=10).text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/url?q=http"):
                clean = href.split("/url?q=")[1].split("&")[0]
                urls.append(clean)
        print(f"  ✓ Google: '{topic}' → {len(urls)} URLs")
    except Exception as e:
        print(f"  ✗ Google '{topic}' → {e}")
    return urls


def auto_seed() -> list[str]:
    """Gather fresh seed URLs from RSS feeds and Google, skip already-crawled ones."""
    print("\n🌱 Auto-seeding...\n")

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM pages")
    already_crawled = {row[0] for row in cursor.fetchall()}
    conn.close()

    all_urls = []

    # Collect from RSS
    all_urls += fetch_seeds_from_rss()

    # Collect from Google topics
    for topic in GOOGLE_TOPICS:
        all_urls += fetch_seeds_from_google(topic)

    # Deduplicate and remove already-crawled
    fresh = list({u for u in all_urls if u not in already_crawled})
    print(f"\n  → {len(fresh)} fresh seed URLs ready.\n")
    return fresh


def crawl(seed_url: str, max_pages: int = 5):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT url FROM pages")
    already_crawled = {row[0] for row in cursor.fetchall()}

    queue     = [seed_url]
    visited   = set(already_crawled)
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
            text   = soup.get_text(separator=" ")
            if not is_english(text[:2000]):   # check only first part (fast)
                print("    ✗ Skipped (non-English)")
                visited.add(url)
                continue
            text = text.lower()
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

    # ── Static seeds (first run / fallback) ─────────────────────
    print("\n🕷  Crawling static seeds...\n")
    for url in SEED_URLS:
        print(f"{'='*55}\n🌐 {url}\n{'='*55}")
        crawl(url, max_pages=5)

    # ── Auto-discovered seeds ────────────────────────────────────
    fresh_seeds = auto_seed()
    print("\n🕷  Crawling auto-discovered seeds...\n")
    for url in fresh_seeds:
        print(f"{'='*55}\n🌐 {url}\n{'='*55}")
        crawl(url, max_pages=5)

    print("✅ Done! Run app to search.")