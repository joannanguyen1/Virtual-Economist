import psycopg2
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.schema import HumanMessage
from dotenv import load_dotenv
from sqlalchemy.sql import text
import openai
import os
load_dotenv()

db_config = {
    "dbname": os.getenv('DB_NAME'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "host": os.getenv('DB_HOST'),
    "port": os.getenv('DB_PORT')
}
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
client = openai

embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")
llm = ChatOpenAI(model="gpt-4o", temperature=0)

def extract_city_from_question(question):
    """
    Uses OpenAI's GPT model to classify housing-related questions and extract:
    - City name (if present)
    """
    prompt = f"""
    Question: "{question}"

    Please extract the city name from the question. If a city is mentioned, return it. If no city is found, return "No city found".
    Just return City string with no extra context
    if it is an abbreviation, return the full name.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert in classifying housing-related questions and extracting city names."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    # Extract the city from the response content
    extracted_city = response.choices[0].message.content.strip()

    if extracted_city == "No city found":
        return None

    return extracted_city


def generate_sql_query(question):
    """
    Generate a SQL query against housing_data_embeddings that returns either
    housing or nested weather data based on the user's question.
    """
    city_full = extract_city_from_question(question)
    has_city = bool(city_full)

    if has_city and "," in city_full:
        city, state = [p.strip() for p in city_full.split(",", 1)]
    else:
        city, state = city_full, None

    prompt = f"""
You are generating a SQL query for the Postgres table `housing_data_embeddings`, where:
- `embedding` is a vector embedding (not needed in this query).
- `metadata` is a JSONB column that contains:
    - metadata->>'city' (e.g., 'Philadelphia, Pennsylvania')
    - metadata->>'median_home_value' (string, needs to be cast to float for comparisons)
    - metadata->>'median_household_income' (same)
    - metadata->'weather_by_month'->'<month>-2024'->>'avg_temperature_f' (string)
    - metadata->'weather_by_month'->'<month>-2024'->>'min_temperature_f'
    - metadata->'weather_by_month'->'<month>-2024'->>'max_temperature_f'
    - metadata->'weather_by_month'->'<month>-2024'->>'precipitation_in'
    - metadata->'weather_by_month'->'<month>-2024'->>'windspeed_mph'
    - metadata->'weather_by_month'->'<month>-2024'->>'snowfall_in'

User question: "{question}"

Generate a SQL query with the following rules:

1. FROM `housing_data_embeddings`

2. If a city is mentioned (e.g., "{city_full}"), filter using fuzzy match:
   WHERE similarity(metadata->>'city', '{city_full}') > 0.3

3. If no city is mentioned, do not apply a city filter — assume the user wants results from any location.

4. Parse the user's question to extract any housing or income thresholds.
   - e.g., "under 200,000" → CAST(metadata->>'median_home_value' AS float) < 200000
   - "income over 60k" → CAST(metadata->>'median_household_income' AS float) > 60000

5. Parse the user's question to extract weather filters:
   - If the user mentions a month, normalize to "Month-2024" (e.g., "July" → "July-2024")
   - If the user mentions a season, use these mappings:
     • summer → June-2024, July-2024, August-2024
     • winter → December-2024, January-2024, February-2024
     • spring → March-2024, April-2024, May-2024
     • fall/autumn → September-2024, October-2024, November-2024

6. If no month is mentioned, include data from **all 12 months**, using "-2024" suffix.

7. Include in SELECT:
   - Always: metadata->>'city' AS city
   - For housing: CAST(metadata->>'median_home_value' AS float), CAST(metadata->>'median_household_income' AS float)
   - For each selected month, include:
     metadata->'weather_by_month'->>'<Month-2024>'->'avg_temperature_f', etc.
     with aliases like avg_temperature_f_july

8. Limit to 25 rows max.

Return ONLY the SQL query — no markdown, no explanation.
"""

    response = llm([HumanMessage(content=prompt)])
    return response.content.strip()


def query_data_with_generated_sql(question):
    """
    Generate the SQL query based on the user's question, execute it, and format results.
    Supports both housing and weather data queries.
    """
    try:
        sql_query = generate_sql_query(question)


        clean_sql_query = sql_query.strip().removeprefix("```sql").removesuffix("```").strip()


        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(clean_sql_query)
        results = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]

        if not results:
            return "No relevant information found in the database."


        context_lines = []
        for row in results[:20]:
            line = "\n".join(f"{col}: {val}" for col, val in zip(column_names, row))
            context_lines.append(line)

        context = "\n\n".join(context_lines)


        prompt = f"""
        You are a helpful housing assistant. You are answering a user’s question using real U.S. housing data.

        Here is the housing information you can use:

        {context}

        Please answer the user’s question in a friendly and conversational tone.
        - Use clear, everyday language.
        - If multiple cities match, summarize them as a list.
        - Do not make up any numbers. Only use the data shown above.
        - If the user asks for one city, just answer for that city.
        - If the city isn't found, politely explain that no matching data was available.
        - Use bullet points or paragraphs for readability.
        - Do not return Farenheit symbols (°) in the answer, anwer should be in form (37 F) for example.

        User's Question:
        "{question}"
        """
                
        # Generate the response from the LLM
        response = llm([HumanMessage(content=prompt)])
        return response.content

    except Exception as e:
        return f"An error occurred: {e}"

    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()


def extract_company_from_question(question):
    prompt = f"""
    Question: "{question}"

    Please extract the company name from the question. If a company is mentioned, return it. 
    If no company is found, return "No company found". 
    Just return the company name with no extra context.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert at identifying public company names in investment-related questions."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    company = response.choices[0].message.content.strip()
    return None if company.lower() == "no company found" else company

def generate_company_sql_query(question):
    prompt = f"""
    You are given a Postgres table called `embeddings` with the following schema:

    - `text` (string): a business description
    - `metadata` (jsonb) with keys:
        - name (string)
        - sector (string)
        - industry (string)
        - recommendation (string): e.g., "Strong Buy", "Hold", etc.
        - insider_ownership (float): 0.0 to 1.0
        - institutional_ownership (float): 0.0 to 1.0

    Write a SQL query that:
    - Selects name, sector, industry, recommendation, insider_ownership, institutional_ownership
    - Filters based on the user's question
    - Returns max 25 rows if no specific filter is found
    - Uses lowercase + ILIKE for matching text attributes (e.g., sector or industry)
    - Uses inequality filters for numeric values when relevant
    - Returns only the SQL query, no explanation

    User question: "{question}"
    """

    response = llm([HumanMessage(content=prompt)])
    return response.content.strip().strip("```sql").strip("```")

def query_companies(question):
    try:
        sql_query = generate_company_sql_query(question)

        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(sql_query)
        results = cur.fetchall()

        if not results:
            return "No relevant company data found."

        context = "\n".join([
            f"Company: {row[0]}\n"
            f"Sector: {row[1]}\n"
            f"Industry: {row[2]}\n"
            f"Recommendation: {row[3]}\n"
            f"Insider Ownership: {row[4]}\n"
            f"Institutional Ownership: {row[5]}\n"
            for row in results
        ])

        prompt = (
            f"Here are details about companies:\n\n{context}\n\n"
            f"Now answer the question: {question}"
        )

        response = llm([HumanMessage(content=prompt)])
        return response.content

    except Exception as e:
        return f"An error occurred: {e}"

    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()