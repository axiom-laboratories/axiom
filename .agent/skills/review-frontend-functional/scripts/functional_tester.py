import sys
import asyncio
from playwright.async_api import async_playwright

# Usage: python functional_tester.py "http://localhost:5173"
# Note: Ensure your React App and FastAPI server are running!

async def test_page(url):
    report = {
        "js_errors": [],
        "network_errors": [],
        "interactions": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # 1. Listener: Catch Console Errors
        page.on("console", lambda msg: report["js_errors"].append(f"{msg.type}: {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: report["js_errors"].append(f"Exception: {exc}"))

        # 2. Listener: Catch Network Errors (The "Missing Backend" detector)
        def handle_response(response):
            if response.status >= 400:
                report["network_errors"].append(
                    f"{response.request.method} {response.url} -> {response.status} {response.status_text}"
                )
        page.on("response", handle_response)

        try:
            print(f"[TESTING] Visiting {url}...")
            await page.goto(url, wait_until="networkidle")

            # 3. Provocateur: Find and click buttons to trigger calls
            # We look for common interactive elements
            buttons = await page.query_selector_all("button:not([disabled])")
            
            # Limit interaction to first 5 buttons to avoid infinite loops/logging out
            for i, btn in enumerate(buttons[:5]):
                txt = await btn.inner_text()
                # Skip navigation buttons usually
                if not txt: txt = "Icon Button"
                
                print(f"   [ACTION] Clicking button: '{txt.strip()}'")
                try:
                    await btn.click(timeout=1000)
                    # Small wait for network reaction
                    await page.wait_for_timeout(500)
                except Exception:
                    pass # Ignore unclickable or covered buttons

        except Exception as e:
            report["js_errors"].append(f"Navigation failed: {str(e)}")

        await browser.close()

    # 4. Print Report for the Agent
    print("\n--- INTERACTION REPORT ---")
    
    if not report["js_errors"] and not report["network_errors"]:
        print("[SUCCESS] No obvious errors detected.")
    
    if report["network_errors"]:
        print("\n[NETWORK ERRORS] BACKEND / NETWORK GAPS:")
        for err in report["network_errors"]:
            print(f"   [ERROR] {err}")
            if "404" in err:
                print("      -> PROBABLE CAUSE: Endpoint missing in FastAPI.")
            if "500" in err:
                print("      -> PROBABLE CAUSE: Server crash/Exception.")

    if report["js_errors"]:
        print("\n[JS ERRORS] FRONTEND / JS CRASHES:")
        for err in report["js_errors"]:
            print(f"   [WARNING] {err}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
    asyncio.run(test_page(target))