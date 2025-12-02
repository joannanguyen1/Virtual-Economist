import requests
import psycopg2
import pandas as pd
from psycopg2 import pool
from dotenv import load_dotenv
import os
import openai
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2.extras
import math
import json

# Load env
load_dotenv()

# Constants
OPEN_METEO_URL = "https://climate-api.open-meteo.com/v1/climate"
openai.api_key = os.getenv("OPENAI_API_KEY")

# DB config
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 10,
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

CITY_COORDS_FILE = "backend/uscities.csv"

def load_pa_cities():
    cities = pd.read_csv(CITY_COORDS_FILE)
    filtered = cities[
        (cities['state_name'].isin(['Arizona', 'Pennsylvania'])) &
        (cities['population'] > 1000)
    ]
    return filtered[['city', 'state_name', 'lat', 'lng']]

def fetch_and_aggregate_weather(lat, lon):
    year = datetime.now().year - 1
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "models": ["EC_Earth3P_HR"],
        "daily": [
            "temperature_2m_max", "temperature_2m_mean", "temperature_2m_min",
            "wind_speed_10m_mean", "snowfall_sum", "precipitation_sum"
        ]
    }

    try:
        response = requests.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data['daily'])
        df['time'] = pd.to_datetime(df['time'])
        df['month'] = df['time'].dt.strftime('%B-%Y')

        return df.groupby('month').mean(numeric_only=True).to_dict(orient='index')
    except Exception as e:
        print(f"Error fetching data for lat={lat}, lon={lon}: {e}")
        return None

def c_to_f(celsius):
    return round((celsius * 9/5) + 32, 1) if celsius is not None else None

def is_valid_stat(val):
    return val is not None and not (isinstance(val, float) and math.isnan(val))

def fetch_existing_metadata(city, state):
    conn = db_pool.getconn()
    city_state = f"{city}, {state}"
    try:
        with conn.cursor() as cur:
            query = """
            SELECT metadata
            FROM housing_data_embeddings
            WHERE SIMILARITY(metadata->>'city', %s) > 0.3
            ORDER BY SIMILARITY(metadata->>'city', %s) DESC
            LIMIT 1
            """
            cur.execute(query, (city_state, city_state))
            result = cur.fetchone()
            return result[0] if result else None
    finally:
        db_pool.putconn(conn)

def update_metadata_with_weather(city, updated_metadata, state):
    conn = db_pool.getconn()
    city_state = f"{city}, {state}"
    try:
        with conn.cursor() as cur:
            update_query = """
                WITH target AS (
                    SELECT ctid
                    FROM housing_data_embeddings
                    WHERE SIMILARITY(metadata->>'city', %s) > 0.3
                    ORDER BY SIMILARITY(metadata->>'city', %s) DESC
                    LIMIT 1
                )
                UPDATE housing_data_embeddings
                SET metadata = %s
                WHERE ctid IN (SELECT ctid FROM target)
            """
            cur.execute(update_query, (city_state, city_state, json.dumps(updated_metadata)))
            conn.commit()
    except Exception as e:
        print(f"Update failed for {city}: {e}")
    finally:
        db_pool.putconn(conn)


def process_city(row):
    city, state, lat, lon = row['city'], row['state_name'], row['lat'], row['lng']
    print(f"Processing {city}, {state}")

    existing_metadata = fetch_existing_metadata(city,state)
    if not existing_metadata:
        print(f"Skipping {city} — not found in housing_data_embeddings.")
        return

    weather_by_month = fetch_and_aggregate_weather(lat, lon)
    if not weather_by_month:
        return

    all_months_weather = {}

    for month, stats in weather_by_month.items():
        if not all(is_valid_stat(stats.get(k)) for k in [
            "temperature_2m_mean", "temperature_2m_min", "temperature_2m_max",
            "precipitation_sum", "wind_speed_10m_mean", "snowfall_sum"
        ]):
            continue

        all_months_weather[month] = {
            "avg_temperature_f": c_to_f(stats.get("temperature_2m_mean")),
            "min_temperature_f": c_to_f(stats.get("temperature_2m_min")),
            "max_temperature_f": c_to_f(stats.get("temperature_2m_max")),
            "precipitation_in": stats.get("precipitation_sum"),
            "windspeed_mph": stats.get("wind_speed_10m_mean"),
            "snowfall_in": stats.get("snowfall_sum")
        }

    if all_months_weather:
        existing_metadata["weather_by_month"] = all_months_weather
        update_metadata_with_weather(city, existing_metadata, state)

def main():
    cities = load_pa_cities()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_city, row) for _, row in cities.iterrows()]
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()
