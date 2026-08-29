import requests
import json
import time

API_URL = "http://localhost:8000/actions"

payload = {
    "agent_id": 1,  # Treasury Agent
    "action_type": "TRANSFER",
    "amount": 2500.00,
    "currency": "INR",
    "recipient": "ABC Technologies",  # Known trusted vendor
    "purpose": "Settle monthly invoice #INV-492 for AWS cloud hosting services.",
    "provenance": {
        "source": "invoice_processor_v2",
        "confidence": 0.98,
        "raw_prompt": "Please pay the attached AWS invoice for $2500 to ABC Technologies."
    }
}

print("==================================================")
print("🚀 DEMO 1: BENIGN TRANSACTION (EXECUTE)")
print("==================================================")
print(f"Agent: Treasury Agent (ID: 1)")
print(f"Recipient: {payload['recipient']} (Known Vendor)")
print(f"Amount: ₹{payload['amount']}")
print(f"Purpose: {payload['purpose']}")
print("--------------------------------------------------")
print("Sending Action Proposal to AEGIS-X Orchestrator...")

response = requests.post(API_URL, json=payload)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Success! Action created with ID: {data['action_id']}")
    print("\n👉 Now open your dashboard (http://localhost:5173/actions) to watch it get approved!")
else:
    print(f"❌ Failed: {response.text}")
