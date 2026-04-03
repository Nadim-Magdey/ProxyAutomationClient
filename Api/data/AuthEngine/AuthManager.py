import requests as r
import json

auth_url = "https://bazookabeef.pythonanywhere.com/api/auth/check/"
from ...Client import ApiClient

class AuthManager:
    token = None
    _instance = None
    api_client: ApiClient = None
    is_auth = False

    def login_with_token(self, token: str, base_url="https://bazookabeef.pythonanywhere.com"):
        """
        Accept the token you got from Telegram login.
        Initializes the ApiClient for further HMAC-signed requests.
        """

        # Create HMAC-ready client
        self.api_client = ApiClient(base_url=base_url, token=token)
        
        # Test authentication by hitting a safe endpoint (like /services/get/)
        try:
            resp = self.api_client.post("/api/services/get/", data={})
            self.is_auth = True
        except Exception as e:
            print("Auth failed:", e)
            self.is_auth = False

        return self.is_auth
        
    def get_client(self) -> ApiClient:
        if not self.is_auth:
            raise Exception("Not authenticated")
        return self.api_client

    def getToken(self):
        return self.token

    def setToken(self, token):
        self.token = token