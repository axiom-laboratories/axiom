import os
import re

def scan_codebase():
    frontend_calls = []
    backend_routes = []

    print("--- SCANNING STACK ALIGNMENT ---")

    # 1. SCAN FRONTEND (Look for API calls)
    # Regex logic: Look for strings that look like API paths
    # Matches: "/api/users", "/nodes", "/jobs"
    fe_pattern = re.compile(r'["\'](/[a-zA-Z0-9_/-]+)["\']')
    
    for root, dirs, files in os.walk("."):
        if "node_modules" in root or "venv" in root: continue
        
        for file in files:
            path = os.path.join(root, file)
            
            # Frontend Scan
            if file.endswith((".tsx", ".ts", ".js")):
                with open(path, 'r', errors='ignore') as f:
                    content = f.read()
                    matches = fe_pattern.findall(content)
                    for m in matches:
                        frontend_calls.append({"path": m, "file": file})

            # Backend Scan
            if file.endswith(".py"):
                with open(path, 'r', errors='ignore') as f:
                    content = f.read()
                    # Matches: @router.get("/users") or @app.post("/login")
                    routes = re.findall(r'@(?:router|app)\.(get|post|put|delete|patch)\(["\'](.*?)["\']', content)
                    for method, route in routes:
                        # Normalise route: FastAPI often uses /users, but Frontend calls /api/users
                        # We assume a prefix mapping might be needed, or we just store the raw suffix
                        backend_routes.append(route)

    # 2. COMPARE
    # Simple normalization: specific to your project (e.g., if FastAPI uses APIRouter(prefix="/api"))
    # We will try to match loosely to be helpful.
    
    missing_endpoints = []
    
    print(f"Found {len(frontend_calls)} Frontend calls and {len(backend_routes)} Backend routes.")
    
    for call in frontend_calls:
        found = False
        api_path = call["path"] # e.g., /api/users/123
        
        # Check against all backend routes
        for route in backend_routes:
            # 1. Exact Match
            if route == api_path: 
                found = True
            # 2. Prefix Match (FastAPI router prefix logic)
            # If backend route is "/users" and frontend is "/api/users", we assume a match if it ends with it
            elif route != "/" and (api_path == f"/api{route}" or api_path == route):
                found = True
            # 3. Path Param Match (Rough)
            # Backend: /users/{id} vs Frontend: /api/users/
            # This is hard to regex perfectly without complex parsing, so we skip for now
            
        if not found:
            missing_endpoints.append(call)

    # 3. REPORT
    if missing_endpoints:
        print("\n[MISSING BACKEND ENDPOINTS] (Frontend expects these):")
        unique_missing = {f"{x['path']} (in {x['file']})" for x in missing_endpoints}
        for m in sorted(unique_missing):
            print(f"   - {m}")
    else:
        print("\n[SUCCESS] Stack Integrity looks good. No obvious orphans.")

if __name__ == "__main__":
    scan_codebase()