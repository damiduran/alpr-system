# Autonomous ALPR Agent (V2.0)

An autonomous agent that monitors a Telegram channel, performs License Plate Recognition (LPR), and maintains a searchable vehicle sighting database.

## 🚀 Overview
This agent is built using a **Multi-Threaded Worker Pattern**. It listens for vehicle images via the Telegram Bot API, processes them through a pluggable perception engine (Rekor or Plate Recognizer), and stores high-fidelity vehicle metadata in a local SQLite database.

## 🧠 Key Features
- **Multi-Provider Support**: Seamlessly switch between Rekor and Plate Recognizer via configuration.
- **Autonomous Polling**: Real-time monitoring of Telegram messages.
- **Defensive Rate Limiting**: Intelligent API cooldown management to respect provider tiers.
- **Search & Export**: Query the history via Telegram commands (`/search`) or export data to CSV.

## 🛠 Architecture
- **Messaging**: `alpr_messaging` (Telegram integration)
- **Perception**: `alpr_perception` (AI/ML Vision clients)
- **Data**: `alpr_data` (SQLite persistence layer)

## 📦 Setup
1. Clone the repository.
2. Create a `.env` file based on the provided template:
   ```env
   TELEGRAM_TOKEN=your_token
   ALPR_PROVIDER=platerecognizer
   PLATE_RECOGNIZER_TOKEN=your_key
   ```
3. Install dependencies:
   ```bash
   pip install requests
   ```
4. Run the agent:
   ```bash
   python3 main.py
   ```

## 📝 License
MIT
