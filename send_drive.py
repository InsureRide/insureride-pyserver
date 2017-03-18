import json, requests

carAddress = json.loads(requests.get(url='https://insureride.net/api/v1/user').text)["1"]["CarAddress"]
print "carAddress=%s" % (carAddress)
data = json.dumps({
    "Kilometers": 0.001070796745332,
    "Avgspeed": 0.35693224844,
    "Avgaccel": 0.356932248444,
    "Starttime": 1489878512,
    "Endtime": 1489878515
})
print "data:"
print data
print requests.post("https://insureride.net/api/v1/car/" + carAddress + "/drive", data = data).text
