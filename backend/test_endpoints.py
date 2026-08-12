import requests
import json

# Test patient registration
print("Testing patient registration...")
patient_data = {
    "name": "Test Child",
    "age": 5,
    "date_of_birth": "2020-01-01",
    "language": "en",
    "gender": "other",
    "diagnosis": "General Speech",
    "therapist_name": None,
    "parent_name": "Test Parent",
    "parent_contact": "1234567890",
    "email": "test@example.com"
}

try:
    response = requests.post("http://127.0.0.1:8002/patients/", json=patient_data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        patient_id = response.json().get("id")
        print(f"✅ Patient registration successful! ID: {patient_id}")
        
        # Verify the data was stored correctly
        patient_data_response = response.json()
        assert patient_data_response["parent_name"] == "Test Parent", "parent_name not stored correctly"
        assert patient_data_response["date_of_birth"] == "2020-01-01", "date_of_birth not stored correctly"
        assert patient_data_response["email"] == "test@example.com", "email not stored correctly"
        assert patient_data_response["therapist_name"] is None, "therapist_name should be null"
        print("✅ All patient fields verified correctly")
    else:
        print(f"❌ Patient registration failed")
except Exception as e:
    print(f"❌ Error testing patient registration: {e}")

print("\n" + "="*50 + "\n")

# Test speech analysis endpoint
print("Testing speech analysis endpoints...")

try:
    # Test random word endpoint
    response = requests.get("http://127.0.0.1:8002/assessment/words/random")
    print(f"Random Word Status Code: {response.status_code}")
    if response.status_code == 200:
        word_data = response.json()
        print(f"✅ Random word endpoint working: {word_data.get('word', 'N/A')}")
    else:
        print(f"❌ Random word endpoint failed")
except Exception as e:
    print(f"❌ Error testing random word endpoint: {e}")

print("\nTesting complete!")
