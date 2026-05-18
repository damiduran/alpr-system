def simulate_search_response(results):
    if results:
        response = "🔍 Results:\n" + "\n".join([f"- {r['plate_number']} on {r['detection_date']} at {r['detection_time']}" for r in results])
        return response
    return "No sightings found."

if __name__ == "__main__":
    # Mock database results
    mock_results = [
        {
            'plate_number': 'ABC123',
            'detection_date': '2026-05-18',
            'detection_time': '12:30:45'
        },
        {
            'plate_number': 'ABC123',
            'detection_date': '2026-05-17',
            'detection_time': '09:15:00'
        }
    ]
    
    print("--- [TEST: Search Result Formatting] ---")
    output = simulate_search_response(mock_results)
    print(output)
    
    # Validation
    if "2026-05-18" in output and "12:30:45" in output:
        print("\n✅ SUCCESS: Search response includes both date and time.")
    else:
        print("\n❌ FAILURE: Search response formatting is incorrect.")
