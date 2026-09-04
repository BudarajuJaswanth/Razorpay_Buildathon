import json
import os
import uuid
import hashlib
from typing import Dict, Optional, Set

USERS_FILE = "users.json"

ADMIN_EMAILS: Set[str] = {
    e.strip().lower() 
    for e in os.getenv("ADMIN_EMAILS", "admin@kicksvault.in,merchant@kicksvault.in,chand@kicksvault.in,jashubudaraju@gmail.com").split(",") 
    if e.strip()
}

def is_admin_email(email: str) -> bool:
    clean = (email or "").strip().lower()
    if clean in ADMIN_EMAILS or clean.startswith("admin@") or clean.startswith("merchant@") or clean == "jashubudaraju@gmail.com":
        return True
    return False

def determine_role(email: str) -> str:
    return "admin" if is_admin_email(email) else "user"

def hash_password(password: str, salt: Optional[str] = None) -> str:
    if not salt:
        salt = uuid.uuid4().hex[:16]
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{pwd_hash}"

def verify_password(password: str, hashed_value: str) -> bool:
    if ":" not in hashed_value:
        return False
    salt, hash_part = hashed_value.split(":", 1)
    return hash_password(password, salt) == hashed_value

import supabase_db

def load_users() -> Dict:
    local_data = {"users": {}}
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                local_data = json.load(f)
        except Exception:
            local_data = {"users": {}}

    remote_users = supabase_db.fetch_users_from_supabase()
    if remote_users:
        local_data["users"].update(remote_users)

    return local_data

def save_users(data: Dict):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[users] Failed to save users: {e}")

    for email, user in data.get("users", {}).items():
        supabase_db.save_user_to_supabase(
            email=email,
            name=user.get("name", ""),
            password_hash=user.get("password_hash", ""),
            role=user.get("role", "user"),
            verified=user.get("verified", True),
            verification_token=user.get("verification_token", ""),
            avatar=user.get("avatar", "")
        )

# Preseed default buyer and admin accounts as pre-verified
def init_users_db():
    data = load_users()
    changed = False
    
    # Preseed Admin
    admin_email = "admin@kicksvault.in"
    if admin_email not in data["users"]:
        data["users"][admin_email] = {
            "name": "Merchant Administrator",
            "password_hash": hash_password("admin123"),
            "role": "admin",
            "verified": True,
            "verification_token": "",
            "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80"
        }
        changed = True

    # Preseed Admin Jashu Budaraju
    jashu_email = "jashubudaraju@gmail.com"
    if jashu_email not in data["users"] or not verify_password("Jayaram@2006", data["users"][jashu_email].get("password_hash", "")):
        data["users"][jashu_email] = {
            "name": "Jashu Budaraju (Admin)",
            "password_hash": hash_password("Jayaram@2006"),
            "role": "admin",
            "verified": True,
            "verification_token": "",
            "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80"
        }
        changed = True
        
    # Preseed Collector
    user_email = "collector@kicksvault.in"
    if user_email not in data["users"]:
        data["users"][user_email] = {
            "name": "Verified Collector",
            "password_hash": hash_password("collector123"),
            "role": "user",
            "verified": True,
            "verification_token": "",
            "avatar": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=200&q=80"
        }
        changed = True
        
    if changed:
        save_users(data)

# Initialize at startup
init_users_db()
