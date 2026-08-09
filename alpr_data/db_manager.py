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
        detections_schema = """
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
        users_schema = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer'
        );
        """
        try:
            with self._get_connection() as conn:
                conn.execute(detections_schema)
                conn.execute(users_schema)
                conn.commit()
                
                # Seed default users if table is empty
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                if cursor.fetchone()[0] == 0:
                    from werkzeug.security import generate_password_hash
                    # admin/admin123
                    cursor.execute(
                        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                        ('admin', generate_password_hash('admin123'), 'admin')
                    )
                    # viewer/viewer123
                    cursor.execute(
                        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                        ('viewer', generate_password_hash('viewer123'), 'viewer')
                    )
                    conn.commit()
                    print("--- [DATABASE] Seeded default users (admin/viewer) ---")
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

    def validate_user(self, username, password):
        from werkzeug.security import check_password_hash
        query = "SELECT id, username, password_hash, role FROM users WHERE username = ?"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (username,))
                row = cursor.fetchone()
                if row and check_password_hash(row['password_hash'], password):
                    return {
                        "id": row['id'],
                        "username": row['username'],
                        "role": row['role']
                    }
        except Exception as e:
            print(f"Error validating user: {e}")
        return None

    def get_user_by_id(self, user_id):
        query = "SELECT id, username, role FROM users WHERE id = ?"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (user_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            print(f"Error fetching user by ID: {e}")
        return None

    def get_all_users(self):
        query = "SELECT id, username, role FROM users"
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching all users: {e}")
        return []

    def add_user(self, username, password, role='viewer'):
        from werkzeug.security import generate_password_hash
        query = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (username, generate_password_hash(password), role))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error adding user: {e}")
            return None

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
