import requests
import os
import time
from .base import ALPRProvider

class PlateRecognizerClient(ALPRProvider):
    """
    Perception Module: Handles communication with Plate Recognizer API.
    """
    def __init__(self, api_token=None, regions=None):
        self.api_token = api_token or os.getenv('PLATE_RECOGNIZER_TOKEN')
        self.regions = regions or os.getenv('PLATE_RECOGNIZER_REGIONS', 'us')
        self.base_url = "https://api.platerecognizer.com/v1/plate-reader/"
        self.last_call_time = 0

    def recognize_file(self, image_path):
        """
        Sends an image file to Plate Recognizer for recognition.
        Includes rate limiting to respect 1 call/sec limit.
        """
        # Rate Limiting: Ensure at least 1 second between calls
        elapsed = time.time() - self.last_call_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        if not self.api_token:
            return {"error": "Plate Recognizer Token is missing."}
        
        if not os.path.exists(image_path):
            return {"error": f"File not found: {image_path}"}

        headers = {'Authorization': f'Token {self.api_token}'}
        data = {
            'regions': self.regions,
            'mmc': 'true'  # Attempt to get make, model, color
        }

        try:
            with open(image_path, 'rb') as fp:
                files = {'upload': fp}
                response = requests.post(self.base_url, headers=headers, data=data, files=files)
                self.last_call_time = time.time()
                response.raise_for_status()
                return response.json()
        except requests.exceptions.RequestException as e:
            self.last_call_time = time.time() # Still update to be safe
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def parse_best_result(self, api_response):
        """
        Standardizes the Plate Recognizer response.
        """
        if not api_response or api_response.get("error") or not api_response.get("results"):
            return None

        # Take the top result
        result = api_response["results"][0]
        vehicle = result.get("vehicle", {})
        
        # In Plate Recognizer, MMC data is often in the 'model_make', 'color', etc. 
        # but it depends on the subscription. We extract what we can.
        # Note: Plate Recognizer nested MMC data inside 'results[0]' if enabled.
        # According to docs, MMC data is at the same level as 'plate' in 'results[0]' 
        # or inside 'vehicle'? Let's re-verify the docs from my previous search.
        # Docs said: vehicle contains type and box.
        # Actually, MMC is often results[0]['model_make'], results[0]['color'] etc.
        
        return {
            "plate": result.get("plate", "").upper(),
            "confidence": result.get("score", 0) * 100, # Convert to percentage
            "make": result.get("model_make", [{}])[0].get("make") if result.get("model_make") else None,
            "model": result.get("model_make", [{}])[0].get("model") if result.get("model_make") else None,
            "color": result.get("color", [{}])[0].get("color") if result.get("color") else None,
            "body_type": vehicle.get("type"),
            "orientation": None, # Not provided by basic Plate Recognizer
            "year": None,        # Not provided by basic Plate Recognizer
            "timestamp": api_response.get("timestamp")
        }
