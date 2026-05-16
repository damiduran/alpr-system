import sqlite3
import os

DB_PATH = 'alpr_data/alpr.db'

SCHEMA = """
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number TEXT NOT NULL,
    confidence REAL,
    vehicle_make TEXT,
    vehicle_model TEXT,
    vehicle_color TEXT,
    body_type TEXT,
    orientation TEXT,
    year TEXT,
    detection_date TEXT,
    detection_time TEXT,
    image_path TEXT,
    raw_json TEXT
);
"""

def init_db():
    print(f"Initializing database at {DB_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executescript(SCHEMA)
        conn.commit()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == "__main__":
    init_db()
