import os

def scan_file(filepath):
    issues = []
    has_assert = False
    is_test_file = False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Heuristics
    if "def test_" in content or "test(" in content or "it(" in content:
        is_test_file = True
        
    if not is_test_file: return

    # Check for assertions
    if "assert " in content or "expect(" in content:
        has_assert = True
        
    if not has_assert:
        issues.append("File contains tests but ZERO assertions/expectations found.")
    
    if "@pytest.mark.skip" in content or ".skip(" in content:
        issues.append("Contains SKIPPED tests. Verify if these should be enabled.")

    if issues:
        print(f"--- QA SCAN: {filepath} ---")
        for issue in issues:
            print(f"   - {issue}")

def main():
    print("Scanning Test Suite...")
    
    # Paths to scan: Current repo AND the validation repo (tests & scripts)
    search_paths = [".", "../mop_validation/tests", "../mop_validation/scripts"]
    
    for base_path in search_paths:
        if not os.path.exists(base_path):
            print(f"Build Warning: Test path '{base_path}' not found.")
            continue
            
        print(f"Scanning directory: {base_path}")
        for root, dirs, files in os.walk(base_path):
            if "node_modules" in root: continue
            if ".git" in root: continue
            
            for file in files:
                if "test" in file.lower() or "spec" in file.lower():
                    scan_file(os.path.join(root, file))

if __name__ == "__main__":
    main()