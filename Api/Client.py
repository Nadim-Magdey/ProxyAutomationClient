import time
import hmac
import hashlib
import secrets
import json
import requests


class ApiClient:
    SECRET = "1d56sa1d5a6s1d65as1d65as1a56dadas65d1d8a6s78vc97v8978a9sda"

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        
    def _generate_headers(self, body_str: str):
        """Generate HMAC headers. `body_str` must be the exact string sent in request body."""
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(8)

        message = f"{self.token}{timestamp}{nonce}{body_str}"

        signature = hmac.new(
            self.SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return {
            "Authorization": f"Token {self.token}",
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
            "Content-Type": "application/json"
        }

    def get(self, path, params=None):
        """GET request: HMAC uses empty body"""
        body_str = ""  # <- empty string for GET
        headers = self._generate_headers(body_str)
        url = f"{self.base_url}{path}"
        response = self.session.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, path, data=None):
        """POST request: HMAC uses JSON body"""
        data = data or {}
        body_str = json.dumps(data, sort_keys=True)  # must match request.body
        headers = self._generate_headers(body_str)
        url = f"{self.base_url}{path}"
        response = self.session.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()

