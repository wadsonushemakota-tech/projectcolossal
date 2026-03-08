from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv


load_dotenv()


def api_base_url() -> str:
    return os.getenv("COLOSSAL_API_URL", "http://127.0.0.1:8001").rstrip("/")


class ApiError(RuntimeError):
    pass


def _handle(resp: requests.Response) -> Any:
    if resp.ok:
        if resp.content:
            return resp.json()
        return None
    try:
        payload = resp.json()
        detail = payload.get("detail") if isinstance(payload, dict) else payload
    except Exception:
        detail = resp.text
    raise ApiError(f"{resp.status_code}: {detail}")


def get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    resp = requests.get(f"{api_base_url()}{path}", params=params, timeout=20)
    return _handle(resp)


def post(
    path: str,
    json: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    files: Any = None,
) -> Any:
    resp = requests.post(f"{api_base_url()}{path}", json=json, params=params, files=files, timeout=60)
    return _handle(resp)

