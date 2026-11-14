import os
import psycopg2
import pandas as pd
from datetime import datetime


def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database using environment variables.
    Defaults are for local development.
    """
    connection = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "docuverify_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
        port=os.getenv("DB_PORT", "5432"),
    )
    return connection


def init_db():
    """
    Creates the verification_logs table if it doesn't already exist.
    Also creates an s3_url column for cloud storage links.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_logs (
            id               SERIAL PRIMARY KEY,
            filename         VARCHAR(255) NOT NULL,
            status           VARCHAR(50)  NOT NULL,
            confidence_score FLOAT,
            ocr_confidence   FLOAT,
            tamper_score     FLOAT,
            tamper_verdict   VARCHAR(100),
            s3_url           TEXT,
            timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()


def log_verification(
    filename: str,
    status: str,
    confidence_score: float = 0.0,
    ocr_confidence: float = 0.0,
    tamper_score: float = 0.0,
    tamper_verdict: str = "Unknown",
    s3_url: str = None,
):
    """
    Inserts a full document verification record into the PostgreSQL database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO verification_logs
                (filename, status, confidence_score, ocr_confidence, tamper_score, tamper_verdict, s3_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (filename, status, confidence_score, ocr_confidence, tamper_score, tamper_verdict, s3_url))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"[Database Error] log_verification: {e}")


def fetch_all_logs() -> pd.DataFrame:
    """
    Fetches all verification log records from PostgreSQL as a Pandas DataFrame.
    Returns an empty DataFrame if the table is empty or DB is unreachable.
    """
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(
            "SELECT id, filename, status, confidence_score, ocr_confidence, "
            "tamper_score, tamper_verdict, s3_url, timestamp "
            "FROM verification_logs ORDER BY timestamp DESC;",
            conn,
        )
        conn.close()
        return df

    except Exception as e:
        print(f"[Database Error] fetch_all_logs: {e}")
        return pd.DataFrame()
