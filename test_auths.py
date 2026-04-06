import requests
import json

with open('data/accounts.json', 'r') as f:
    accs = json.load(f)
token = accs[0]['token']
print(f"Token: {token[:20]}...")

resp = requests.get(
    "https://chat.qwen.ai/api/v1/auths/",
    headers={"Authorization": f"Bearer {token}"}
)
print(f"Status: {resp.status_code}")
print(f"Headers: {resp.headers}")
print(f"Body: {resp.text}")
