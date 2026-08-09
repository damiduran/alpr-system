import os
import time
import csv
import threading
import pytz
from queue import Queue
from datetime import datetime
from alpr_messaging.telegram_bot import TelegramBot
from alpr_perception.factory import get_alpr_provider
from alpr_data.db_manager import DBManager

def run_web_server(port):
    print(f"--- [SYSTEM] Starting ALPR Web Dashboard Server on port {port} ---")
    from alpr_web.app import app as web_app
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def load_env():
    print("--- [SYSTEM] Initializing environment... ---")
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v
    else:
        print("--- [SYSTEM] No .env file found. Using platform environment variables. ---")

class ALPRAgent:
    def __init__(self):
        print("--- [AGENT] Creating ALPR Agent instance... ---")
        load_env()
        
        # Load authorized users from .env
        auth_users_str = os.getenv("AUTHORIZED_USERS", "")
        self.authorized_users = [int(uid.strip()) for uid in auth_users_str.split(",") if uid.strip()]
        if self.authorized_users:
            print(f"--- [SECURITY] Authorization active. Allowed IDs: {self.authorized_users} ---")
        else:
            print("--- [SECURITY] WARNING: No AUTHORIZED_USERS set. Bot is public! ---")

        # Note: self.bot and self.perception are initialized in run() to catch FATAL errors
        self.db = DBManager()
        self.queue = Queue()
        self.running = True

    def poller(self):
        print("--- [THREADS] Polling thread active. ---")
        while self.running:
            try:
                updates = self.bot.get_updates()
                for update in updates:
                    self.queue.put(update)
                    self.bot.offset = update['update_id'] + 1
            except Exception as e:
                print(f"--- [ERROR] Polling error: {e} ---")
                time.sleep(4) # Extra wait on error
            
            # Consistent heartbeat delay
            time.sleep(1)

    def worker(self):
        print("--- [THREADS] Worker thread active. ---")
        while self.running:
            update = self.queue.get()
            try:
                self.process_update(update)
            except Exception as e:
                print(f"--- [ERROR] Processing error: {e} ---")
            self.queue.task_done()

    def run(self):
        print("--- [STARTUP] ALPR Agent initiating... ---")
        try:
            # Test initialization to catch config errors early
            self.bot = TelegramBot()
            self.perception = get_alpr_provider()
            print("--- [STARTUP] Bot and Perception Engine ready. ---")
        except Exception as e:
            print(f"--- [FATAL] Agent configuration error: {e} ---")
            self.running = False
            return

        # Start Web Dashboard Server (which handles Railway health checks on /)
        port = int(os.getenv("PORT", 8080))
        threading.Thread(target=run_web_server, args=(port,), daemon=True).start()

        print("--- [STARTUP] Spinning up background threads... ---")
        threading.Thread(target=self.poller, daemon=True).start()
        threading.Thread(target=self.worker, daemon=True).start()
        
        print("--- [STARTUP] Agent is now fully operational and monitoring. ---")
        while self.running:
            time.sleep(1)

    def process_update(self, update):
        message = update.get('message', {})
        chat_id = message.get('chat', {}).get('id')

        # Security: Check if user is authorized
        if self.authorized_users and chat_id not in self.authorized_users:
            print(f"--- [SECURITY] Unauthorized access attempt from ID: {chat_id} ---")
            return

        if 'photo' in message:
            # Convert UTC timestamp from Telegram to AEST (Australia/Sydney)
            utc_date = datetime.fromtimestamp(message['date'], tz=pytz.UTC)
            aest_date = utc_date.astimezone(pytz.timezone('Australia/Sydney'))
            det_date = aest_date.strftime('%Y-%m-%d')
            det_time = aest_date.strftime('%H:%M:%S')
            photo = message['photo'][-1]
            file_id = photo['file_id']
            self.bot.send_message(chat_id, "📸 Image received. Analyzing vehicle...")
            os.makedirs('assets/downloads', exist_ok=True)
            local_path = f"assets/downloads/{file_id}.jpg"
            self.bot.download_file(file_id, local_path)
            raw_response = self.perception.recognize_file(local_path)
            result = self.perception.parse_best_result(raw_response)
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
                        response = "🔍 Results:\n" + "\n".join([f"- {r['plate_number']} on {r['detection_date']} at {r['detection_time']}" for r in results])
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
                        self.bot.send_message(chat_id, "❌ Export failed due to internal error.")
                else:
                    self.bot.send_message(chat_id, "📭 No detection data available to export.")

if __name__ == "__main__":
    agent = ALPRAgent()
    agent.run()
