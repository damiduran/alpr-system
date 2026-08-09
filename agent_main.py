import os
import time
import csv
import threading
from queue import Queue
from datetime import datetime
from alpr_messaging.telegram_bot import TelegramBot
from alpr_perception.rekor_client import RekorClient
from alpr_data.db_manager import DBManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'data', 'downloads')

def load_env():
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v

class ALPRAgent:
    def __init__(self):
        load_env()
        self.bot = TelegramBot()
        self.rekor = RekorClient()
        self.db = DBManager()
        self.queue = Queue()
        self.running = True

    def poller(self):
        """Thread worker to continuously fetch new updates."""
        print("Starting polling thread...")
        while self.running:
            try:
                updates = self.bot.get_updates()
                for update in updates:
                    self.queue.put(update)
                    self.bot.offset = update['update_id'] + 1
                time.sleep(1)
            except Exception as e:
                print(f"Polling error: {e}")
                time.sleep(5)

    def worker(self):
        """Thread worker to process updates from the queue."""
        print("Starting worker thread...")
        while self.running:
            update = self.queue.get()
            try:
                self.process_update(update)
            except Exception as e:
                print(f"Processing error: {e}")
            self.queue.task_done()

    def run(self):
        # Start background threads
        threading.Thread(target=self.poller, daemon=True).start()
        threading.Thread(target=self.worker, daemon=True).start()
        
        # Keep the main thread alive
        while self.running:
            time.sleep(1)

    def process_update(self, update):
        message = update.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        
        if 'photo' in message:
            msg_date = datetime.fromtimestamp(message['date'])
            det_date = msg_date.strftime('%Y-%m-%d')
            det_time = msg_date.strftime('%H:%M:%S')

            photo = message['photo'][-1]
            file_id = photo['file_id']
            
            self.bot.send_message(chat_id, "📸 Image received. Analyzing vehicle...")
            
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            local_path = os.path.join(DOWNLOAD_DIR, f"{file_id}.jpg")
            self.bot.download_file(file_id, local_path)
            
            raw_response = self.rekor.recognize_file(local_path)
            result = self.rekor.parse_best_result(raw_response)
            
            if result:
                db_id = self.db.insert_detection(
                    plate_number=result['plate'],
                    confidence=result['confidence'],
                    vehicle_make=result['make'],
                    vehicle_model=result['model'],
                    vehicle_color=result['color'],
                    body_type=result.get('body_type'),
                    orientation=result.get('orientation'),
                    year=result.get('year'),
                    detection_date=det_date,
                    detection_time=det_time,
                    image_path=local_path,
                    raw_json=raw_response
                )
                if db_id:
                    self.bot.send_message(chat_id, f"✅ Detected: {result['plate']} (Saved)")
                else:
                    self.bot.send_message(chat_id, f"✅ Detected: {result['plate']} (⚠️ Failed to save to DB)")
            else:
                self.bot.send_message(chat_id, "❌ No plate detected.")

        elif 'text' in message:
            text = message['text']
            if text == '/start':
                self.bot.send_message(chat_id, "Hello! I am your ALPR Agent.")
            elif text.startswith('/search'):
                parts = text.split(' ', 1)
                if len(parts) > 1:
                    results = self.db.search_by_plate(parts[1])
                    if results:
                        response = "🔍 Search Results:\n"
                        for r in results:
                            response += f"- {r['plate_number']} on {r['detection_date']}\n"
                        self.bot.send_message(chat_id, response)
                    else:
                        self.bot.send_message(chat_id, "No sightings found.")
            elif text == '/export':
                detections = self.db.get_all_detections()
                if detections:
                    csv_path = 'detections_export.csv'
                    try:
                        with open(csv_path, 'w', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=detections[0].keys())
                            writer.writeheader()
                            writer.writerows(detections)
                        self.bot.send_message(chat_id, f"📊 Exporting {len(detections)} records...")
                        self.bot.send_document(chat_id, csv_path)
                    except Exception as e:
                        print(f"--- [ERROR] Export failed: {e} ---")
                        self.bot.send_message(chat_id, "❌ Export failed.")
                else:
                    self.bot.send_message(chat_id, "📭 No data to export.")


if __name__ == "__main__":
    agent = ALPRAgent()
    agent.run()
