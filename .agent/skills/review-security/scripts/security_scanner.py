import os
import re

def scan_file(filepath):
    issues = []
    
    # Regex for suspicious patterns
    patterns = {
        'api_key': re.compile(r'(?i)(api_key|secret|password|token)\s*=\s*["\'][a-zA-Z0-9_\-]{20,}["\']'),
        'dangerous_html': re.compile(r'dangerouslySetInnerHTML'),
        'sql_raw': re.compile(r'execute\(\s*f["\'].*\{.*\}'), # f-string inside execute()
        'no_auth_route': re.compile(r'@app\.(get|post|put|delete).*# TODO: Add auth', re.IGNORECASE)
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            for key, pattern in patterns.items():
                if pattern.search(line):
                    msg = ""
                    if key == 'api_key': msg = "POTENTIAL HARDCODED SECRET"
                    if key == 'dangerous_html': msg = "Use of dangerouslySetInnerHTML"
                    if key == 'sql_raw': msg = "Potential SQL Injection (f-string in execute)"
                    if key == 'no_auth_route': msg = "Route marked with TODO for Auth"
                    
                    if msg:
                        issues.append(f"Line {i+1}: {msg}")

        if issues:
            print(f"--- SECURITY ALERT: {filepath} ---")
            for issue in issues:
                print(f"   - {issue}")

    except Exception:
        pass # Ignore binary files or read errors

def main():
    print("Scanning for security vulnerabilities...")
    for root, dirs, files in os.walk("."):
        if "node_modules" in root or ".git" in root:
            continue
        for file in files:
            if file.endswith((".py", ".tsx", ".ts", ".js")):
                scan_file(os.path.join(root, file))

if __name__ == "__main__":
    main()