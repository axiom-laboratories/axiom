import os

def find_missing():
    source_files = set()
    test_files = set()

    # 1. Map Files
    for root, dirs, files in os.walk("."):
        if "venv" in root or "node_modules" in root: continue
        for file in files:
            if file.endswith(".py"):
                if file.startswith("test_") or "tests/" in root:
                    test_files.add(file)
                else:
                    source_files.add(os.path.join(root, file))

    # 2. Compare
    print("--- UNTESTED FILES ---")
    for src in source_files:
        filename = os.path.basename(src)
        expected_test = f"test_{filename}"
        if expected_test not in test_files and filename != "__init__.py":
            print(f"Missing: tests/{expected_test} (for {src})")

if __name__ == "__main__":
    find_missing()