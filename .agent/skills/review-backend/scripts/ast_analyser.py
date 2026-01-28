import ast
import os
import sys

class BackendAnalyser(ast.NodeVisitor):
    def __init__(self, filepath):
        self.filepath = filepath
        self.issues = []
        self.in_async_func = False
        self.current_func_name = None

    def visit_AsyncFunctionDef(self, node):
        self.in_async_func = True
        self.current_func_name = node.name
        
        # Check for excessive length (complexity proxy)
        func_length = node.end_lineno - node.lineno
        if func_length > 50:
            self.issues.append(f"Logic: Async function '{node.name}' is too long ({func_length} lines). Breakdown suggested.")

        self.generic_visit(node)
        self.in_async_func = False
        self.current_func_name = None

    def visit_Call(self, node):
        # Only check for blocking calls if we are currently inside an async function
        if self.in_async_func:
            blocking_patterns = {
                'time.sleep': 'Blocking sleep detected. Use asyncio.sleep().',
                'requests.get': 'Blocking HTTP call. Use httpx.AsyncClient.',
                'requests.post': 'Blocking HTTP call. Use httpx.AsyncClient.',
                'urllib.request': 'Blocking network call detected.'
            }
            
            # Helper to get the full name of the function being called (e.g. "time.sleep")
            func_name = self._get_func_name(node.func)
            
            if func_name in blocking_patterns:
                self.issues.append(f"Perf: {blocking_patterns[func_name]} in '{self.current_func_name}' at line {node.lineno}")

        self.generic_visit(node)

    def visit_Assign(self, node):
        # Check for Global Session instantiation (a common SQLAlchemy anti-pattern)
        # e.g., session = SessionLocal() at module level (indentation 0)
        if hasattr(node, 'col_offset') and node.col_offset == 0:
            if isinstance(node.value, ast.Call):
                func_name = self._get_func_name(node.value.func)
                if func_name in ['SessionLocal', 'sessionmaker']:
                    self.issues.append(f"Architecture: Global DB Session detected at line {node.lineno}. Use Dependency Injection.")
        
        self.generic_visit(node)

    def _get_func_name(self, node):
        """Recursively resolve function names like module.submodule.func"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_func_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        return None

def analyse_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as source:
            tree = ast.parse(source.read())
            
        analyser = BackendAnalyser(filepath)
        analyser.visit(tree)
        
        if analyser.issues:
            print(f"--- Analysis: {filepath} ---")
            for issue in analyser.issues:
                # Add emoji based on category
                prefix = "⚠️ " if "Perf" in issue else "ℹ️ "
                print(f"   {prefix} {issue}")
                        
    except Exception as e:
        # Silently fail on syntax errors in the user code to avoid crashing the tool
        pass

def main():
    print("Scanning Backend Logic & Performance...")
    # Walk the directory
    for root, dirs, files in os.walk("."):
        # Ignore common non-source directories
        if any(ignore in root for ignore in ["venv", "__pycache__", ".git", "node_modules"]):
            continue
            
        for file in files:
            if file.endswith(".py"):
                analyse_file(os.path.join(root, file))

if __name__ == "__main__":
    main()