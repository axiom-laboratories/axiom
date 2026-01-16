import httpx
import asyncio
import json
import time

MODEL_URL = "https://localhost:8000"
AGENT_URL = "https://localhost:8001"
API_KEY = "master-secret-key"

async def verify():
    headers = {"X-API-KEY": API_KEY}
    client = httpx.AsyncClient(verify=False, timeout=10.0)
    
    print("--- 1. Creating Schedule ---")
    try:
        resp = await client.post(
            f"{MODEL_URL}/schedules",
            json={
                "name": "Backend Test Schedule",
                "task_type": "python_script", 
                "interval_seconds": 5,
                "payload": {
                    "script_content": "print('Scheduled Job Executed')",
                    "requirements": []
                }
            },
            headers=headers
        )
        print(f"Create Resp: {resp.status_code} - {resp.text}")
        if resp.status_code != 200:
            return
        job_id = resp.json()["id"]
        print(f"Schedule ID: {job_id}")
    except Exception as e:
        print(f"FAIL: {e}")
        return

    print("--- 2. Waiting for Execution (10s) ---")
    await asyncio.sleep(10)
    
    print("--- 3. Checking Jobs on Agent ---")
    try:
        resp = await client.get(f"{AGENT_URL}/jobs", headers=headers)
        jobs = resp.json()
        found = False
        for job in jobs[:5]:
            # Check payload for our script content
            if "Scheduled Job Executed" in str(job.get("payload")):
                print(f"PASS: Found executed job {job['guid']}")
                found = True
                break
        if not found:
            print("FAIL: No scheduled job found in Agent history.")
    except Exception as e:
        print(f"FAIL: {e}")

    print("--- 4. Deleting Schedule ---")
    try:
        resp = await client.delete(f"{MODEL_URL}/schedules/{job_id}", headers=headers)
        print(f"Delete Resp: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"FAIL: {e}")

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(verify())
