class MockAgent:
    def __init__(self, authorized_users):
        self.authorized_users = authorized_users
        self.processed = []

    def process_update(self, update):
        message = update.get('message', {})
        chat_id = message.get('chat', {}).get('id')

        # Matches the logic in main.py
        if self.authorized_users and chat_id not in self.authorized_users:
            print(f"--- [SECURITY] Blocked: {chat_id} ---")
            return

        print(f"--- [SECURITY] Allowed: {chat_id} ---")
        self.processed.append(chat_id)

if __name__ == "__main__":
    auth_list = [8685332424]
    agent = MockAgent(auth_list)
    
    print("--- [TEST 1: Authorized User] ---")
    agent.process_update({'message': {'chat': {'id': 8685332424}}})
    
    print("\n--- [TEST 2: Unauthorized User] ---")
    agent.process_update({'message': {'chat': {'id': 1234567890}}})
    
    # Validation
    if 8685332424 in agent.processed and 1234567890 not in agent.processed:
        print("\n✅ SUCCESS: Authorization logic correctly filters users.")
    else:
        print("\n❌ FAILURE: Authorization logic failed.")
