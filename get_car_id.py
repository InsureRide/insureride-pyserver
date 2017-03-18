import json, requests

resp = requests.get(url='https://insureride.net/api/v1/user')
data = json.loads(resp.text)

print data["1"]["CarAddress"]
