import sqlite3

DB_FILE = "quotation.db"

def migrate():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Check existing columns
    cur.execute("PRAGMA table_info(items)")
    cols = [row[1] for row in cur.fetchall()]

    if "unit" not in cols:
        print("Adding missing 'unit' column to items table...")
        cur.execute("ALTER TABLE items ADD COLUMN unit TEXT")
        conn.commit()
        print("Migration complete: 'unit' column added.")
    else:
        print("'unit' column already exists. No migration needed.")

    conn.close()

if __name__ == "__main__":
    migrate()
