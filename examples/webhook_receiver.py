import hmac
import hashlib
import json
from fastapi import FastAPI, Request, HTTPException, Header
from typing import Optional

app = FastAPI(title="MOP Webhook Receiver Reference")

# In a real app, load this from environment variables or a database
WEBHOOK_SECRET = "whsec_your_secret_here"

def verify_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """
    Verifies that the webhook payload matches the signature sent by Master of Puppets.
    """
    if not signature_header.startswith("sha256="):
        return False
    
    received_sig = signature_header.replace("sha256=", "")
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(received_sig, expected_sig)

@app.post("/webhook")
async def handle_mop_event(
    request: Request,
    x_mop_signature: Optional[str] = Header(None)
):
    # 1. Read raw body for signature verification
    payload_bytes = await request.body()
    
    # 2. Verify Signature
    if not x_mop_signature or not verify_signature(payload_bytes, x_mop_signature, WEBHOOK_SECRET):
        print("❌ Invalid or missing signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 3. Parse JSON
    try:
        data = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 4. Process Event
    event_type = data.get("event")
    event_data = data.get("data", {})
    
    print(f"🔔 Received MOP Event: {event_type}")
    
    if event_type == "alert:new":
        print(f"⚠️ ALERT [{event_data.get('severity')}]: {event_data.get('message')}")
    
    elif event_type == "job:completed":
        print(f"✅ JOB FINISHED: {event_data.get('guid')} (Exit Code: {event_data.get('exit_code')})")
        
    elif event_type == "job:failed" or event_type == "job:dead_letter":
        print(f"❌ JOB FAILED: {event_data.get('guid')} status is now {event_data.get('status')}")

    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 MOP Webhook Receiver starting on http://0.0.0.0:9000")
    print("Tip: Use 'ngrok http 9000' or similar to test with a public URL")
    uvicorn.run(app, host="0.0.0.0", port=9000)
