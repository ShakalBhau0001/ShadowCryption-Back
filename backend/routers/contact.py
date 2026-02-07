from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
import smtplib, json, traceback
from email.message import EmailMessage
from datetime import datetime
import os

router = APIRouter(prefix="/api", tags=["contact"])

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
CONTACT_TO = os.getenv("CONTACT_TO", SMTP_USER)
CONTACT_LOG_PATH = os.getenv("CONTACT_LOG_PATH", "contact_messages.jsonl")


def persist_contact_message(name, email_from, message_text):
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "name": name,
        "email": email_from,
        "message": message_text,
    }
    try:
        with open(CONTACT_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print("Failed to persist contact message:", e)


def send_contact_email(name, email_from, message_text):
    msg = EmailMessage()
    msg["Subject"] = f"ShadowCryption Contact — {name}"
    msg["From"] = SMTP_USER
    msg["To"] = CONTACT_TO
    body = f"New contact form submission\n\nTime (UTC): {datetime.utcnow().isoformat()}Z\nName: {name}\nEmail: {email_from}\n\nMessage:\n{message_text}\n"
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
        s.ehlo()
        if SMTP_PORT == 587:
            s.starttls()
            s.ehlo()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)


@router.post("/contact")
def api_contact(
    name: str = Form(...), email: str = Form(...), message: str = Form(...)
):
    if not name or not email or not message:
        raise HTTPException(
            status_code=400, detail="name, email and message are required"
        )
    try:
        send_contact_email(name, email, message)
    except Exception:
        traceback.print_exc()
        persist_contact_message(name, email, message)
        raise HTTPException(
            status_code=500, detail="Failed to send message; saved for later"
        )
    return JSONResponse({"status": "ok", "message": "Sent. Thank you."})
