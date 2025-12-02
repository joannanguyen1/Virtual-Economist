import requests
import json
import os
import psycopg2
from psycopg2 import pool
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
load_dotenv()

# API Keys
API_KEY = os.getenv("SCRAPER_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# PostgreSQL Config
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Setup PostgreSQL Connection Pool (better performance)
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 10, host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
)

# Census API Variables
variables = ['B19013_001E', 'B25077_001E']
url = f'https://api.census.gov/data/2023/acs/acs5?get=NAME,{",".join(variables)}&for=place:*&in=state:*&key={API_KEY}'

def generate_embedding_parallel(texts):
    """Generate embeddings for a list of texts in parallel using OpenAI API."""
    client = OpenAI()  # No need to pass api_key explicitly if set as env variable

    embeddings = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_text = {executor.submit(client.embeddings.create, model="text-embedding-ada-002", input=text): text for text in texts}

        for future in as_completed(future_to_text):
            try:
                result = future.result()
                embeddings.append(result.data[0].embedding)
            except Exception as e:
                print(f"Embedding generation failed for '{future_to_text[future]}': {e}")
                embeddings.append(None)  # Maintain indexing even if an embedding fails

    return embeddings

def batch_insert_embeddings(batch_data):
    """Insert a batch of embeddings into PostgreSQL using connection pooling."""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        insert_query = """
        INSERT INTO housing_data_embeddings (embedding, metadata)
        VALUES (%s, %s)
        """
        cursor.executemany(insert_query, batch_data)
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Database insert failed: {e}")
    finally:
        db_pool.putconn(conn)

def get_data():
    """Fetch Census API data, process it, and store embeddings in PostgreSQL."""
    response = requests.get(url)
    if response.status_code != 200:
        print(f'Error: Unable to fetch data (Status code: {response.status_code})')
        return

    data = response.json()
    rows = data[1:]  # Skip header

    batch_size = 500
    batch_data = []
    texts_to_embed = []

    for i, row in enumerate(rows):
        city = row[0]
        median_household_income = row[1]
        median_home_value = row[2]

        # Handle missing or invalid values
        try:
            median_household_income = int(median_household_income)
            median_home_value = int(median_home_value)
        except ValueError:
            continue  # Skip invalid entries

        if median_household_income == -666666666 or median_home_value == -666666666:
            continue

        metadata = {
            'city': city,
            'median_household_income': median_household_income,
            'median_home_value': median_home_value,
        }

        texts_to_embed.append(city)
        batch_data.append((city, metadata))  # Store city to match embedding

        # Process batch when batch size is reached
        if len(texts_to_embed) >= batch_size:
            embeddings = generate_embedding_parallel(texts_to_embed)
            batch_data_with_embeddings = list(zip(embeddings, [json.dumps(metadata) for _, metadata in batch_data if embeddings]))

            batch_insert_embeddings(batch_data_with_embeddings)
            batch_data = []
            texts_to_embed = []

    # Insert remaining data
    if batch_data:
        embeddings = generate_embedding_parallel(texts_to_embed)
        batch_data_with_embeddings = list(zip(embeddings, [json.dumps(metadata) for _, metadata in batch_data if embeddings]))

        batch_insert_embeddings(batch_data_with_embeddings)

if __name__ == "__main__":
    get_data()
