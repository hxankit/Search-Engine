from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import mysql.connector
import math
from typing import Optional

app = FastAPI()

UI_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mini Search Engine</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: sans-serif; max-width: 750px; margin: 50px auto; line-height: 1.6; padding: 0 20px; }
        h1 { margin-bottom: 20px; }
        .search-row { display: flex; gap: 10px; margin-bottom: 20px; }
        .search-box { flex: 1; padding: 10px 16px; border-radius: 20px; border: 1px solid #ccc; font-size: 1em; }
        .search-btn { padding: 10px 20px; border: none; border-radius: 20px; background: #4285f4; color: white; font-size: 1em; cursor: pointer; }
        .search-btn:hover { background: #2a6dd9; }
        hr { border: none; border-top: 1px solid #eee; margin-bottom: 20px; }
        .result { margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 15px; }
        .url { color: green; font-size: 0.85em; margin-bottom: 2px; }
        .score { color: #888; font-size: 0.85em; margin-top: 4px; }
        a { font-size: 1.15em; color: #1a0dab; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .no-results { color: #888; margin-top: 20px; }
        .result-count { color: #555; font-size: 0.9em; margin-bottom: 16px; }
    </style>
</head>
<body>
    <h1>🔍 Mini Search Engine</h1>
    <form method="POST" action="/search">
        <div class="search-row">
            <input type="text" name="query" class="search-box"
                   value="{{ query }}" placeholder="Search..." autofocus>
            <button type="submit" class="search-btn">Search</button>
        </div>
    </form>
    <hr>
    {% if query and not results %}
        <p class="no-results">No results found for <strong>{{ query }}</strong>.</p>
    {% endif %}
    {% if results %}
        <p class="result-count">About {{ results|length }} result(s) for <strong>{{ query }}</strong></p>
        {% for url, title, score, match_count in results %}
            <div class="result">
                <div class="url">{{ url }}</div>
                <a href="{{ url }}" target="_blank">{{ title }}</a>
                <p class="score">
                    Relevance score: <strong>{{ "%.4f" % score }}</strong>
                    &nbsp;|&nbsp; Terms matched: <strong>{{ match_count }}</strong>
                </p>
            </div>
        {% endfor %}
    {% endif %}
</body>
</html>
"""

# ── Jinja2 setup (inline templates) ─────────────────────────────────────────
from jinja2 import Environment
jinja_env = Environment()
jinja_env.globals.update(len=len)

def render(template_str: str, **context) -> HTMLResponse:
    tmpl = jinja_env.from_string(template_str)
    return HTMLResponse(tmpl.render(**context))


# ── DB ───────────────────────────────────────────────────────────────────────
def get_conn():
    return mysql.connector.connect(
        host="localhost", user="root", password="Anki@112", database="search_engine"
    )


# ── TF-IDF Search ────────────────────────────────────────────────────────────
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

    scores = {}
    matches = {}
    meta = {}

    for term in tokens:
        cursor.execute(
            "SELECT COUNT(DISTINCT page_id) FROM word_index WHERE word = %s", (term,)
        )
        doc_freq = cursor.fetchone()[0]
        if doc_freq == 0:
            continue

        idf = math.log((total_pages + 1) / (doc_freq + 1)) + 1

        cursor.execute("""
            SELECT p.id, p.url, p.title, COALESCE(p.word_count, 1), i.count
            FROM pages p
            JOIN word_index i ON p.id = i.page_id
            WHERE i.word = %s
        """, (term,))

        for page_id, url, title, word_count, term_count in cursor.fetchall():
            tf = term_count / max(word_count, 1)
            tfidf = tf * idf
            scores[page_id] = scores.get(page_id, 0) + tfidf
            matches[page_id] = matches.get(page_id, 0) + 1
            meta[page_id] = (url, title)

    conn.close()

    ranked = sorted(
        scores.keys(),
        key=lambda pid: (matches[pid], scores[pid]),
        reverse=True
    )

    return [
        (meta[pid][0], meta[pid][1], scores[pid], matches[pid])
        for pid in ranked[:10]
    ]


# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home():
    return render(UI_TEMPLATE, query="", results=[])


@app.post("/search", response_class=HTMLResponse)
def do_search(query: str = Form(...)):
    query = query.strip()
    results = search(query) if query else []
    return render(UI_TEMPLATE, query=query, results=results)

