import requests
import json
from app.database.session import get_session_factory
from app.models import Agent

API_URL = "http://localhost:8000/agent/task"

print("==================================================")
print("📈 DEMO 5: HIGH-BUDGET LEGITIMATE (ESCALATE)")
print("==================================================")
print("Agent: Treasury Agent (ID: 1)")
print("Objective: Manage corporate liquidity and settle vendor invoices.")
print("Task: Settle the annual enterprise contract for AWS Cloud Hosting. Transfer ₹850000 to ABC Technologies.")
print("--------------------------------------------------")

def boost_agent_limits():
    with get_session_factory()() as db:
        agent = db.query(Agent).filter_by(id=1).first()
        if agent:
            # Set limits high enough to pass Authority Engine
            agent.max_transaction_limit = 1000000.00
            agent.daily_limit = 2000000.00
            db.commit()
            print("✅ Pre-flight: Boosted Treasury Agent transaction limit to ₹1,000,000 so Authority Engine allows it.")

boost_agent_limits()
print("Sending Natural Language Task to Agent...")

payload = {
    "agent_id": 1,
    "task": "Settle the annual enterprise contract for AWS Cloud Hosting. Transfer ₹850000 to ABC Technologies.",
    "context": [
        {
            "source": "slack_approval_bot",
            "confidence": 0.95,
            "raw_prompt": "Treasury, please pay the massive annual AWS bill to ABC Technologies. Amount is ₹850,000."
        }
    ]
}

response = requests.post(API_URL, json=payload)

if response.status_code in (200, 201):
    data = response.json()
    print(f"✅ Success! Action proposed with ID: {data['proposal']['action_id']}")
    print(f"   Parser used: {data['parser']}")
    print("\n👉 Now open your dashboard (http://localhost:5173/actions).")
    print("Watch AEGIS-X ESCALATE this to a human! The Intent is perfectly benign, but the Financial DNA engine will flag a massive amount spike, pushing the risk score just high enough to require manual Human approval.")
else:
    print(f"❌ Failed: {response.text}")
