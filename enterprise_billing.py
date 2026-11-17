"""Central control-plane endpoints for private Veracust deployments.

These routes run on Veracust's hosted API, never inside customer Docker containers.
Customer deployments authenticate with a per-deployment bearer token. Only a SHA-256
hash of that token is stored in Supabase.
"""
import hashlib
import os
from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


def _admin_headers():
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Enterprise billing control plane is not configured.")
    return url, {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


async def _deployment(credentials: HTTPAuthorizationCredentials | None):
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="A deployment credential is required.")
    token_hash = hashlib.sha256(credentials.credentials.encode("utf-8")).hexdigest()
    url, headers = _admin_headers()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{url}/rest/v1/enterprise_deployments",
                headers=headers,
                params={
                    "select": "id,account_id,status",
                    "credential_hash": f"eq.{token_hash}",
                    "status": "eq.active",
                    "limit": "1",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not validate deployment with Veracust.") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Could not validate deployment with Veracust.")
    rows = response.json()
    if len(rows) != 1:
        raise HTTPException(status_code=401, detail="Deployment credential is invalid or revoked.")
    deployment = rows[0]
    # Update last-seen telemetry; never include audio, filenames, transcripts, or credentials.
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.patch(
                f"{url}/rest/v1/enterprise_deployments",
                headers={**headers, "Prefer": "return=minimal"},
                params={"id": f"eq.{deployment['id']}"},
                json={"last_seen_at": datetime.now(timezone.utc).isoformat()},
            )
    except httpx.HTTPError:
        pass
    return url, headers, deployment


async def _rpc(url: str, headers: dict, function_name: str, payload: dict):
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                f"{url}/rest/v1/rpc/{function_name}",
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Veracust billing service is temporarily unavailable.") from exc
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=503, detail="Veracust could not update the usage ledger.")
    return response.json()


class AuthorizeInspection(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class FinalizeInspection(BaseModel):
    reservation_id: UUID
    success: bool


@router.post("/v1/control/authorize", summary="Authorize one private deployment inspection")
async def authorize_inspection(
    body: AuthorizeInspection,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    url, headers, deployment = await _deployment(credentials)
    result = await _rpc(
        url, headers, "enterprise_reserve_inspection",
        {
            "p_account_id": deployment["account_id"],
            "p_deployment_id": deployment["id"],
            "p_idempotency_key": body.idempotency_key,
        },
    )
    if not result.get("allowed"):
        reason = result.get("reason", "INSPECTION_NOT_AUTHORIZED")
        status_code = 402 if reason in {"SPENDING_CAP_REACHED", "SPENDING_CAP_NOT_CONFIGURED"} else 403
        raise HTTPException(status_code=status_code, detail={"code": reason, "message": "Inspection not authorized."})
    return result


@router.post("/v1/control/finalize", summary="Finalize one private deployment inspection")
async def finalize_inspection(
    body: FinalizeInspection,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    url, headers, deployment = await _deployment(credentials)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{url}/rest/v1/enterprise_inspection_reservations",
                headers=headers,
                params={
                    "select": "id",
                    "id": f"eq.{str(body.reservation_id)}",
                    "deployment_id": f"eq.{deployment['id']}",
                    "limit": "1",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not validate inspection reservation.") from exc
    if response.status_code != 200 or not response.json():
        raise HTTPException(status_code=404, detail="Inspection reservation was not found for this deployment.")
    return await _rpc(
        url, headers, "enterprise_finalize_inspection",
        {"p_reservation_id": str(body.reservation_id), "p_success": body.success},
    )
