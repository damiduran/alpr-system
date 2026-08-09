import os
import sqlite3
from flask import Flask, request, jsonify, session, send_file, redirect, url_for
from alpr_data.db_manager import DBManager
from PIL import Image

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_key_for_alpr_dashboard_123')

# Initialize DBManager
db = DBManager()

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

# --- AUTH API ---

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
        
    user = db.validate_user(username, password)
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({
            "message": "Login successful",
            "user": {
                "username": user['username'],
                "role": user['role']
            }
        })
    return jsonify({"error": "Invalid username or password"}), 401

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

# --- MEDIA SERVICE API ---

@app.route('/api/media/full/<file_id>', methods=['GET'])
@login_required
def serve_full_image(file_id):
    # Sanitize file_id to prevent directory traversal
    file_id = os.path.basename(file_id)
    image_path = f"assets/downloads/{file_id}.jpg"
    
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/jpeg')
    return jsonify({"error": "Image not found"}), 404

@app.route('/api/media/thumbnail/<file_id>', methods=['GET'])
@login_required
def serve_thumbnail(file_id):
    # Sanitize file_id
    file_id = os.path.basename(file_id)
    source_path = f"assets/downloads/{file_id}.jpg"
    
    if not os.path.exists(source_path):
        return jsonify({"error": "Source image not found"}), 404
        
    # Paths for thumbnails
    thumb_dir = "assets/downloads/thumbnails"
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
