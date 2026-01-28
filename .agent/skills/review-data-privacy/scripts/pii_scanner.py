import os
import re

def scan_file(filepath):
    issues = []
    # Regex patterns for UK/Global PII
    patterns = {
        'uk_nino': re.compile(r'\b[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\s?[0-9]{2}\s?[0-9]{2}\s?[0-9]{2}\s?[A-D]\b', re.IGNORECASE),
        'uk_sort_code': re.compile(r'\b\d{2}-\d{2}-\d{2}\b'),
        'credit_card': re.compile(r'\b(?:\d[ -]*?){13,16}\b'),
        'email_list': re.compile(r'([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+,\s*){2,}') # List of multiple emails
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if len(line) > 500: continue # Skip minified code/assets
                
                for key, pattern in patterns.items():
                    if pattern.search(line):
                        msg = f"Potential {key.upper().replace('_', ' ')} detected."
                        # Exclude obvious placeholders
                        if "example" in line.lower() or "test" in line.lower() or "0000" in line:
                            continue 
                        issues.append(f"Line {i+1}: {msg}")

        if issues:
            print(f"--- PRIVACY ALERT: {filepath} ---")
            for issue in issues:
                print(f"   - {issue}")

    except Exception:
        pass

def main():
    print("Scanning for PII Leaks...")
    for root, dirs, files in os.walk("."):
        if "node_modules" in root or ".git" in root: continue
        for file in files:
            if file.endswith((".py", ".ts", ".tsx", ".sql", ".json", ".csv")):
                scan_file(os.path.join(root, file))

if __name__ == "__main__":
    main()