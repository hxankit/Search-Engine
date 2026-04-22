import requests
from bs4 import BeautifulSoup
import mysql.connector
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

STOP_WORDS = {"the", "is", "at", "on", "and", "a", "an", "to", "in", "of",
              "it", "for", "with", "this", "that", "was", "are", "as", "be"}

def setup_db():
    conn = mysql.connector.connect(
        host="localhost", user="root", password="Anki@112", database="search_engine"
    )
    cursor = conn.cursor()

    # ✅ DROP and recreate to fix stale schema (word_count NULL issue)
    cursor.execute("DROP TABLE IF EXISTS word_index")
    cursor.execute("DROP TABLE IF EXISTS pages")

    cursor.execute("""
        CREATE TABLE pages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            url VARCHAR(2048),
            title TEXT,
            content LONGTEXT,
            word_count INT DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE word_index (
            id INT AUTO_INCREMENT PRIMARY KEY,
            word VARCHAR(255),
            page_id INT,
            count INT DEFAULT 0,
            UNIQUE KEY unique_word_page (word, page_id),
            FOREIGN KEY (page_id) REFERENCES pages(id)
        )
    """)
    conn.commit()
    return conn


def simple_crawler(seed_url, max_pages=10):
    conn = setup_db()
    cursor = conn.cursor()

    queue = [seed_url]
    visited = set()

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue

        try:
            print(f"Crawling: {url}")
            # ✅ Fixed: User-Agent header so sites don't block us
            response = requests.get(url, timeout=10, headers=HEADERS)

            # ✅ Skip non-HTML responses (PDFs, images, etc.)
            if "text/html" not in response.headers.get("Content-Type", ""):
                print(f"  ⚠ Skipped non-HTML: {url}")
                visited.add(url)
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            title = soup.title.string.strip() if soup.title else url
            text = soup.get_text(separator=' ').lower()
            clean_text = re.sub(r'[^a-z\s]', '', text)
            tokens = clean_text.split()

            # ✅ Skip pages with almost no content (bot-rejection pages)
            if len(tokens) < 20:
                print(f"  ⚠ Skipped low-content page: {url}")
                visited.add(url)
                continue

            word_counts = {}
            for word in tokens:
                if word not in STOP_WORDS and len(word) > 2:
                    word_counts[word] = word_counts.get(word, 0) + 1

            # ✅ INSERT page first, then get its ID
            cursor.execute(
                "INSERT INTO pages (url, title, content, word_count) VALUES (%s, %s, %s, %s)",
                (url, title, text, len(tokens))
            )
            conn.commit()
            page_id = cursor.lastrowid

            # ✅ Build inverted index
            for word, count in word_counts.items():
                cursor.execute(
                    """INSERT INTO word_index (word, page_id, count) VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE count = count + VALUES(count)""",
                    (word, page_id, count)
                )
            conn.commit()

            # ✅ Only follow links on the same domain to stay focused
            for link in soup.find_all('a', href=True):
                new_url = link['href']
                if new_url.startswith('http') and new_url not in visited:
                    queue.append(new_url)

            visited.add(url)
            print(f"  ✓ Indexed {len(word_counts)} unique words | word_count={len(tokens)}")

        except Exception as e:
            print(f"  ✗ Failed: {url} → {e}")
            visited.add(url)  # ✅ Mark failed URLs so we don't retry forever

    conn.close()
    print(f"\nDone! Crawled {len(visited)} pages.")


# ✅ Use a specific article, not the homepage
simple_crawler("https://en.wikipedia.org/wiki/Artificial_intelligence", max_pages=10)