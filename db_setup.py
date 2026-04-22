import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Anki@112",
    "database": "search_engine"
}

def get_conn():
    """Just returns a connection — no table creation, no dropping."""
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    """
    Run ONCE to create tables fresh.
    Wipes all existing data and recreates tables.
    """
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS word_index")
    cursor.execute("DROP TABLE IF EXISTS pages")

    cursor.execute("""
        CREATE TABLE pages (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            url        VARCHAR(2048),
            title      TEXT,
            content    LONGTEXT,
            word_count INT DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE word_index (
            id      INT AUTO_INCREMENT PRIMARY KEY,
            word    VARCHAR(255),
            page_id INT,
            count   INT DEFAULT 0,
            UNIQUE KEY unique_word_page (word, page_id),
            FOREIGN KEY (page_id) REFERENCES pages(id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database setup complete! Tables created fresh.")


if __name__ == "__main__":
    init_db()