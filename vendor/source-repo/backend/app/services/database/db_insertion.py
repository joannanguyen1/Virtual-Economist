import psycopg2
import json
from langchain_community.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

db_config = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002", api_key=os.getenv("OPEN_AI_KEY"))

with open("../dummy_data/company_data.json", "r") as f:
    companies = json.load(f)

try:
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    print("Deleting previous embeddings...")
    cur.execute("DELETE FROM embeddings;")
    conn.commit()
    print("Previous embeddings deleted.")

    for company in companies:
        ticker = company["ticker"]
        name = company["name"]
        sector = company["sector"]
        industry = company["industry"]
        market_cap = company["market_cap"]
        revenue = company["revenue"]
        pe_ratio = company["pe_ratio"]
        description = company["description"]
        recommendation = company["recommendation"]
        insider_ownership = company["insider_ownership"]
        institutional_ownership = company["institutional_ownership"]

        metadata = {
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "industry": industry,
            "market_cap": market_cap,
            "revenue": revenue,
            "pe_ratio": pe_ratio,
            "description": description,
            "recommendation": recommendation,
            "insider_ownership": insider_ownership,
            "institutional_ownership": institutional_ownership
        }

        combined_text = f"""
        Company Name: {name}
        Ticker: {ticker}
        Sector: {sector}
        Industry: {industry}
        Market Cap: {market_cap}
        Revenue: {revenue}
        Description: {description}
        Recommendation: {recommendation}
        Insider Ownership: {insider_ownership}
        Institutional Ownership: {institutional_ownership}
        """

        vector = embedding_model.embed_query(combined_text)

        insert_query = """
            INSERT INTO embeddings (vector_column, text, metadata)
            VALUES (%s, %s, %s);
        """
        cur.execute(insert_query, (json.dumps(vector), combined_text, json.dumps(metadata)))
        print("Inserted:", company["name"])

    conn.commit()
    print("All company data has been embedded and inserted successfully!")

    cur.close()
    conn.close()

except Exception as e:
    print("Error:", e)
