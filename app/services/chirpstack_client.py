from __future__ import annotations

import secrets
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.core.exceptions import ChirpStackError

_client: Optional[httpx.AsyncClient] = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        settings = get_settings()
        base_url = settings.chirpstack_base_url.rstrip("/")
        if not base_url.endswith("/api"):
            base_url = f"{base_url}/api"

        _client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {settings.chirpstack_api_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def generate_lorawan_keys() -> Tuple[str, str]:
    dev_eui = secrets.token_hex(8)
    app_key = secrets.token_hex(16)
    return dev_eui, app_key


def _raise_if_error(resp: httpx.Response, fallback_msg: str) -> None:
    if resp.is_success:
        return
    try:
        body = resp.json()
    except Exception:
        body = None
    detail = fallback_msg
    if isinstance(body, dict):
        msg = body.get("message") or body.get("error") or body.get("detail")
        if msg:
            detail = str(msg)
    raise ChirpStackError(detail, status_code=resp.status_code, body=body)


async def get_all_tenants(limit: int = 100) -> List[Dict[str, Any]]:
    client = await _get_client()
    tenants: List[Dict[str, Any]] = []
    offset = 0
    while True:
        resp = await client.get(
            "/tenants",
            params={"limit": limit, "offset": offset},
        )
        resp.raise_for_status()
        data = resp.json()
        tenants.extend(data.get("result", []))
        if len(tenants) >= data.get("totalCount", 0):
            break
        offset += limit
    return tenants


async def get_all_devices(application_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    client = await _get_client()
    devices: List[Dict[str, Any]] = []
    offset = 0
    while True:
        resp = await client.get(
            "/devices",
            params={
                "applicationId": application_id,
                "limit": limit,
                "offset": offset,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        devices.extend(data.get("result", []))
        if len(devices) >= data.get("totalCount", 0):
            break
        offset += limit
    return devices


async def get_device(dev_eui: str) -> Dict[str, Any]:
    client = await _get_client()
    resp = await client.get(f"/devices/{dev_eui}")
    _raise_if_error(resp, f"ChirpStack: failed to get device {dev_eui}")
    body = resp.json()
    return body.get("device", body)


async def create_device(
        application_id: str,
        device_profile_id: str,
        dev_eui: str,
        name: str,
        tags: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    client = await _get_client()
    payload = {
        "device": {
            "applicationId": application_id,
            "deviceProfileId": device_profile_id,
            "devEui": dev_eui.lower().strip(),
            "name": name,
            "tags": tags if tags is not None else {},
        }
    }
    resp = await client.post("/devices", json=payload)
    _raise_if_error(resp, f"ChirpStack: failed to create device {dev_eui}")
    return resp.json() if resp.content else {}


async def update_device(dev_eui: str, name: str) -> None:
    client = await _get_client()
    payload = {"device": {"name": name}}
    resp = await client.put(f"/devices/{dev_eui}", json=payload)
    _raise_if_error(resp, f"ChirpStack: failed to update device {dev_eui}")


async def delete_device(dev_eui: str) -> None:
    client = await _get_client()
    resp = await client.delete(f"/devices/{dev_eui}")
    _raise_if_error(resp, f"ChirpStack: failed to delete device {dev_eui}")


async def set_device_keys(
        dev_eui: str,
        app_key: str,
        *,
        nwk_key: Optional[str] = None,
) -> None:
    dev_eui = dev_eui.lower().strip()
    app_key = app_key.strip().lower()

    client = await _get_client()
    payload = {
        "deviceKeys": {
            "devEui": dev_eui,
            "nwkKey": nwk_key.strip().lower() if nwk_key else app_key,
            "appKey": app_key,
        }
    }

    resp = await client.post(f"/devices/{dev_eui}/keys", json=payload)

    if resp.status_code == 409 or (
            resp.is_client_error and "exists" in resp.text.lower()
    ):
        resp = await client.put(f"/devices/{dev_eui}/keys", json=payload)

    _raise_if_error(resp, f"ChirpStack: failed to set/update keys for {dev_eui}")


async def create_tenant(name: str, description: str = "") -> str:
    client = await _get_client()
    payload = {
        "tenant": {
            "name": name,
            "description": description,
            "canHaveGateways": True,
        }
    }
    resp = await client.post("/tenants", json=payload)
    _raise_if_error(resp, f"ChirpStack: failed to create tenant '{name}'")
    data = resp.json()
    return data.get("id", "")


async def create_application(tenant_id: str, name: str = "default_application") -> str:
    client = await _get_client()
    payload = {
        "application": {
            "tenantId": tenant_id,
            "name": name,
        }
    }
    resp = await client.post("/applications", json=payload)
    _raise_if_error(resp, f"ChirpStack: failed to create application '{name}'")
    data = resp.json()
    return data.get("id", "")


async def delete_application(application_id: str) -> None:
    """Delete an application from ChirpStack. Silently ignores 404."""
    client = await _get_client()
    resp = await client.delete(f"/applications/{application_id}")
    if resp.status_code == 404:
        return
    _raise_if_error(resp, f"ChirpStack: failed to delete application {application_id}")


async def delete_device_profile(device_profile_id: str) -> None:
    """Delete a device profile from ChirpStack. Silently ignores 404."""
    client = await _get_client()
    resp = await client.delete(f"/device-profiles/{device_profile_id}")
    if resp.status_code == 404:
        return
    _raise_if_error(resp, f"ChirpStack: failed to delete device profile {device_profile_id}")


async def delete_tenant(tenant_id: str) -> None:
    """Delete a tenant from ChirpStack. Silently ignores 404."""
    client = await _get_client()
    resp = await client.delete(f"/tenants/{tenant_id}")
    if resp.status_code == 404:
        return
    _raise_if_error(resp, f"ChirpStack: failed to delete tenant {tenant_id}")


async def create_device_profile(
        tenant_id: str,
        name: str,
        *,
        region: str = "EU868",
        mac_version: str = "LORAWAN_1_0_3",
        reg_params_revision: str = "A",
        supports_otaa: bool = True,
        supports_class_b: bool = False,
        supports_class_c: bool = False,
) -> str:
    client = await _get_client()
    payload = {
        "deviceProfile": {
            "tenantId": tenant_id,
            "name": name,
            "region": region,
            "macVersion": mac_version,
            "regParamsRevision": reg_params_revision,
            "supportsOtaa": supports_otaa,
            "supportsClassB": supports_class_b,
            "supportsClassC": supports_class_c,
        }
    }
    resp = await client.post("/device-profiles", json=payload)
    _raise_if_error(resp, f"ChirpStack: failed to create device profile '{name}'")
    data = resp.json()
    return data.get("id", "")


async def register_new_device_automated(
        application_id: str, device_profile_id: str, name: str
) -> Dict[str, str]:
    dev_eui, app_key = generate_lorawan_keys()
    await create_device(application_id, device_profile_id, dev_eui, name)
    await set_device_keys(dev_eui, app_key)
    return {"dev_eui": dev_eui, "app_key": app_key}