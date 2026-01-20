import requests
import sys

filename = "Screenshot 2025-10-31 214320.png"
url = f"http://localhost:8000/results/{filename}"

try:
    print(f"Requesting {url}...")
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response JSON:")
        print(response.json())
    else:
        print("Error response:")
        print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
