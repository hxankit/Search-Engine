import requests
from bs4 import BeautifulSoup
import re
from db_setup import get_conn, init_db   # ✅ import from db_setup, not redefined here

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

STOP_WORDS = {
    "the", "is", "at", "on", "and", "a", "an", "to", "in", "of",
    "it", "for", "with", "this", "that", "was", "are", "as", "be",
    "by", "or", "but", "not", "from", "have", "had", "has", "will",
    "its", "we", "you", "he", "she", "they", "our", "your", "their"
}


def simple_crawler(seed_url, max_pages=5):
    conn = get_conn()
    cursor = conn.cursor()

    # Load already-crawled URLs so we never re-crawl
    cursor.execute("SELECT url FROM pages")
    already_crawled = {row[0] for row in cursor.fetchall()}

    queue = [seed_url]
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
                print(f"    ⚠ Skipped non-HTML")
                visited.add(url)
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            title  = soup.title.string.strip() if soup.title else url
            text   = soup.get_text(separator=' ').lower()
            clean  = re.sub(r'[^a-z\s]', '', text)
            tokens = clean.split()

            if len(tokens) < 20:
                print(f"    ⚠ Skipped low-content page ({len(tokens)} tokens)")
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

            for link in soup.find_all('a', href=True):
                new_url = link['href']
                if new_url.startswith('http') and new_url not in visited:
                    queue.append(new_url)

            visited.add(url)
            new_count += 1
            print(f"    ✓ Indexed {len(word_counts)} words | total tokens: {len(tokens)}")

        except Exception as e:
            print(f"    ✗ Failed: {e}")
            visited.add(url)

    conn.close()
    print(f"  → Done! {new_count} new pages indexed.\n")


SEED_URLS = [
    # Wikipedia
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Machine_learning",
    "https://en.wikipedia.org/wiki/Deep_learning",
    "https://en.wikipedia.org/wiki/Python_(programming_language)",
    "https://en.wikipedia.org/wiki/Climate_change",
    "https://en.wikipedia.org/wiki/World_War_II",
    "https://en.wikipedia.org/wiki/Quantum_computing",
    "https://en.wikipedia.org/wiki/Black_hole",
    # Tech news
    "https://arstechnica.com",
    "https://www.wired.com",
    "https://stackoverflow.blog",
    "https://dev.to",
    # Programming
    "https://docs.python.org/3/tutorial/index.html",
    "https://realpython.com",
    "https://www.geeksforgeeks.org/python-programming-language/",
    "https://www.freecodecamp.org/news",
    # Science
    "https://www.nasa.gov",
    "https://www.nationalgeographic.com/science",
    "https://www.scientificamerican.com",
    # Business
    "https://www.forbes.com/technology",
    "https://www.businessinsider.com",
    "https://hbr.org",
    # Education
    "https://ocw.mit.edu",
    "https://www.coursera.org/articles",
    # AI blogs
    "https://www.deepmind.com/blog",
    "https://huggingface.co/blog",
    "https://ai.googleblog.com",
    # General
    "https://www.britannica.com",
    "https://www.history.com",
]


if __name__ == "__main__":
    print("🗄  Setting up database...")
    init_db()                          # ✅ called from db_setup, runs once

    print("\n🕷  Starting crawler...\n")
    for url in SEED_URLS:
        print(f"{'='*55}")
        print(f"🌐 Seed: {url}")
        print('='*55)
        simple_crawler(url, max_pages=5)

    print("✅ All done! Run app.py and start searching.")