import sqlite3

conn = sqlite3.connect("file:Neostats Hackathon AI Usecase/ridewise.db?mode=ro", uri=True)
cursor = conn.cursor()

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("Tables in ridewise.db:", [t[0] for t in tables])

for t in tables:
    tname = t[0]
    count = cursor.execute(f"SELECT count(*) FROM {tname}").fetchone()[0]
    cursor.execute(f"SELECT * FROM {tname} LIMIT 2")
    cols = [d[0] for d in cursor.description]
    sample = cursor.fetchall()
    print(f"\n==========================================")
    print(f"Table: {tname} ({count} rows)")
    print("Columns:", cols)
    for row in sample:
        print("  Sample row:", dict(zip(cols, row)))
