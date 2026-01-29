import sys
import asyncio
from playwright.async_api import async_playwright

# Usage: python capture_assets.py "login_flow" "http://localhost:3000"

async def capture(flow_name, url):
    async with async_playwright() as p:
        # Launch browser (headless=True for CI, False to watch it)
        browser = await p.chromium.launch()
        context = await browser.new_context(record_video_dir=f"docs/assets/videos/{flow_name}")
        page = await context.new_page()

        print(f"Starting capture for: {flow_name} at {url}")
        
        # 1. Navigate
        try:
            await page.goto(url, timeout=5000)
        except Exception as e:
            print(f"Failed to reach {url} (Server likely offline). Skipping capture.")
            await context.close()
            await browser.close()
            return

        # 2. Heuristic Actions
        if "login" in flow_name:
            await page.screenshot(path=f"docs/assets/screenshots/{flow_name}_step1_blank.png")
            
            # Fill fake creds
            if await page.query_selector("input[type=email]"):
                await page.fill("input[type=email]", "demo@sigmaconnected.co.uk")
                await page.fill("input[type=password]", "password123")
                await page.screenshot(path=f"docs/assets/screenshots/{flow_name}_step2_filled.png")
                
                # Click Login
                await page.click("button[type=submit]")
                try:
                    await page.wait_for_load_state("networkidle", timeout=2000)
                except: pass
                
            await page.screenshot(path=f"docs/assets/screenshots/{flow_name}_step3_dashboard.png")

        # 3. Save Video/GIF
        await context.close() 
        print(f"Done: Assets saved to docs/assets/screenshots/ and docs/assets/videos/{flow_name}")
        await browser.close()

if __name__ == "__main__":
    flow = sys.argv[1] if len(sys.argv) > 1 else "default_flow"
    target_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5173" # Vite default
    
    asyncio.run(capture(flow, target_url))