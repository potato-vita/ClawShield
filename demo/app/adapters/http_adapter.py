from urllib.parse import urlparse


class HttpAdapter:
    def request(self, method: str, url: str, payload: dict | None = None) -> dict:
        # Demo uses simulated HTTP responses to avoid unsafe external side effects.
        domain = urlparse(url).netloc
        return {
            "simulated": True,
            "method": method.upper(),
            "url": url,
            "domain": domain,
            "payload": payload or {},
            "response": {"status_code": 200, "body": "mock-ok"},
        }
