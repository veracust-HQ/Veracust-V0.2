from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import httpx
from voice_guard import VeracustEngine

security_scheme = HTTPBearer(auto_error=False)

app = FastAPI(
    title="VERACUST Enterprise Gateway",
    description="Deterministic Acoustic Authenticity Protocol | Veracust",
    version="4.0.0"
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
POLICY_VERSION = "2026-11-17"
FRONTEND_ORIGIN = os.environ.get(
    "FRONTEND_ORIGIN", "https://frontend-01-j8w5.onrender.com"
)
ALLOWED_ORIGINS = [x.strip() for x in FRONTEND_ORIGIN.split(",") if x.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["http://localhost:3000", "http://127.0.0.1:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "apikey"],
)

guard = VeracustEngine()
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".webm"}


def _supabase_headers(access_token: str):
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise HTTPException(status_code=503, detail="Account services are not configured.")
    return {
        "apikey": SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


async def current_user(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to use the Veracust evaluation dashboard.")
    token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Your session is invalid. Please sign in again.")
    headers = _supabase_headers(token)
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(f"{SUPABASE_URL}/auth/v1/user", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not validate your account session.") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    user = response.json()
    if not user.get("id"):
        raise HTTPException(status_code=401, detail="Supabase did not return a valid user.")
    return {"id": user["id"], "email": user.get("email"), "token": token}


async def require_policy_acceptance(user):
    headers = _supabase_headers(user["token"])
    params = {
        "select": "id",
        "user_id": f"eq.{user['id']}",
        "policy_version": f"eq.{POLICY_VERSION}",
        "limit": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/policy_acceptances",
                headers=headers,
                params=params,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not verify the evaluation policy acceptance.") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Could not verify the evaluation policy acceptance.")
    if not response.json():
        raise HTTPException(status_code=403, detail="Please review and accept the current Veracust Evaluation Policy before uploading audio.")


async def record_event(user, event_type, verdict=None, confidence_score=None, analysis_metadata=None):
    headers = _supabase_headers(user["token"])
    payload = {
        "user_id": user["id"],
        "event_type": event_type,
        "verdict": verdict,
        "confidence_score": confidence_score,
        "analysis_metadata": analysis_metadata or {},
    }
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/evaluation_events",
                headers={**headers, "Prefer": "return=minimal"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not save this evaluation activity.") from exc
    if response.status_code not in (200, 201, 204):
        raise HTTPException(status_code=503, detail="Could not save this evaluation activity. Please retry.")


async def event_count(user, event_type):
    headers = _supabase_headers(user["token"])
    params = {"select": "id", "event_type": f"eq.{event_type}"}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/evaluation_events",
                headers={**headers, "Prefer": "count=exact", "Range": "0-0"},
                params=params,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not load your account activity.") from exc
    if response.status_code not in (200, 206):
        raise HTTPException(status_code=503, detail="Could not load your account activity.")
    content_range = response.headers.get("content-range", "*/0")
    try:
        return int(content_range.rsplit("/", 1)[1])
    except (ValueError, IndexError):
        return 0


@app.get("/")
def home():
    return {
        "status": "online",
        "engine": "VERACUST-Core-v3.0",
        "audio_retention": "not_intentionally_retained",
        "account_auth": "supabase"
    }


@app.get("/v1/stats", summary="View Your Veracust Evaluation Activity")
async def get_stats(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    user = await current_user(request)
    await require_policy_acceptance(user)
    headers = _supabase_headers(user["token"])
    params = {
        "select": "event_type,verdict,confidence_score,analysis_metadata,created_at",
        "event_type": "eq.inspection",
        "order": "created_at.desc",
        "limit": "50",
    }
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(
                f"{SUPABASE_URL}/rest/v1/evaluation_events",
                headers=headers,
                params=params,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Could not load your evaluation history.") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Could not load your evaluation history.")
    rows = response.json()
    inspections = [row for row in rows if row.get("event_type") == "inspection"]
    return {
        "total_inspections": await event_count(user, "inspection"),
        "total_logins": await event_count(user, "login"),
        "synthetic_detected": sum(1 for row in inspections if row.get("verdict") == "SYNTHETIC_DETECTED"),
        "authentic_human": sum(1 for row in inspections if row.get("verdict") == "AUTHENTIC_HUMAN"),
        "recent_audit_trail": inspections[:10],
        "policy_version": POLICY_VERSION,
    }


@app.post("/v1/verify", summary="Verify Audio Stream Authenticity")
async def verify_audio(request: Request, file: UploadFile = File(...), credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    user = await current_user(request)
    await require_policy_acceptance(user)

    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported audio format. Use WAV, MP3, M4A, OGG, FLAC, AAC or WEBM.")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="veracust_", suffix=suffix, delete=False) as tmp:
            temp_path = tmp.name
            size = 0
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Audio file exceeds the 25 MB upload limit.")
                tmp.write(chunk)

        if size == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        started = datetime.now(timezone.utc)
        result = guard.verify(temp_path)
        if result.get("verdict") == "ERROR":
            raise HTTPException(status_code=422, detail="Audio could not be decoded or analyzed.")

        elapsed_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000, 2)
        # Store only analysis metadata. Never store the audio bytes or original filename.
        metadata = {
            "recommended_action": result.get("recommended_action"),
            "channel_telemetry": result.get("channel_telemetry", {}),
            "anomalies_flagged": result.get("anomalies_flagged", []),
            "processing_time_ms": elapsed_ms,
        }
        await record_event(
            user,
            "inspection",
            verdict=result.get("verdict"),
            confidence_score=result.get("confidence_score"),
            analysis_metadata=metadata,
        )
        return result
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        await file.close()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
