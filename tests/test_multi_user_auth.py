import os

def parse_auth_users(auth_string):
    # This mimics the logic now in ALPRAgent.__init__
    return [int(uid.strip()) for uid in auth_string.split(",") if uid.strip()]

if __name__ == "__main__":
    # Simulate a .env line with multiple users
    env_string = "8685332424, 123456789, 555666777"
    
    authorized_list = parse_auth_users(env_string)
    print(f"Parsed Authorized List: {authorized_list}")
    
    # Test cases
    test_ids = [8685332424, 123456789, 999999999]
    
    for uid in test_ids:
        status = "✅ ALLOWED" if uid in authorized_list else "❌ BLOCKED"
        print(f"User {uid}: {status}")

    # Validation
    if 8685332424 in authorized_list and 123456789 in authorized_list and 999999999 not in authorized_list:
        print("\n✅ SUCCESS: Multi-user parsing and validation works correctly.")
    else:
        print("\n❌ FAILURE: Multi-user logic error.")
