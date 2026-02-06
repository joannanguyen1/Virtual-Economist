import psycopg2
import json
from dotenv import load_dotenv
import os

load_dotenv()

db_config = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

try:
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    # Query to fetch all rows from the embeddings table
    cur.execute("SELECT id, vector_column, text, metadata FROM embeddings;")
    rows = cur.fetchall()

    print("Embedding Table Contents:")
    for row in rows:
        row_id = row[0]
        vector = json.loads(row[1])[:5]
        text = row[2]
        metadata = json.loads(row[3]) if isinstance(row[3], str) else row[3]

        print(f"ID: {row_id}")
        print(f"Text: {text}")
        print(f"Vector (truncated): {vector} ...")
        print("Metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        print("-" * 50)

    cur.close()
    conn.close()

except Exception as e:
    print("Error:", e)
