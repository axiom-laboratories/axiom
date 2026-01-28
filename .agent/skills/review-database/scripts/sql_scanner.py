import os
import re

def scan_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    issues = []
    
    # Define rules per dialect/extension
    rules = {
        'common': [
            (r'DROP TABLE', "Destructive DDL: DROP TABLE detected."),
            (r'TRUNCATE TABLE', "Destructive DDL: TRUNCATE TABLE detected."),
            (r'SELECT \*', "Select All detected. Specify columns for performance.")
        ],
        '.sql': [ # General SQL (assume T-SQL/PG mixed)
            (r'VARCHAR\(MAX\)', "T-SQL: Avoid MAX length types for indexing."),
            (r'NVARCHAR\(MAX\)', "T-SQL: Avoid MAX length types for indexing."),
            (r'SERIAL', "Postgres: Prefer 'GENERATED ALWAYS AS IDENTITY'.")
        ],
        '.py': [ # PySpark / Python
            (r'\.collect\(\)', "Spark: .collect() pulls data to driver. Use .take() or write to disk.")
        ]
    }

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check Common Rules
        for pattern, msg in rules['common']:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"Global: {msg}")

        # Check Specific Rules
        if ext in rules:
            for pattern, msg in rules[ext]:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(f"Dialect: {msg}")
                    
        # Spark specific check in python files
        if ext == '.py' and ('pyspark' in content or 'spark.' in content):
             if re.search(r'\.collect\(\)', content):
                 issues.append("Spark: Dangerous .collect() detected.")

        if issues:
            print(f"--- DB REPORT: {filepath} ---")
            for issue in issues:
                print(f"   - {issue}")

    except Exception:
        pass

def main():
    print("Scanning Database Migrations & Scripts...")
    for root, dirs, files in os.walk("."):
        if "node_modules" in root or "venv" in root: continue
        for file in files:
            if file.endswith((".sql", ".hql", ".py")):
                scan_file(os.path.join(root, file))

if __name__ == "__main__":
    main()