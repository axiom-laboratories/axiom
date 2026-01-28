import os
import re

def scan_file(filepath):
    issues = []
    
    # Regex patterns for common accessibility failures
    patterns = {
        'img_no_alt': re.compile(r'<img(?!.*alt=)[^>]*>'),
        'clickable_div': re.compile(r'<div[^>]*onClick=[^>]*>'),
        'empty_button': re.compile(r'<button[^>]*>\s*<'), # Button immediately opening a tag (likely icon) with no text
        'bad_tabindex': re.compile(r'tabIndex\s*=\s*["\']?[1-9]["\']?'), # Positive tabindex is an anti-pattern
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            for key, pattern in patterns.items():
                if pattern.search(line):
                    msg = ""
                    if key == 'img_no_alt': msg = "Image missing 'alt' attribute."
                    if key == 'clickable_div': msg = "Div with onClick (non-semantic). Use <button>."
                    if key == 'empty_button': msg = "Potential empty button (icon only?). Needs aria-label."
                    if key == 'bad_tabindex': msg = "Avoid positive tabIndex. Use 0 or -1."
                    
                    if msg:
                        issues.append(f"Line {i+1}: {msg}")

        if issues:
            print(f"--- A11Y REPORT: {filepath} ---")
            for issue in issues:
                print(f"   - {issue}")

    except Exception:
        pass

def main():
    print("Scanning for Accessibility barriers...")
    for root, dirs, files in os.walk("."):
        if "node_modules" in root: continue
        for file in files:
            if file.endswith((".tsx", ".jsx", ".html")):
                scan_file(os.path.join(root, file))

if __name__ == "__main__":
    main()