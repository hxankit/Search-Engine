from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import math
from jinja2 import Environment
from db_setup import get_conn              # ✅ single source of truth

app = FastAPI()

UI_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Search Engine</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'DM Sans', sans-serif;
            background: #f5f5f0;
            min-height: 100vh;
            padding: 0 20px 60px;
        }
        .header { max-width: 700px; margin: 0 auto; padding: 48px 0 32px; }
        .header h1 { font-size: 2rem; font-weight: 600; letter-spacing: -0.5px; color: #111; }
        .header h1 span { color: #4285f4; }
        .search-wrap { max-width: 700px; margin: 0 auto 32px; position: relative; }
        .search-box {
            width: 100%; padding: 14px 120px 14px 20px;
            border-radius: 12px; border: 2px solid #ddd;
            font-size: 1rem; font-family: 'DM Sans', sans-serif;
            background: #fff; transition: border-color 0.2s; outline: none;
        }
        .search-box:focus { border-color: #4285f4; }
        .search-btn {
            position: absolute; right: 6px; top: 6px;
            padding: 8px 20px; border: none; border-radius: 8px;
            background: #4285f4; color: #fff; font-size: 0.95rem;
            font-family: 'DM Sans', sans-serif; font-weight: 500;
            cursor: pointer; transition: background 0.2s;
        }
        .search-btn:hover { background: #2a6dd9; }

        #loading {
            display: none; position: fixed; inset: 0;
            background: rgba(245,245,240,0.85); backdrop-filter: blur(4px);
            z-index: 100; flex-direction: column;
            align-items: center; justify-content: center; gap: 16px;
        }
        #loading.active { display: flex; }
        .spinner {
            width: 40px; height: 40px; border: 3px solid #ddd;
            border-top-color: #4285f4; border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loading-text {
            font-size: 0.95rem; color: #555; font-family: 'DM Mono', monospace;
            animation: pulse 1.2s ease-in-out infinite;
        }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

        .results-wrap { max-width: 700px; margin: 0 auto; }
        .result-count { font-size: 0.85rem; color: #888; margin-bottom: 20px; font-family: 'DM Mono', monospace; }
        .result {
            background: #fff; border-radius: 12px; padding: 18px 20px;
            margin-bottom: 14px; border: 1px solid #e8e8e4;
            transition: box-shadow 0.2s, transform 0.2s;
            animation: fadeUp 0.3s ease both;
        }
        .result:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.08); transform: translateY(-1px); }
        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(10px); }
            to   { opacity: 1; transform: translateY(0); }
        }
        .result:nth-child(1){animation-delay:0.05s} .result:nth-child(2){animation-delay:0.10s}
        .result:nth-child(3){animation-delay:0.15s} .result:nth-child(4){animation-delay:0.20s}
        .result:nth-child(5){animation-delay:0.25s}
        .result-url {
            font-size: 0.78rem; color: #3a7d44; font-family: 'DM Mono', monospace;
            margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .result a {
            font-size: 1.05rem; font-weight: 500; color: #1a0dab;
            text-decoration: none; display: block; margin-bottom: 6px;
        }
        .result a:hover { text-decoration: underline; }
        .result-meta { display: flex; gap: 16px; font-size: 0.78rem; color: #aaa; font-family: 'DM Mono', monospace; }
        .no-results { text-align: center; padding: 60px 0; color: #999; }
        .no-results strong { color: #333; }
    </style>
</head>
<body>
    <div id="loading">
        <div class="spinner"></div>
        <div class="loading-text">searching the index...</div>
    </div>

    <div class="header">
        <h1>🔍 Mini <span>Search</span> Engine</h1>
    </div>

    <div class="search-wrap">
        <form id="searchForm" method="POST" action="/search">
            <input type="text" name="query" class="search-box"
                   value="{{ query }}" placeholder="Search anything..." autofocus>
            <button type="submit" class="search-btn">Search</button>
        </form>
    </div>

    <div class="results-wrap">
        {% if query and not results %}
            <div class="no-results">
                No results found for <strong>{{ query }}</strong>.<br><br>
                Try a different keyword.
            </div>
        {% endif %}
        {% if results %}
            <p class="result-count">About {{ results|length }} result(s) for "{{ query }}"</p>
            {% for url, title, score, match_count in results %}
                <div class="result">
                    <div class="result-url">{{ url }}</div>
                    <a href="{{ url }}" target="_blank">{{ title }}</a>
                    <div class="result-meta">
                        <span>⚡ score: {{ "%.4f" % score }}</span>
                        <span>🔤 terms matched: {{ match_count }}</span>
                    </div>
                </div>
            {% endfor %}
        {% endif %}
    </div>

    <script>
        document.getElementById('searchForm').addEventListener('submit', function() {
            const query = this.querySelector('input[name="query"]').value.trim();
            if (query) document.getElementById('loading').classList.add('active');
        });
        window.addEventListener('pageshow', function() {
            document.getElementById('loading').classList.remove('active');
        });
    </script>
</body>
</html>
"""

jinja_env = Environment()
jinja_env.globals.update(len=len)

def render(template_str: str, **context) -> HTMLResponse:
    return HTMLResponse(jinja_env.from_string(template_str).render(**context))


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
            FROM pages p
            JOIN word_index i ON p.id = i.page_id
            WHERE i.word = %s
        """, (term,))

        for page_id, url, title, word_count, term_count in cursor.fetchall():
            tfidf = (term_count / max(word_count, 1)) * idf
            scores[page_id] = scores.get(page_id, 0) + tfidf
            matches[page_id] = matches.get(page_id, 0) + 1
            meta[page_id] = (url, title)

    conn.close()

    ranked = sorted(scores.keys(), key=lambda pid: (matches[pid], scores[pid]), reverse=True)
    return [(meta[pid][0], meta[pid][1], scores[pid], matches[pid]) for pid in ranked[:10]]


@app.get("/", response_class=HTMLResponse)
def home():
    return render(UI_TEMPLATE, query="", results=[])

@app.post("/search", response_class=HTMLResponse)
def do_search(query: str = Form(...)):
    query = query.strip()
    results = search(query) if query else []
    return render(UI_TEMPLATE, query=query, results=results)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)