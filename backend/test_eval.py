import requests
import json
res = requests.post("http://localhost:8000/actions/act_9bc204f4a8d84614/evaluate")
print(json.dumps(res.json(), indent=2))
