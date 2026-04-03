# Api/endpoints.py

from .Client import ApiClient
from Api.data.AuthEngine.AuthManager import AuthManager

# BASE_URL = "https://bazookabeef.pythonanywhere.com"
BASE_URL = "http://127.0.0.1:8000"

# Singleton auth manager
auth_manager = AuthManager()

def login_with_telegram_token(token: str):
    """
    Log in using a Telegram login token.
    Returns an ApiClient instance if successful, else None.
    """
    success = auth_manager.login_with_token(token, base_url=BASE_URL)
    if success:
        return auth_manager.get_client()
    else:
        print("Login failed")
        return None

        
class ApiEndpoints:
    def __init__(self, client: ApiClient):
        self.client = client

    # -----------------------------
    # Services
    # -----------------------------
    def get_services(self):
        """Fetch all services available to the user"""
        return self.client.post("/api/services/get/", data={})

    def get_flows(self):
        """Fetch all service flows"""
        return self.client.get("/api/service/flows/")

    def get_inputs(self):
        """Fetch service inputs"""
        return self.client.get("/api/service/inputs/")

    # -----------------------------
    # Encryption
    # -----------------------------
    def encrypt_cybersource(self, card_data, public_key, extra=None):
        payload = {
            "cardData": card_data,
            "publicKey": public_key,
            "extra": extra or {}
        }
        return self.client.post("/api/encrypt/cyber/", payload)

    def encrypt_apg(self, card_data, public_key, extra=None):
        payload = {
            "cardData": card_data,
            "publicKey": public_key,
            "extra": extra or {}
        }
        return self.client.post("/api/encrypt/apg/", payload)

    # -----------------------------
    # User
    # -----------------------------
    def get_user_info(self):
        return self.client.post("/api/user/info/", data={})

    def get_user_proxies(self):
        return self.client.post("/api/user/proxy/", data={})

    def send_user_logs(self, service_name, info, log_type="INFO"):
        payload = {
            "service_name": service_name,
            "info": info,
            "logType": log_type
        }
        return self.client.post("/api/user/logs/", payload)

    def send_user_notification(self, variables, success):
        payload = {
            "variables": variables,
            "sucess": success
        }
        return self.client.post("/api/user/notification/", payload)
        
    # -----------------------------
    # Flow constraints
    # -----------------------------
    def get_flow_constraints(self):
        return self.client.get("/api/service/constraints/")


if __name__ == "__main__":
    
    telegram_token = "440bd32fe5ef4fe38cce86d2d525737c823577ae"
    client = login_with_telegram_token(telegram_token)

    if client:
        api = ApiEndpoints(client)

        # Fetch services
        services = api.get_services()
        print(services)

        # Fetch flows
        flows = api.get_flows()
        print(flows)

