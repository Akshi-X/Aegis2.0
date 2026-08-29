import requests
import json
res = requests.post("http://localhost:8000/actions/act_3fe566c302514d18/evaluate")
print("Response code:", res.status_code)
if res.status_code != 200:
    print(res.text)
else:
    evals = res.json()
    print("Decision:", evals["evaluation"]["decision"])
