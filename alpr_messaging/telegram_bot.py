import requests
import time
import os

class TelegramBot:
    """
    Messaging Module: A simple Telegram bot using polling via requests.
    This acts as the agent's 'Ears' and 'Eyes'.
    """
    def __init__(self, token=None):
        self.token = token or os.getenv('TELEGRAM_TOKEN')
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.offset = 0

    def get_updates(self):
        url = f"{self.base_url}/getUpdates"
        params = {'offset': self.offset, 'timeout': 30}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return data.get("result", [])
            return []
        except Exception as e:
            print(f"Error getting updates: {e}")
            return []

    def send_message(self, chat_id, text):
        url = f"{self.base_url}/sendMessage"
        payload = {'chat_id': chat_id, 'text': text}
        requests.post(url, json=payload)

    def send_document(self, chat_id, document_path):
        url = f"{self.base_url}/sendDocument"
        try:
            with open(document_path, 'rb') as doc:
                files = {'document': doc}
                data = {'chat_id': chat_id}
                res = requests.post(url, data=data, files=files)
                print(f"Telegram sendDocument response: {res.text}")
                return res.json()
        except Exception as e:
            print(f"send_document exception: {e}")
            return None

    def download_file(self, file_id, destination):
        # 1. Get file path
        url = f"{self.base_url}/getFile"
        res = requests.get(url, params={'file_id': file_id}).json()
        if not res.get("ok"):
            return None
        
        file_path = res["result"]["file_path"]
        # 2. Download the file
        download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        file_res = requests.get(download_url)
        
        with open(destination, 'wb') as f:
            f.write(file_res.content)
        return destination
