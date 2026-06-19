import csv
import sqlite3

CSV_PATH = "metadata.csv"
DB_PATH = "programs.db"


def build():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # drop the table if it exists, then create a new one
    cur.execute("DROP TABLE IF EXISTS programs")
    cur.execute("""
    CREATE TABLE programs (
        filename TEXT,
        title TEXT,
        college TEXT,
        level TEXT,
        url TEXT
    )
    """)

    # read the csv and insert the data into the database
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            (r["filename"], r["title"], r["college"], r["level"], r["url"])
            for r in reader
        ] # list of tuples
    
    cur.executemany("INSERT INTO programs VALUES (?, ?, ?, ?, ?)", rows) 
    conn.commit() 

    # verify
    count = cur.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
    print(f"Inserted {count} rows into {DB_PATH}")

    print("\nSample rows:")
    for row in cur.execute("SELECT title, college, level FROM programs LIMIT 5"):
        print("  ", row)
    
    # Show the counts by college
    print("\nPrograms per college:")
    for row in cur.execute(
        "SELECT college, COUNT(*) FROM programs GROUP BY college ORDER BY COUNT(*) DESC"
    ):
        print("  ", row)

    conn.close()

if __name__ == "__main__":
    build()