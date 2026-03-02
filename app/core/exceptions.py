from __future__ import annotations

from typing import Any, Optional


class ChirpStackError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        body: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body
