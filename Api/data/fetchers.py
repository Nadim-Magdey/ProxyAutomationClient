import requests as r
import json

flows_url = "http://127.0.0.1:8000/api/service/flows/"
inputs_url = "http://127.0.0.1:8000/api/service/inputs/"


cyber_source_url = "http://127.0.0.1:8000/api/encrypt/cyber/"
apg_url = "http://127.0.0.1:8000/api/encrypt/apg/"

services_url = "http://127.0.0.1:8000/api/services/get/"


def fetch_flows(token, service_id):
    headers = {"Authorization" : token}
    res = r.get(flows_url, headers=headers)
    srt_content = res.content
    json_content = json.loads(srt_content)
    # print(f"json content {json_content}")
    flows = json_content.get("flows")

    return flows

    
def fetch_inputs(token, service_id):
    headers = {"Authorization" : token}
    res = r.get(inputs_url, headers=headers)
    srt_content = res.content
    json_content = json.loads(srt_content)
    # print(f"json content {json_content}")
    inputs = json_content.get("inputs")

    return inputs
    
def fetch_services(token):
    headers = {"Authorization" : f"Token {token}"}
    res = r.post(services_url, headers=headers)
    res_content = res.content
    print("contnent", res_content)
    json_content = json.loads(res_content)
    print(f"json content {json_content}")
    services = json_content["result"]["services"]

    return services


def apply_apg(c, v, m, y, pct, n,e ,sessionId,merchantId):

    headers = {"Authorization" : ""}

    cardData= {
        "c": c,
        "v": v,
        "m": m,
        "y": y,
        "pct": pct 
        }
    
    publicKey = {
        "n": n,
        "e": e 
        }
    
    extra = {
        "sessionId": sessionId,
        "merchantId": merchantId
    }

    payload = {
        "cardData": cardData,
        "publicKey":publicKey,
        "extra": extra
        }

    res = r.post(apg_url,headers=headers, json=payload)
    return res.content
    
def apply_cyber():
    pass

if __name__ == "__main__":
    result = apply_apg("1", "2", "3", "4", "5", "6", "7", "8", "9")
    print(result)
