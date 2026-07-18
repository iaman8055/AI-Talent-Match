from typing import Protocol


class EmailProvider(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...
