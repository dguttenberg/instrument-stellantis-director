"""Live Brand Gravity HTTP provider (thin stub).

Brand Gravity is a live consumer-grade service; the agent posts the structured
request to POST {base_url}/v1/context and parses the documented response shape.
The RAM buckets are not yet connected, so this path is unexercised — kept thin and
interface-complete so it can be wired and tested when the buckets come online.
"""

from __future__ import annotations

import httpx

from ..schemas.bg import BGRequest, BGResponse

CONTEXT_PATH = "/v1/context"


class HttpBGProvider:
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def resolve(self, request: BGRequest) -> BGResponse:
        headers = {"content-type": "application/json"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        resp = httpx.post(
            f"{self.base_url}{CONTEXT_PATH}",
            json=request.model_dump(mode="json"),
            headers=headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return BGResponse.model_validate(resp.json())
