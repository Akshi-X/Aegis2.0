import requests
import json
import time

API_URL = "http://localhost:8000/agent/task"

payload = {
    "agent_id": 1,  # Treasury Agent
    "task": "Settle monthly invoice #INV-492 for ABC Technologies cloud hosting services. Transfer ₹2500 to ABC Technologies.",
    "context": [
        {
            "source": "invoice_processor_v2",
            "confidence": 0.98,
            "raw_prompt": "Please pay the attached ABC Technologies invoice for $2500."
        }
    ]
}

print("==================================================")
print("🚀 DEMO 1: BENIGN TRANSACTION (EXECUTE)")
print("==================================================")
print(f"Agent: Treasury Agent (ID: 1)")
print(f"Task: {payload['task']}")
print("--------------------------------------------------")
print("Sending Natural Language Task to Agent...")

response = requests.post(API_URL, json=payload)

if response.status_code in (200, 201):
    data = response.json()
    print(f"✅ Success! Action proposed with ID: {data['proposal']['action_id']}")
    print(f"   Parser used: {data['parser']}")
    print("\n👉 Now open your dashboard (http://localhost:5173/actions) to watch it get approved!")
else:
    print(f"❌ Failed: {response.text}")
