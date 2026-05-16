import os
from main import ALPRAgent

# Mock update dictionary for /export
mock_update = {
    'message': {
        'chat': {'id': 8685332424},
        'text': '/export'
    }
}

agent = ALPRAgent()
print("Starting manual process_update for /export...")
try:
    agent.process_update(mock_update)
    print("Process complete.")
except Exception as e:
    print(f"Exception during manual process: {e}")
