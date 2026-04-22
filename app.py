from flask import Flask, render_template_string, request
import mysql.connector
import math

app = Flask(__name__)

UI_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Mini Search Engine</title>
    <style>
        body { font-family: sans-serif; max-width: 750px; margin: 50px auto; line-height: 1.6; }
        .search-box { width: 80%; padding: 10px; border-radius: 20px; border: 1px solid #ccc; font-size: 1em; }
        .result { margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 15px; }
        .url { color: green; font-size: 0.85em; }
        .score { color: #888; font-size: 0.85em; }
        a { font-size: 1.15em; color: #1a0dab; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .no-results { color: #888; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>🔍 Mini Search Engine</h1>
    <form method="POST">
        <input type="text" name="query" class="search-box"
               value="{{ query }}" placeholder="Search...">
        <input type="submit" value="Search" style="padding:10px 16px; margin-left:8px;">
    </form>
    <hr>
    {% if query and not results %}
        <p class="no-results">No results found for <strong>{{ query }}</strong>.</p>
    {% endif %}
    {% for url, title, score, match_count in results %}
        <div class="result">
            <div class="url">{{ url }}</div>
            <a href="{{ url }}">{{ title }}</a>
            <p class="score">
                Relevance score: <strong>{{ "%.4f"|format(score) }}</strong>
                &nbsp;|&nbsp; Terms matched: <strong>{{ match_count }}</strong>
            </p>
        </div>
    {% endfor %}
</body>
</html>
'''

def get_conn():
    return mysql.connector.connect(
        host="localhost", user="root", password="Anki@112", database="search_engine"
    )

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
        #                 ✅ COALESCE prevents NULL word_count from crashing TF calc

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


@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    query = ""
    if request.method == 'POST':
        query = request.form['query'].strip()
        if query:
            results = search(query)
    return render_template_string(UI_TEMPLATE, results=results, query=query)


if __name__ == '__main__':
    app.run(debug=True)