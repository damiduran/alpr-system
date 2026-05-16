from .base import ALPRProvider
import requests
import os
import json

class RekorClient(ALPRProvider):
    """
    Perception Module: Handles communication with the Rekor Cloud API.
    """
    def __init__(self, secret_key=None, country='us'):
        self.secret_key = secret_key or os.getenv('REKOR_SECRET_KEY')
        self.country = country
        self.base_url = "https://api.openalpr.com/v3/recognize"

    def recognize_file(self, image_path):
        """
        Sends an image file to Rekor for recognition.
        """
        recognize_vehicle = 1
        if not self.secret_key:
            return {"error": "Rekor Secret Key is missing."}
        
        if not os.path.exists(image_path):
            return {"error": f"File not found: {image_path}"}

        params = {
            'secret_key': self.secret_key,
            'country': self.country,
            'recognize_vehicle': recognize_vehicle
        }

        try:
            with open(image_path, 'rb') as img_file:
                files = {'image': img_file}
                try:
                    response = requests.post(self.base_url, params=params, files=files)
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.RequestException as e:
                    return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def parse_best_result(self, api_response):
        """
        Extracts high-fidelity vehicle metadata from the Rekor CarCheck response.
        """
        if not api_response or api_response.get("error") or not api_response.get("results"):
            return None

        # Focus on the first detected plate result
        result = api_response["results"][0]
        vehicle = result.get("vehicle", {})

        # Helper to get top result name from Rekor's list-of-dicts format
        def get_top(field):
            data = vehicle.get(field)
            return data[0].get("name") if data and isinstance(data, list) else None

        return {
            "plate": result.get("plate"),
            "confidence": result.get("confidence"),
            "make": get_top("make"),
            "model": get_top("model"),
            "color": get_top("color"),
            "body_type": get_top("body_type"),
            "orientation": get_top("orientation"),
            "year": get_top("year"),
            "timestamp": api_response.get("epoch_time")
        }

if __name__ == "__main__":
    # Example usage (stubbed for now)
    client = RekorClient(secret_key="sk_DEMO")
    print("RekorClient initialized. Ready for API integration.")
