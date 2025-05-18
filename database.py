import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

print("Conexión con:", os.getenv("DB_NAME"), os.getenv("DB_USER"))


def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", 5432),
    )
