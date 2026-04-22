import math
from db.connection import get_conn

def search(query: str):
    conn = get_conn()
    cursor = conn.cursor()

    tokens = [w for w in query.lower().split() if len(w) > 1]
    if not tokens:
        conn.close()
        return []

    cursor.execute("SELECT COUNT(*) FROM pages")
    total_pages = cursor.fetchone()[0]
    if total_pages == 0:
        conn.close()
        return []

    scores, matches, meta = {}, {}, {}

    for term in tokens:
        cursor.execute("SELECT COUNT(DISTINCT page_id) FROM word_index WHERE word = %s", (term,))
        doc_freq = cursor.fetchone()[0]
        if doc_freq == 0:
            continue

        idf = math.log((total_pages + 1) / (doc_freq + 1)) + 1

        cursor.execute("""
            SELECT p.id, p.url, p.title, COALESCE(p.word_count, 1), i.count
            FROM pages p JOIN word_index i ON p.id = i.page_id
            WHERE i.word = %s
        """, (term,))

        for page_id, url, title, word_count, term_count in cursor.fetchall():
            tfidf = (term_count / max(word_count, 1)) * idf
            scores[page_id]  = scores.get(page_id, 0) + tfidf
            matches[page_id] = matches.get(page_id, 0) + 1
            meta[page_id]    = (url, title)

    conn.close()
    ranked = sorted(scores, key=lambda pid: (matches[pid], scores[pid]), reverse=True)
    return [(meta[p][0], meta[p][1], scores[p], matches[p]) for p in ranked[:10]]