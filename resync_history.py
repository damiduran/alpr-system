import os
import json
from alpr_perception.rekor_client import RekorClient
from alpr_data.db_manager import DBManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'data', 'downloads')

def resync():
    client = RekorClient()
    db = DBManager()
    
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    downloads = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.jpg')]
    
    for img in downloads:
        path = os.path.join(DOWNLOAD_DIR, img)
        print(f"\n--- Resyncing {img} ---")
        
        raw_response = client.recognize_file(path)
        result = client.parse_best_result(raw_response)
        
        if result:
            db.insert_detection(
                plate_number=result['plate'],
                confidence=result['confidence'],
                vehicle_make=result['make'],
                vehicle_model=result['model'],
                vehicle_color=result['color'],
                body_type=result.get('body_type'),
                orientation=result.get('orientation'),
                year=result.get('year'),
                image_path=path,
                raw_json=raw_response
            )
            print(f"Successfully added to DB: {result['plate']}")
        else:
            print("Failed to parse result.")

if __name__ == "__main__":
    resync()
