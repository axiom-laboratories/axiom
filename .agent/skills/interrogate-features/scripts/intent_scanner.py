import ast
import os

def scan_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
    
    print(f"\n--- FILE: {filepath} ---")
    
    # 1. Module Docstring (High Level Intent)
    docstring = ast.get_docstring(tree)
    if docstring:
        print(f"[DOC] MODULE INTENT: {docstring.strip().splitlines()[0]}")

    for node in ast.walk(tree):
        # 2. API Routes (FastAPI)
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    # e.g. @router.post("/login")
                    if dec.func.attr in ['get', 'post', 'put', 'delete']:
                        route = dec.args[0].value if dec.args else "?"
                        print(f"[API] ROUTE: {dec.func.attr.upper()} {route} -> '{node.name}'")
                        if ast.get_docstring(node):
                            print(f"   Ref: {ast.get_docstring(node).strip().splitlines()[0]}")

        # 3. Data Models (Pydantic/SQLAlchemy)
        if isinstance(node, ast.ClassDef):
            # Heuristic: Classes that inherit from something usually define data
            print(f"[MODEL] MODEL: {node.name}")
            if ast.get_docstring(node):
                 print(f"   Desc: {ast.get_docstring(node).strip().splitlines()[0]}")

def main():
    for root, dirs, files in os.walk("."):
        if "venv" in root or "node_modules" in root: continue
        for file in files:
            if file.endswith(".py"):
                scan_file(os.path.join(root, file))

if __name__ == "__main__":
    main()