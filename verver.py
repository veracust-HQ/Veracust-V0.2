from fastapi import FastAPI, UploadFile, File
import shutil
import os
import json
from datetime import datetime
from voice_guard import VeracustEngine

app = FastAPI(
    title="VERACUST Enterprise Gateway",
    description="Deterministic Acoustic Authenticity Protocol | Engineered by Utkarsh Dixit (Founder & Lead Systems Engineer)",
    version="3.0.0"
)

guard = VeracustEngine()

AUDIT_LOG_FILE = "audit_log.json"

def log_verification(filename: str, verdict: str, confidence: float):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "file_name": filename,
        "verdict": verdict,
        "confidence": confidence
    }
    logs = []
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    logs.append(log_entry)
    with open(AUDIT_LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

@app.get("/")
def home():
    total_scanned = 0
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, "r") as f:
                total_scanned = len(json.load(f))
        except Exception:
            pass
    return {
        "status": "online",
        "engine": "VERACUST-Core-v3.0",
        "architect": "Utkarsh Dixit",
        "total_streams_audited": total_scanned
    }

@app.get("/v1/stats", summary="View Enterprise Usage Analytics")
def get_stats():
    if not os.path.exists(AUDIT_LOG_FILE):
        return {"total_inspections": 0, "synthetic_detected": 0, "authentic_human": 0}
    try:
        with open(AUDIT_LOG_FILE, "r") as f:
            logs = json.load(f)
        synthetic_count = sum(1 for entry in logs if entry.get("verdict") == "SYNTHETIC_DETECTED")
        human_count = sum(1 for entry in logs if entry.get("verdict") == "AUTHENTIC_HUMAN")
        return {
            "total_inspections": len(logs),
            "synthetic_detected": synthetic_count,
            "authentic_human": human_count,
            "recent_audit_trail": logs[-10:]
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/v1/verify", summary="Verify Audio Stream Authenticity")
async def verify_audio(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    result = guard.verify(temp_path)
    
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    if "verdict" in result:
        log_verification(file.filename, result["verdict"], result.get("confidence_score", 0.0))
        
    return result

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
