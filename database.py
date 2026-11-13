import psycopg2
import os

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.
    """
    connection = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "docuverify_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
        port=os.getenv("DB_PORT", "5432")
    )
    return connection

def init_db():
    """
    Initializes the audit logs table if it doesn't already exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_logs (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            status VARCHAR(50) NOT NULL,
            confidence_score FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

def log_verification(filename, status, confidence_score=0.0):
    """
    Inserts a document verification record into the PostgreSQL database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO verification_logs (filename, status, confidence_score)
            VALUES (%s, %s, %s);
        ''', (filename, status, confidence_score))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")