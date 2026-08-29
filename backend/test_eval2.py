import requests
import json
res = requests.get("http://localhost:8000/actions/act_9bc204f4a8d84614/evaluations")
evals = res.json()
print("Decision:", evals[0]["decision"])
print("Reason:", evals[0]["decision_reason"])
