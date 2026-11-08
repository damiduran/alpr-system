import os
import sqlite3
import requests
from flask import Flask, request, jsonify, session, send_file, redirect, url_for
from alpr_data.db_manager import DBManager
from PIL import Image

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_key_for_alpr_dashboard_123')

# Initialize DBManager
db = DBManager()

# Define absolute paths to ensure consistent file resolution across modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'data', 'downloads')


def get_google_client_id() -> str:
    return os.getenv('GOOGLE_CLIENT_ID', '').strip()


def get_allowed_role_for_email(email: str):
    """
    Determines the dashboard role ('admin' or 'viewer') for a verified Google email.
    Checks ALLOWED_ADMIN_EMAILS (falling back to ALLOWED_EMAILS) for admin privileges,
    and ALLOWED_VIEWER_EMAILS for viewer-only privileges.
    """
    normalized = (email or '').strip().lower()
    if not normalized:
        return None

    admin_raw = os.getenv('ALLOWED_ADMIN_EMAILS', os.getenv('ALLOWED_EMAILS', ''))
    admin_emails = [e.strip().lower() for e in admin_raw.split(',') if e.strip()]
    if normalized in admin_emails:
        return 'admin'

    viewer_raw = os.getenv('ALLOWED_VIEWER_EMAILS', '')
    viewer_emails = [e.strip().lower() for e in viewer_raw.split(',') if e.strip()]
    if normalized in viewer_emails:
        return 'viewer'

    return None


def verify_google_id_token(token: str, client_id: str) -> dict:
    """
    Verifies a Google Identity Services ID token via Google's tokeninfo endpoint.
    Raises ValueError on invalid token/audience, or RuntimeError on network failure.
    """
    try:
        res = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
            timeout=10.0
        )
    except Exception as e:
        raise RuntimeError(f"Failed to reach Google token verification service: {e}")

    if res.status_code != 200:
        raise ValueError("Invalid Google credential token.")

    token_info = res.json()
    if token_info.get("aud") != client_id:
        raise ValueError("Token audience mismatch.")

    if token_info.get("email_verified") not in ("true", True):
        raise ValueError("Google account email is not verified.")

    return token_info

# Helper decorator for login check
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function

# Helper decorator for admin check
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        if session.get('role') != 'admin':
            return jsonify({"error": "Forbidden. Admin access required."}), 403
        return f(*args, **kwargs)
    return decorated_function

# Serve SPA
@app.route('/')
def index():
    # If the user is not logged in, we serve the SPA which defaults to the login view.
    # The client-side JS handles checking /api/auth/me to decide what screen to display.
    return send_file(os.path.join(app.static_folder, 'index.html'))

# --- AUTH API (Google OAuth 2.0) ---

@app.route('/api/auth/config', methods=['GET'])
def auth_config():
    return jsonify({
        "google_client_id": get_google_client_id()
    })

@app.route('/api/auth/google', methods=['POST'])
def auth_google():
    data = request.get_json() or {}
    token = (data.get('credential') or '').strip()
    if not token:
        return jsonify({"error": "Google credential token is required."}), 400

    client_id = get_google_client_id()
    if not client_id:
        return jsonify({
            "error": "Google Authentication is not configured on this server (missing GOOGLE_CLIENT_ID)."
        }), 500

    try:
        token_info = verify_google_id_token(token, client_id)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    email = token_info.get("email", "").strip().lower()
    role = get_allowed_role_for_email(email)
    if not role:
        return jsonify({"error": f"Unauthorized email address: {email}"}), 403

    session['user_id'] = email
    session['username'] = email
    session['role'] = role
    return jsonify({
        "message": "Login successful",
        "user": {
            "username": email,
            "role": role
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.clear()
    return jsonify({"message": "Logout successful"})

@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    if 'user_id' in session:
        return jsonify({
            "authenticated": True,
            "user": {
                "username": session['username'],
                "role": session['role']
            }
        })
    return jsonify({"authenticated": False}), 200

# --- DETECTIONS API ---

@app.route('/api/detections', methods=['GET'])
@login_required
def get_detections():
    # Fetch filter options from query parameters
    plate_filter = request.args.get('plate', '').strip()
    
    # Fetch all detections or filter by plate
    if plate_filter:
        raw_detections = db.search_by_plate(plate_filter)
    else:
        raw_detections = db.get_all_detections()
        
    # Optional column filtering requested by user
    selected_columns = request.args.get('columns', '').strip()
    if selected_columns:
        columns_list = [col.strip() for col in selected_columns.split(',') if col.strip()]
    else:
        columns_list = []
        
    processed = []
    for item in raw_detections:
        # Resolve vehicle photo filename
        image_path = item.get('image_path', '')
        file_id = None
        if image_path:
            file_id = os.path.basename(image_path).replace('.jpg', '')
            
        # Build base record
        record = {
            "id": item.get('id'),
            "plate_number": item.get('plate_number'),
            "confidence": item.get('confidence'),
            "vehicle_make": item.get('vehicle_make'),
            "vehicle_model": item.get('vehicle_model'),
            "vehicle_color": item.get('vehicle_color'),
            "body_type": item.get('body_type'),
            "orientation": item.get('orientation'),
            "year": item.get('year'),
            "detection_date": item.get('detection_date'),
            "detection_time": item.get('detection_time'),
            "file_id": file_id
        }
        
        # If columns_list is specified, filter keys (always keep id and file_id for table UI actions)
        if columns_list:
            filtered_record = {"id": record["id"], "file_id": record["file_id"]}
            for col in columns_list:
                if col in record:
                    filtered_record[col] = record[col]
            processed.append(filtered_record)
        else:
            processed.append(record)
            
    return jsonify(processed)

@app.route('/api/detections/delete', methods=['POST'])
@admin_required
def delete_detections():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({"error": "No IDs provided"}), 400
    
    success = db.delete_detections(ids)
    if success:
        return jsonify({"message": f"Successfully deleted {len(ids)} records"})
    return jsonify({"error": "Failed to delete records"}), 500

@app.route('/api/detections/export', methods=['GET'])
@login_required
def export_detections():
    import csv
    import io
    from flask import Response
    
    ids_filter = request.args.get('ids', '').strip()
    plate_filter = request.args.get('plate', '').strip()
    
    if ids_filter:
        try:
            id_list = [int(i.strip()) for i in ids_filter.split(',') if i.strip()]
            all_detections = db.get_all_detections()
            detections = [d for d in all_detections if d.get('id') in id_list]
        except Exception as e:
            print(f"Error parsing IDs for export: {e}")
            detections = []
    elif plate_filter:
        detections = db.search_by_plate(plate_filter)
    else:
        detections = db.get_all_detections()
        
    output = io.StringIO()
    if not detections:
        # Empty export with headers
        headers = ["id", "plate_number", "confidence", "vehicle_make", "vehicle_model", "vehicle_color", "body_type", "orientation", "year", "detection_date", "detection_time", "image_path"]
        writer = csv.writer(output)
        writer.writerow(headers)
    else:
        writer = csv.DictWriter(output, fieldnames=detections[0].keys())
        writer.writeheader()
        writer.writerows(detections)
        
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers["Content-Disposition"] = "attachment; filename=alpr_detections_export.csv"
    return response

# --- MEDIA SERVICE API ---

@app.route('/api/media/full/<file_id>', methods=['GET'])
@login_required
def serve_full_image(file_id):
    # Sanitize file_id to prevent directory traversal
    file_id = os.path.basename(file_id)
    image_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.jpg")
    
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/jpeg')
    return jsonify({"error": "Image not found"}), 404

@app.route('/api/media/thumbnail/<file_id>', methods=['GET'])
@login_required
def serve_thumbnail(file_id):
    # Sanitize file_id
    file_id = os.path.basename(file_id)
    source_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.jpg")
    
    if not os.path.exists(source_path):
        return jsonify({"error": "Source image not found"}), 404
        
    # Paths for thumbnails
    thumb_dir = os.path.join(DOWNLOAD_DIR, 'thumbnails')
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_path = os.path.join(thumb_dir, f"{file_id}.jpg")
    
    # Generate thumbnail on-the-fly if it does not exist
    if not os.path.exists(thumb_path):
        try:
            with Image.open(source_path) as img:
                # Resize keeping aspect ratio or crop-to-square (we will crop to square 150x150 for clean layout)
                width, height = img.size
                min_dim = min(width, height)
                
                # Crop to square
                left = (width - min_dim) / 2
                top = (height - min_dim) / 2
                right = (width + min_dim) / 2
                bottom = (height + min_dim) / 2
                
                img_cropped = img.crop((left, top, right, bottom))
                img_cropped.thumbnail((150, 150), Image.Resampling.LANCZOS)
                img_cropped.save(thumb_path, "JPEG", quality=85)
        except Exception as e:
            # Fallback to source image if thumbnailing fails
            print(f"Error creating thumbnail: {e}")
            return send_file(source_path, mimetype='image/jpeg')
            
    return send_file(thumb_path, mimetype='image/jpeg')

if __name__ == '__main__':
    # Start app on port 8080
    app.run(host='0.0.0.0', port=8080, debug=True)
