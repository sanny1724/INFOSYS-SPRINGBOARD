import requests
import time
import os

# Create a dummy image
with open("test_image.jpg", "wb") as f:
    f.write(os.urandom(1024))

url = "http://localhost:8000/upload"
files = {'file': open('test_image.jpg', 'rb')}

print("Uploading...")
response = requests.post(url, files=files)
print(f"Upload status: {response.status_code}")
print(f"Upload response: {response.json()}")

if response.status_code == 200:
    filename = "test_image.jpg"
    print("Polling for results...")
    for i in range(10):
        res = requests.get(f"http://localhost:8000/results/{filename}")
        data = res.json()
        print(f"Poll {i}: {data}")
        if data.get("status") == "completed":
            print("Processing completed!")
            break
        time.sleep(1)
