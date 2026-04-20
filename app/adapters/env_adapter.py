import os


class EnvAdapter:
    def read(self, key: str) -> str | None:
        return os.getenv(key)
