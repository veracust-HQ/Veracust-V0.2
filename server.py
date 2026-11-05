from fastapi import FastAPI, UploadFile, File, Header, HTTPException, status
import shutil
import os
import json
import secrets
from datetime import datetime
from voice_guard import VeracustEngine

app = FastAPI(
    title="VERACUST Enterprise Gateway",
    description="Deterministic Acoustic Authenticity Protocol | Engineered by Utkarsh Dixit (Founder & Lead Systems Engineer)",
    version="3.1.0"
)

guard = VeracustEngine()

# Persistent Local Databases (Zero-cost JSON storage)
DB_USERS_FILE = "users_db.json"
AUDIT_LOG_FILE = "audit_log.json"

# =====================================================================
# YOUR MASTER ADMIN KEY (Unlimited Access Forever)
# Replace this string with any secret master password you want!
# =====================================================================
MASTER_ADMIN_KEY = "veracust_master_utkarsh_unlimited_2026"

def load_users():
    if not os.path.exists(DB_USERS_FILE):
        # Initialize with Admin Key
        initial_db = {
            MASTER_ADMIN_KEY: {
                "owner": "Utkarsh Dixit (Founder)",
                "tokens_remaining": 999999999,
                "tier": "UNLIMITED_MASTER_ADMIN"
            }
        }
        with open(DB_USERS_FILE, "w") as f:
            json.dump(initial_db, f, indent=4)
        return initial_db
    try:
        with open(DB_USERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users_db):
    with open(DB_USERS_FILE, "w") as f:
        json.dump(users_db, f, indent=4)

def log_verification(filename: str, verdict: str, confidence: float, user_email: str):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "file_name": filename,
        "verdict": verdict,
        "confidence": confidence,
        "account": user_email
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
    users = load_users()
    return {
        "status": "online",
        "engine": "VERACUST-Core-v3.1",
        "architect": "Utkarsh Dixit",
        "registered_accounts": len(users)
    }

@app.post("/v1/auth/register", summary="Register & Get 10 Free Testing Tokens")
def register_account(name: str, company_email: str):
    """Generates an Enterprise Sandbox API Key with 10 free test tokens."""
    users = load_users()
    
    # Check if email already registered
    for key, data in users.items():
        if data.get("email") == company_email:
            return {
                "message": "Account already exists for this email.",
                "api_key": key,
                "tokens_remaining": data.get("tokens_remaining")
            }
            
    # Generate secure 24-character hex key
    new_api_key = f"veracust_sb_{secrets.token_hex(12)}"
    
    users[new_api_key] = {
        "owner": name,
        "email": company_email,
        "tokens_remaining": 10,
        "tier": "FREE_SANDBOX_TIER",
        "registered_at": datetime.utcnow().isoformat() + "Z"
    }
    save_users(users)
    
    return {
        "message": "Account created successfully. Keep your API key private.",
        "api_key": new_api_key,
        "tokens_remaining": 10,
        "instructions": "Pass this key in the 'x_api_key' header when calling /v1/verify"
    }

@app.post("/v1/verify", summary="Verify Audio Stream (Requires API Key Header)")
async def verify_audio(file: UploadFile = File(...), x_api_key: str = Header(..., description="Your Veracust API Key")):
    users = load_users()
    
    # 1. AUTHENTICATION CHECK
    if x_api_key not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key. Register at /v1/auth/register to get 10 free testing tokens."
        )
        
    user_data = users[x_api_key]
    
    # 2. TOKEN USAGE & BILLING GATE
    if user_data.get("tokens_remaining", 0) <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Free Sandbox tokens exhausted (0 remaining). Contact enterprise@veracust.com to upgrade to an Enterprise Tier."
        )
        
    # Deduct 1 token (Admins don't decrease)
    if x_api_key != MASTER_ADMIN_KEY:
        user_data["tokens_remaining"] -= 1
        save_users(users)

    # 3. RUN VERIFICATION ENGINE
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    result = guard.verify(temp_path)
    
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    # Append usage telemetry to response
    result["account_info"] = {
        "tier": user_data.get("tier"),
        "tokens_remaining": user_data.get("tokens_remaining")
    }
    
    if "verdict" in result:
        log_verification(file.filename, result["verdict"], result.get("confidence_score", 0.0), user_data.get("owner"))
        
    return result

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
