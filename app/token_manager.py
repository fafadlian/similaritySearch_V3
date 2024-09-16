import threading
import time
import requests
import os
import logging

import threading
import time
import requests
import os
import logging

class TokenManager:
    _instance = None
    _lock = threading.Lock()
    _token = None
    _token_expiry = None
    _max_requests = 1000  # Set your maximum number of requests here
    _request_count = 0

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(TokenManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.api_url = 'https://tenacity-rmt.eurodyn.com/api/user/auth/token'
        self.username = os.getenv("USERNAME")
        self.password = os.getenv("PASSWORD")

    def get_token(self):
        with self._lock:
            if self._token and self._token_expiry and self._token_expiry > time.time() and self._request_count < self._max_requests:
                self._request_count += 1
                return self._token
            return self._reauthenticate()

    def _reauthenticate(self):
        data = {'username': self.username, 'password': self.password}
        response = requests.post(self.api_url, json=data)
        if response.status_code == 200:
            tokens = response.json()
            self._token = tokens["accessToken"]
            os.environ["ACCESS_TOKEN"] = self._token
            self._token_expiry = time.time() + 3600  # Token expiry time, e.g., 1 hour
            self._request_count = 0  # Reset request count
            logging.info("Re-authenticated successfully")
            return self._token
        else:
            logging.error(f"Failed to re-authenticate: {response.status_code} - {response.text}")
            return None

# Usage in your fetch functions
token_manager = TokenManager()
token = token_manager.get_token()

