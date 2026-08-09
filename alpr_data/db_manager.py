import os
import sqlite3
import json

class DBManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.getenv('DB_PATH', 'data/alpr.db')
        self.db_path = db_path
        
        # Ensure parent directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        self._ensure_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self):
        schema = """
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
        try:
            with self._get_connection() as conn:
                conn.execute(schema)
                conn.commit()
        except Exception as e:
            print(f"Error initializing tables: {e}")

    def insert_detection(self, plate_number, confidence=None, vehicle_make=None, 
                         vehicle_model=None, vehicle_color=None, body_type=None,
                         orientation=None, year=None, detection_date=None, 
                         detection_time=None, image_path=None, raw_json=None):
        query = """
        INSERT INTO detections (
            plate_number, confidence, vehicle_make, vehicle_model, 
            vehicle_color, body_type, orientation, year,
            detection_date, detection_time, image_path, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        if isinstance(raw_json, dict):
            raw_json = json.dumps(raw_json)
            
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (
                    plate_number, confidence, vehicle_make, vehicle_model,
                    vehicle_color, body_type, orientation, year,
                    detection_date, detection_time, image_path, raw_json
                ))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error inserting detection: {e}")
            return None

    def get_all_detections(self):
        query = "SELECT * FROM detections ORDER BY detection_date DESC, detection_time DESC"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching all detections: {e}")
            return []

    def get_recent_detections(self, limit=5):
        query = "SELECT * FROM detections ORDER BY id DESC LIMIT ?"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching recent detections: {e}")
            return []

    def search_by_plate(self, plate_number):
        query = "SELECT * FROM detections WHERE plate_number LIKE ? ORDER BY detection_date DESC"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (f"%{plate_number}%",))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error searching by plate: {e}")
            return []

if __name__ == "__main__":
    # Quick Test
    db = DBManager()
    id = db.insert_detection(
        plate_number="TEST123", 
        confidence=95.5, 
        vehicle_make="Tesla", 
        vehicle_model="Model 3", 
        vehicle_color="Red"
    )
    print(f"Inserted test record with ID: {id}")
    recent = db.get_recent_detections(1)
    print(f"Recent detection: {recent}")
