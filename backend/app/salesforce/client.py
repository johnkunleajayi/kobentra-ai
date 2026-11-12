import re
import threading
import time
from urllib.parse import urlparse

import httpx

from .budget import timeout


class SalesforceError(Exception):
    """Intentionally excludes response bodies, URLs, credentials and user data."""


class SalesforceClient:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.origin = (settings.salesforce_instance_url or "").rstrip("/")
        self.http = httpx.Client(
            timeout=httpx.Timeout(20, connect=5), follow_redirects=False, transport=transport
        )
        self.token = None
        self.expires = 0.0
        self.lock = threading.Lock()

    def close(self):
        self.http.close()

    def _authenticate(self, force=False):
        with self.lock:
            if not force and self.token and time.monotonic() < self.expires:
                return
            if (
                not self.origin
                or not self.settings.salesforce_client_id
                or not self.settings.salesforce_client_secret
            ):
                raise SalesforceError("Salesforce authentication unavailable")
            try:
                response = self.http.post(
                    self.origin + "/services/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.settings.salesforce_client_id.get_secret_value(),
                        "client_secret": self.settings.salesforce_client_secret.get_secret_value(),
                    },
                    timeout=timeout(),
                )
                response.raise_for_status()
                data = response.json()
                if data.get("instance_url", self.origin).rstrip("/") != self.origin:
                    raise ValueError
                token = data["access_token"]
                if not isinstance(token, str) or not token:
                    raise ValueError
                # Core Salesforce may omit expires_in; use a conservative local cache TTL.
                lifetime = min(float(data.get("expires_in", 300)), 300)
                self.token, self.expires = token, time.monotonic() + max(0, lifetime - 15)
            except (httpx.HTTPError, ValueError, KeyError, TypeError, TimeoutError):
                self.token = None
                raise SalesforceError("Salesforce authentication unavailable") from None

    def request(self, method, path, **kwargs):
        if (
            not path.startswith("/services/data/v68.0/")
            or urlparse(path).netloc
            or "?" in path
            or ".." in path
        ):
            raise SalesforceError("Invalid Salesforce resource")
        try:
            self._authenticate()
            for attempt in range(2):
                response = self.http.request(
                    method,
                    self.origin + path,
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=timeout(),
                    **kwargs,
                )
                if response.status_code == 401 and attempt == 0:
                    self._authenticate(force=True)
                    continue
                response.raise_for_status()
                return response.json() if response.content else {}
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError):
            raise SalesforceError(
                "Salesforce request failed; reconciliation may be required"
            ) from None
        raise SalesforceError("Salesforce authentication unavailable")

    def query(self, soql):
        page = self.request("GET", "/services/data/v68.0/query", params={"q": soql})
        rows = []
        for _ in range(20):
            if not isinstance(page.get("records"), list):
                raise SalesforceError("Invalid Salesforce query response")
            rows.extend(page["records"])
            if page.get("done") is True:
                return rows
            next_url = page.get("nextRecordsUrl", "")
            if not re.fullmatch(r"/services/data/v68\.0/query/[A-Za-z0-9-]+", next_url):
                raise SalesforceError("Invalid query continuation")
            page = self.request("GET", next_url)
        raise SalesforceError("Reconciliation query exceeded safety bound")
