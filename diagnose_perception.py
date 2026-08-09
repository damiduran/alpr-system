import os
import json
from alpr_perception.factory import get_alpr_provider

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'data', 'downloads')

def load_env():
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line:
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        k, v = parts
                        os.environ[k] = v

def diagnose():
    load_env()
    client = get_alpr_provider()
    print(f"Using Provider: {type(client).__name__}")
    
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    downloads = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.jpg')]
    
    for img in downloads:
        path = os.path.join(DOWNLOAD_DIR, img)
        print(f"\n--- Diagnosing {img} ---")
        raw_response = client.recognize_file(path)
        
        # Print full response for inspection
        print(json.dumps(raw_response, indent=2))
        
        # Check parser
        result = client.parse_best_result(raw_response)
        print(f"Parsed Result: {result}")

if __name__ == "__main__":
    diagnose()
