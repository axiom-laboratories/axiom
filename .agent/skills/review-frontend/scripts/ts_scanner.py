import os
import re

def scan_file(filepath):
    issues = []
    line_count = 0
    
    # Regex patterns for common issues
    patterns = {
        'console_log': re.compile(r'console\.log\('),
        'explicit_any': re.compile(r':\s*any\b|as\s+any\b'),
        'inline_style': re.compile(r'style=\{\{'),
        'use_effect': re.compile(r'useEffect\('), # Trigger for agent to check dependency logic
        'hardcoded_px': re.compile(r'-\[\d+px\]') # Detect arbitrary tailwind values like w-[50px]
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            line_count = len(lines)

        # 1. Check File Size
        if line_count > 250:
            issues.append(f"File too long ({line_count} lines). Consider splitting component.")

        # 2. Scan Lines
        for i, line in enumerate(lines):
            for key, pattern in patterns.items():
                if pattern.search(line):
                    msg = ""
                    if key == 'console_log': msg = "Leftover console.log detected."
                    if key == 'explicit_any': msg = "Usage of 'any' type detected."
                    if key == 'inline_style': msg = "Inline style detected. Prefer Tailwind classes."
                    if key == 'hardcoded_px': msg = "Arbitrary Tailwind value detected."
                    
                    if msg:
                        issues.append(f"Line {i+1}: {msg}")

        if issues:
            print(f"--- Analysis: {filepath} ---")
            for issue in issues:
                print(f"   - {issue}")

    except Exception as e:
        print(f"Error scanning {filepath}: {e}")

def main():
    print("Scanning .tsx and .ts files for strict compliance...")
    for root, dirs, files in os.walk("."):
        if "node_modules" in root or ".git" in root:
            continue
            
        for file in files:
            if file.endswith(".tsx") or file.endswith(".ts"):
                scan_file(os.path.join(root, file))

if __name__ == "__main__":
    main()