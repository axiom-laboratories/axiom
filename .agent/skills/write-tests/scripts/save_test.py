import sys
import os

# Usage: python save_test.py "mop_validation/tests/test_auth.py" "import pytest..."

def save_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Saved test file to: {path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Error: Missing arguments. Usage: python save_test.py <path> <content>")
    else:
        save_file(sys.argv[1], sys.argv[2])