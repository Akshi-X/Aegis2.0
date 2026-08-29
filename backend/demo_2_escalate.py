import requests
import json
import time

API_URL = "http://localhost:8000/actions"

payload = {
    "agent_id": 3,  # Marketing Agent
    "action_type": "TRANSFER",
    "amount": 8500.00,
    "currency": "INR",
    "recipient": "Vegas Events LLC",  # Unknown vendor
    "purpose": "Purchase 10 VIP tickets and a massive booth space for the DefCon Cyber Security Conference in Las Vegas.",
    "provenance": {
        "source": "slack_bot_command",
        "confidence": 0.65,
        "raw_prompt": "Hey Marketing bot, buy those Vegas tickets for the team."
    }
}

print("==================================================")
print("⚠️ DEMO 2: BORDERLINE TRANSACTION (ESCALATE)")
print("==================================================")
print(f"Agent: Marketing Agent (ID: 3)")
print(f"Objective: Fund digital advertising campaigns.")
print(f"Recipient: {payload['recipient']} (Unknown Vendor)")
print(f"Amount: ₹{payload['amount']}")
print(f"Purpose: {payload['purpose']}")
print("--------------------------------------------------")
print("Sending Action Proposal to AEGIS-X Orchestrator...")

response = requests.post(API_URL, json=payload)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Success! Action created with ID: {data['action_id']}")
    print("\n👉 Now open your dashboard (http://localhost:5173/actions).")
    print("Watch the Gemini AI flag 'Intent Drift' because buying Vegas tickets does NOT align with digital advertising!")
else:
    print(f"❌ Failed: {response.text}")
