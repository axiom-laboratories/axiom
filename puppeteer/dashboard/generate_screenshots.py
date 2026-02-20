import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Ensure directories exist
        os.makedirs("docs/assets/screenshots", exist_ok=True)
        
        url = "http://localhost:5174"
        print(f"Navigating to {url}...")
        await page.goto(url)
        await asyncio.sleep(2)  # Wait for animation
        
        # Screenshot Login
        await page.screenshot(path="docs/assets/screenshots/login_page.png")
        print("Saved login_page.png")
        
        # Bypass Login
        await page.evaluate("""() => {
            localStorage.setItem('token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsIm5hbWUiOiJBZG1pbiBVc2VyIiwicm9sZSI6ImFkbWluIiwiZXhwIjoyNTI0NjA4MDAwfQ.dummy');
        }""")
        
        await page.goto(f"{url}/")
        print("Waiting for dashboard...")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        
        # Dashboard
        await page.screenshot(path="docs/assets/screenshots/dashboard_view.png")
        print("Saved dashboard_view.png")
        
        # Navigate to Nodes
        await page.click("a:has-text('Puppets')")
        await asyncio.sleep(1)
        await page.screenshot(path="docs/assets/screenshots/nodes_view.png")
        print("Saved nodes_view.png")

        # Navigate to Jobs
        await page.click("a:has-text('Orchestration')")
        await asyncio.sleep(1)
        await page.screenshot(path="docs/assets/screenshots/jobs_view.png")
        print("Saved jobs_view.png")

        # Navigate to Signatures
        await page.click("a:has-text('Trust Assets')")
        await asyncio.sleep(1)
        await page.screenshot(path="docs/assets/screenshots/signatures_view.png")
        print("Saved signatures_view.png")

        # Navigate to Admin
        await page.click("a:has-text('Settings')")
        await asyncio.sleep(1)
        await page.screenshot(path="docs/assets/screenshots/admin_view.png")
        print("Saved admin_view.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
