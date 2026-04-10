import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("API Server Test Script")
print("=" * 60)

# Test 1: GET /products
print("\n[TEST 1] GET /products")
print("-" * 60)
try:
    response = requests.get(f"{BASE_URL}/products", timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    try:
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
    except json.JSONDecodeError:
        print(f"Response Body (raw): {response.text}")
except requests.exceptions.ConnectionError as e:
    print(f"ERROR: Connection failed - {str(e)}")
    print("The API server may not be running at http://127.0.0.1:8000")
except requests.exceptions.Timeout:
    print("ERROR: Request timed out")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")

# Test 2: POST /login
print("\n[TEST 2] POST /login")
print("-" * 60)
login_data = {
    "username": "root",
    "password": "P@ssw0rd"
}
print(f"Payload: {json.dumps(login_data, indent=2)}")
try:
    response = requests.post(
        f"{BASE_URL}/login",
        json=login_data,
        timeout=5
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    try:
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
    except json.JSONDecodeError:
        print(f"Response Body (raw): {response.text}")
except requests.exceptions.ConnectionError as e:
    print(f"ERROR: Connection failed - {str(e)}")
    print("The API server may not be running at http://127.0.0.1:8000")
except requests.exceptions.Timeout:
    print("ERROR: Request timed out")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
