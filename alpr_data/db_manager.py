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
        authorized_emails_schema = """
        CREATE TABLE IF NOT EXISTS authorized_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('viewer', 'manager', 'admin')),
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            with self._get_connection() as conn:
                conn.execute(detections_schema)
                conn.execute(authorized_emails_schema)
                conn.commit()
                self._seed_authorized_emails_from_env(conn)
        except Exception as e:
            print(f"Error initializing tables: {e}")

    def _seed_authorized_emails_from_env(self, conn):
        """Seeds initial admin, manager, and viewer emails from environment variables if not already present."""
        cursor = conn.cursor()
        env_mappings = [
            ('admin', os.getenv('ALLOWED_ADMIN_EMAILS', os.getenv('ALLOWED_EMAILS', ''))),
            ('manager', os.getenv('ALLOWED_MANAGER_EMAILS', '')),
            ('viewer', os.getenv('ALLOWED_VIEWER_EMAILS', '')),
        ]
        for role, raw_str in env_mappings:
            for email in [e.strip().lower() for e in raw_str.split(',') if e.strip()]:
                cursor.execute(
                    "INSERT OR IGNORE INTO authorized_emails (email, role) VALUES (?, ?)",
                    (email, role)
                )
        conn.commit()

    def get_email_role(self, email: str):
        normalized = (email or '').strip().lower()
        if not normalized:
            return None
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role FROM authorized_emails WHERE email = ?", (normalized,))
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            print(f"Error fetching email role: {e}")
        return None

    def list_authorized_emails(self):
        query = """
        SELECT id, email, role, added_at
        FROM authorized_emails
        ORDER BY
            CASE role
                WHEN 'admin' THEN 1
                WHEN 'manager' THEN 2
                WHEN 'viewer' THEN 3
                ELSE 4
            END,
            email ASC
        """
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query)
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            print(f"Error listing authorized emails: {e}")
            return []

    def upsert_authorized_email(self, email: str, role: str) -> bool:
        normalized = (email or '').strip().lower()
        role_norm = (role or '').strip().lower()
        if not normalized or '@' not in normalized or role_norm not in ('viewer', 'manager', 'admin'):
            return False
        query = """
        INSERT INTO authorized_emails (email, role)
        VALUES (?, ?)
        ON CONFLICT(email) DO UPDATE SET role = excluded.role
        """
        try:
            with self._get_connection() as conn:
                conn.execute(query, (normalized, role_norm))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error upserting authorized email: {e}")
            return False

    def remove_authorized_email(self, email: str) -> bool:
        normalized = (email or '').strip().lower()
        if not normalized:
            return False
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM authorized_emails WHERE email = ?", (normalized,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error removing authorized email: {e}")
            return False

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

    def delete_detections(self, ids):
        if not ids:
            return False
        try:
            # Cast all ids to integers for safety
            sanitized_ids = [int(i) for i in ids]
            placeholders = ','.join('?' for _ in sanitized_ids)
            query = f"DELETE FROM detections WHERE id IN ({placeholders})"
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, sanitized_ids)
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting detections: {e}")
            return False

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
