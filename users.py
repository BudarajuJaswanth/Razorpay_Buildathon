import json
import os
import uuid
import hashlib
import smtplib
from email.mime.text import MIMEText
from typing import Dict, Optional

USERS_FILE = "users.json"
EMAILS_LOG_FILE = "verification_emails.log"

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

def load_users() -> Dict:
    if not os.path.exists(USERS_FILE):
        return {"users": {}}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}

def save_users(data: Dict):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[users] Failed to save users: {e}")

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

def send_verification_email(email: str, name: str, token: str):
    verify_url = f"http://127.0.0.1:8000/api/auth/verify?token={token}&email={email}"
    subject = "Verify your KicksVault account"
    body = f"""Hi {name},

Thank you for signing up for KicksVault India. Please click the link below to verify your email address:
{verify_url}

If you did not sign up, please ignore this email.

Best regards,
KicksVault India Security Team
"""
    # Write to local log for easy user retrieval (even if offline or SMTP is unconfigured)
    try:
        with open(EMAILS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"--- VERIFICATION EMAIL TO: {email} ---\nSubject: {subject}\nBody:\n{body}\n---------------------------------------\n\n")
    except Exception as e:
         print(f"[WARN] Failed to write verification email to log file: {e}")

    # Print to console for immediate visibility
    print(f"\n=======================================================")
    print(f"[EMAIL] VERIFICATION EMAIL SENT TO: {email}")
    print(f"[LINK] CLICK TO VERIFY: {verify_url}")
    print(f"=======================================================\n")

    # Optional real SMTP sending if configured in environment
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    
    if smtp_host and smtp_port and smtp_user and smtp_pass:
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = smtp_user
            msg['To'] = email
            
            with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [email], msg.as_string())
            print(f"[SMTP] Real email successfully sent to {email}")
        except Exception as e:
            print(f"[SMTP WARN] Real SMTP sending failed (link is still available in terminal & logs): {e}")

# Initialize at startup
init_users_db()
