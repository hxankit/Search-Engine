from db.connection import get_conn

def init_db():
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
    print("✅ Database ready.")

if __name__ == "__main__":
    init_db()