import pytz
from datetime import datetime

def test_conversion(unix_timestamp):
    # This matches the logic in main.py
    utc_date = datetime.fromtimestamp(unix_timestamp, tz=pytz.UTC)
    aest_date = utc_date.astimezone(pytz.timezone('Australia/Sydney'))
    
    print(f"Unix Timestamp: {unix_timestamp}")
    print(f"UTC Time:       {utc_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"AEST Time:      {aest_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    return aest_date

if __name__ == "__main__":
    # Current time
    now_ts = int(datetime.now().timestamp())
    print("--- [TEST 1: Current Time] ---")
    test_conversion(now_ts)
    
    # A known UTC time (e.g., 2026-05-18 00:00:00 UTC)
    known_ts = 1779148800 # 2026-05-18 00:00:00 UTC
    print("\n--- [TEST 2: Known UTC Midnight] ---")
    aest = test_conversion(known_ts)
    
    # Check if AEST is +10 or +11 (Sydney is +10 in May)
    offset = aest.utcoffset().total_seconds() / 3600
    print(f"\nOffset from UTC: {offset} hours")
    
    if offset == 10.0:
        print("✅ SUCCESS: Correct AEST offset (+10) detected for May.")
    elif offset == 11.0:
        print("⚠️ NOTE: AEDT offset (+11) detected. (Expected if in Daylight Saving period)")
    else:
        print("❌ FAILURE: Unexpected offset.")
