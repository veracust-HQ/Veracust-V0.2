"""Central control-plane endpoints for private Veracust deployments.

These routes run on Veracust's hosted API, never inside customer Docker containers.
Customer deployments authenticate with a per-deployment bearer token. Only a SHA-256
hash of that token is stored in Supabase.
"""
import hashlib
import os
import secrets
import hmac
from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from uuid import UUID

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


class CreateDeployment(BaseModel):
    account_id: UUID
    subscription_id: UUID
    deployment_name: str = Field(min_length=2, max_length=120)


class AuthorizeInspection(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class FinalizeInspection(BaseModel):
    reservation_id: UUID
    success: bool




BILLING_CONSENT_VERSION = "enterprise-billing-v1-2026-11-18"


class EnterpriseConsent(BaseModel):
    plan_code: str = Field(min_length=3, max_length=80)
    accept_plan_price: bool
    accept_overage_rate: bool
    accept_spending_cap: bool


def _user_supabase_headers(access_token: str):
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
    if not url or not publishable_key:
        raise HTTPException(status_code=503, detail="Account services are not configured.")
    return url, {
        "apikey": publishable_key,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


async def _authenticated_customer(request: Request):
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer ") or not authorization[7:].strip():
        raise HTTPException(status_code=401, detail="Sign in before choosing an enterprise plan.")
    token = authorization[7:].strip()
    url, headers = _user_supabase_headers(token)
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(f"{url}/auth/v1/user", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not validate your Veracust session.") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Your Veracust session has expired. Please sign in again.")
    user = response.json()
    if not user.get("id"):
        raise HTTPException(status_code=401, detail="Could not identify your Veracust account.")
    return {"id": user["id"], "token": token}


async def _service_request(method: str, url: str, headers: dict, path: str, **kwargs):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(method, f"{url}/rest/v1/{path}", headers=headers, **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Veracust billing service is temporarily unavailable.") from exc
    if response.status_code not in (200, 201, 204):
        raise HTTPException(status_code=503, detail="Veracust could not save the enterprise billing request.")
    return response


@router.get("/v1/enterprise/plans", summary="List enterprise plans and calculated spending caps")
async def list_enterprise_plans(request: Request):
    await _authenticated_customer(request)
    url, headers = _admin_headers()
    response = await _service_request(
        "GET", url, headers, "enterprise_plan_catalog",
        params={"select": "plan_code,display_name,term_months,price_usd_cents,included_calls,standard_bonus_calls,overage_price_usd_micros", "active": "eq.true", "order": "term_months.asc"},
    )
    plans = []
    for row in response.json():
        months = int(row["term_months"])
        monthly_equivalent_cents = (int(row["price_usd_cents"]) * 90 + months * 50) // (months * 100)
        cap_cents = monthly_equivalent_cents
        plans.append({
            **row,
            "monthly_overage_cap_usd_cents": cap_cents,
            "monthly_overage_cap_usd": f"{cap_cents / 100:.2f}",
        })
    return {"plans": plans, "overage_rate_usd": "0.005", "consent_version": BILLING_CONSENT_VERSION}


@router.post("/v1/enterprise/consent", summary="Record explicit enterprise plan and overage consent")
async def record_enterprise_consent(body: EnterpriseConsent, request: Request):
    if not (body.accept_plan_price and body.accept_overage_rate and body.accept_spending_cap):
        raise HTTPException(status_code=400, detail="All billing acknowledgements are required.")
    user = await _authenticated_customer(request)
    url, headers = _admin_headers()

    account_response = await _service_request(
        "GET", url, headers, "usage_accounts",
        params={"select": "id", "user_id": f"eq.{user['id']}", "is_active": "eq.true", "limit": "2"},
    )
    accounts = account_response.json()
    if len(accounts) != 1:
        raise HTTPException(status_code=409, detail="Your login must have exactly one active usage account. Contact Veracust support.")
    account_id = accounts[0]["id"]

    plan_response = await _service_request(
        "GET", url, headers, "enterprise_plan_catalog",
        params={"select": "plan_code,display_name,term_months,price_usd_cents,included_calls,standard_bonus_calls,overage_price_usd_micros", "plan_code": f"eq.{body.plan_code}", "active": "eq.true", "limit": "1"},
    )
    plans = plan_response.json()
    if len(plans) != 1:
        raise HTTPException(status_code=400, detail="The selected enterprise plan is not available.")
    plan = plans[0]

    months = int(plan["term_months"])
    price_cents = int(plan["price_usd_cents"])
    monthly_equivalent_cents = (price_cents * 90 + months * 50) // (months * 100)
    cap_cents = monthly_equivalent_cents
    accepted_at = datetime.now(timezone.utc).isoformat()
    subscription_payload = {
        "account_id": account_id,
        "user_id": user["id"],
        "plan_code": plan["plan_code"],
        "status": "pending_payment",
        "currency": "USD",
        "subscription_price_usd_cents": price_cents,
        "included_calls": int(plan["included_calls"]),
        "bonus_calls": int(plan["standard_bonus_calls"]),
        "overage_price_usd_micros": int(plan["overage_price_usd_micros"]),
        "overage_cap_usd_micros": cap_cents * 10000,
        "billing_consent_version": BILLING_CONSENT_VERSION,
        "billing_consent_at": accepted_at,
        "overage_rate_accepted_at": accepted_at,
        "spending_cap_accepted_at": accepted_at,
        "updated_at": accepted_at,
    }

    pending_response = await _service_request(
        "GET", url, headers, "enterprise_subscriptions",
        params={"select": "id,billing_consent_at", "account_id": f"eq.{account_id}", "user_id": f"eq.{user['id']}", "plan_code": f"eq.{plan['plan_code']}", "status": "eq.pending_payment", "order": "created_at.desc", "limit": "2"},
    )
    pending = pending_response.json()
    if len(pending) > 1:
        raise HTTPException(status_code=409, detail="Multiple pending subscriptions exist for this plan. Contact Veracust support before proceeding.")
    if pending and pending[0].get("billing_consent_at") is None:
        saved = await _service_request(
            "PATCH", url, {**headers, "Prefer": "return=representation"}, "enterprise_subscriptions",
            params={"id": f"eq.{pending[0]['id']}", "status": "eq.pending_payment"},
            json={k: v for k, v in subscription_payload.items() if k not in {"account_id", "user_id", "plan_code", "status"}},
        )
    elif pending:
        return {
            "subscription_id": pending[0]["id"],
            "status": "pending_payment",
            "consent_already_recorded": True,
            "plan": plan["display_name"],
            "monthly_overage_cap_usd": f"{cap_cents / 100:.2f}",
            "message": "Billing consent was already recorded. Payment and activation are not enabled.",
        }
    else:
        saved = await _service_request(
            "POST", url, {**headers, "Prefer": "return=representation"}, "enterprise_subscriptions",
            json=subscription_payload,
        )
    rows = saved.json() if saved.content else []
    subscription_id = rows[0]["id"] if rows else (pending[0]["id"] if pending else None)
    return {
        "subscription_id": subscription_id,
        "status": "pending_payment",
        "consent_recorded": True,
        "plan": plan["display_name"],
        "monthly_overage_cap_usd": f"{cap_cents / 100:.2f}",
        "overage_rate_usd": "0.005",
        "message": "Consent recorded. No payment was collected and the subscription remains inactive.",
    }


@router.post("/v1/admin/deployments", summary="Provision a customer deployment credential")
async def create_deployment(
    body: CreateDeployment,
    x_veracust_admin_key: str | None = Header(default=None),
):
    configured_admin_key = os.environ.get("VERACUST_ADMIN_API_KEY", "")
    if not configured_admin_key or not x_veracust_admin_key or not hmac.compare_digest(
        configured_admin_key, x_veracust_admin_key
    ):
        raise HTTPException(status_code=401, detail="Administrator authorization is required.")

    url, headers = _admin_headers()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            subscription_response = await client.get(
                f"{url}/rest/v1/enterprise_subscriptions",
                headers=headers,
                params={
                    "select": "id,account_id,status",
                    "id": f"eq.{str(body.subscription_id)}",
                    "account_id": f"eq.{str(body.account_id)}",
                    "status": "eq.active",
                    "limit": "1",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not validate the customer subscription.") from exc
    if subscription_response.status_code != 200 or not subscription_response.json():
        raise HTTPException(status_code=404, detail="No active subscription matches this customer account.")

    raw_token = secrets.token_urlsafe(40)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                f"{url}/rest/v1/enterprise_deployments",
                headers={**headers, "Prefer": "return=representation"},
                json={
                    "account_id": str(body.account_id),
                    "subscription_id": str(body.subscription_id),
                    "deployment_name": body.deployment_name,
                    "credential_hash": token_hash,
                    "status": "active",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not create deployment credential.") from exc
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=503, detail="Could not create deployment credential.")
    rows = response.json()
    if not rows:
        raise HTTPException(status_code=503, detail="Deployment credential was not created.")
    return {
        "deployment_id": rows[0]["id"],
        "deployment_name": body.deployment_name,
        "deployment_token": raw_token,
        "status": "active",
        "warning": "Copy this token now. It cannot be retrieved again.",
    }


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
