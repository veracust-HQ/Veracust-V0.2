from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from voice_guard import VeracustEngine

app = FastAPI(
    title="VERACUST Enterprise Gateway",
    description="Deterministic Acoustic Authenticity Protocol | Veracust",
    version="3.3.0"
)

# Public evaluation UI needs cross-origin access. Restrict this to your deployed
# frontend domain before using the API for a customer-facing production service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

guard = VeracustEngine()
AUDIT_LOG_FILE = "audit_log.json"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".webm"}

def log_verification(filename: str, verdict: str, confidence: float):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file_name": Path(filename).name[:180],
        "verdict": verdict,
        "confidence": confidence
    }
    logs = []
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
            if not isinstance(logs, list):
                logs = []
        except (OSError, ValueError):
            logs = []
    logs.append(log_entry)
    with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs[-1000:], f, indent=2)

@app.get("/")
def home():
    total_scanned = 0
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                total_scanned = len(json.load(f))
        except (OSError, ValueError, TypeError):
            pass
    return {
        "status": "online",
        "engine": "VERACUST-Core-v3.0",
        "total_streams_audited": total_scanned
    }

@app.get("/v1/stats", summary="View Enterprise Usage Analytics")
def get_stats():
    if not os.path.exists(AUDIT_LOG_FILE):
        return {"total_inspections": 0, "synthetic_detected": 0, "authentic_human": 0, "recent_audit_trail": []}
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        if not isinstance(logs, list):
            logs = []
        synthetic_count = sum(1 for entry in logs if entry.get("verdict") == "SYNTHETIC_DETECTED")
        human_count = sum(1 for entry in logs if entry.get("verdict") == "AUTHENTIC_HUMAN")
        return {
            "total_inspections": len(logs),
            "synthetic_detected": synthetic_count,
            "authentic_human": human_count,
            "recent_audit_trail": logs[-10:]
        }
    except (OSError, ValueError) as e:
        raise HTTPException(status_code=500, detail="Could not read audit history") from e

@app.post("/v1/verify", summary="Verify Audio Stream Authenticity")
async def verify_audio(file: UploadFile = File(...)):
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

        result = guard.verify(temp_path)
        if result.get("verdict") == "ERROR":
            raise HTTPException(status_code=422, detail=result.get("error", "Audio could not be decoded or analyzed."))

        log_verification(filename, result["verdict"], result.get("confidence_score", 0.0))
        return result
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        await file.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
