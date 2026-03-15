import requests
import json

payload = {
    "threat_level": 85,
    "targets": 1,
    "labels": ["gun"],
    "motion_score": 1200,
    "zones": ["CENTER"],
    "distances": [2.5]
}

response = requests.post("http://localhost:3000/analyze", json=payload)
print("Response Status Code:", response.status_code)
print("Response Body:", response.text)
