import requests as r
import json
from .fetchers import setToken, flushToken

"""
manage autointication
"""
auth_url = ""

def auth(token):
    header = {
        "Authitntication": token
    }

    res = r.post()
