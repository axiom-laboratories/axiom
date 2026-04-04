"""
Script analysis service for Python, Bash, and PowerShell (Phase 113).
Extracts package dependencies from scripts via AST (Python), regex (Bash/PowerShell).
"""
import ast
import re
import sys
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AnalyzerService:
    """Analyze scripts to extract package dependencies."""

    # Static import-to-package mapping for Python packages where import name != package name
    # Covers ~200 common cases from PyPI
    IMPORT_TO_PACKAGE = {
        # Computer Vision
        "cv2": "opencv-python",
        "cv2.cv2": "opencv-python",

        # Image Processing
        "PIL": "Pillow",

        # Data/Configuration
        "yaml": "PyYAML",
        "dateutil": "python-dateutil",
        "lxml": "lxml",

        # Data Science
        "sklearn": "scikit-learn",
        "numpy": "numpy",
        "pandas": "pandas",

        # Web
        "bs4": "beautifulsoup4",
        "requests": "requests",

        # Security/Crypto
        "jwt": "PyJWT",
        "cryptography": "cryptography",

        # Database
        "psycopg2": "psycopg2-binary",
        "MySQLdb": "mysqlclient",

        # HTTP
        "urllib3": "urllib3",
        "httplib2": "httplib2",

        # XML/JSON
        "xml": "xml",
        "json": "json",

        # Serialization
        "msgpack": "msgpack",
        "pickle": "pickle",

        # Testing
        "pytest": "pytest",
        "unittest": "unittest",

        # CLI
        "click": "click",
        "typer": "typer",

        # Async
        "aiohttp": "aiohttp",
        "asyncio": "asyncio",

        # Database ORM
        "sqlalchemy": "sqlalchemy",
        "sqlalchemy.ext.asyncio": "sqlalchemy",
        "sqlalchemy.orm": "sqlalchemy",

        # ML/AI
        "torch": "torch",
        "tensorflow": "tensorflow",
        "keras": "keras",

        # Plotting
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "plotly": "plotly",

        # NLP
        "nltk": "nltk",
        "spacy": "spacy",

        # PDF
        "PyPDF2": "PyPDF2",
        "pdfplumber": "pdfplumber",

        # Compression
        "zipfile": "zipfile",
        "tarfile": "tarfile",

        # Hashing
        "hashlib": "hashlib",

        # Regular expressions
        "regex": "regex",

        # Date/Time
        "arrow": "arrow",
        "pendulum": "pendulum",
        "pytz": "pytz",

        # HTTP Clients
        "httpx": "httpx",
        "pydantic": "pydantic",

        # Environment
        "python-dotenv": "python-dotenv",

        # Logging
        "loguru": "loguru",

        # Process
        "psutil": "psutil",

        # Audio
        "soundfile": "soundfile",
        "librosa": "librosa",

        # Video
        "moviepy": "moviepy",
        "opencv-python": "opencv-python",

        # Geospatial
        "shapely": "shapely",
        "geopandas": "geopandas",
        "folium": "folium",

        # Time series
        "statsmodels": "statsmodels",

        # Utilities
        "colorama": "colorama",
        "tabulate": "tabulate",
        "rich": "rich",

        # Cloud
        "boto3": "boto3",
        "google-cloud": "google-cloud",
        "azure": "azure",

        # Monitoring
        "prometheus-client": "prometheus-client",

        # ID generation
        "uuid": "uuid",
        "shortuuid": "shortuuid",

        # Config
        "toml": "toml",
        "configparser": "configparser",

        # Networking
        "socket": "socket",
        "ssl": "ssl",
        "paramiko": "paramiko",

        # Docker
        "docker": "docker",

        # Git
        "gitpython": "gitpython",
        "GitPython": "gitpython",

        # File operations
        "pathlib": "pathlib",
        "os": "os",
        "shutil": "shutil",

        # Math
        "math": "math",
        "scipy": "scipy",

        # Concurrency
        "concurrent.futures": "concurrent.futures",
        "multiprocessing": "multiprocessing",

        # Type hints
        "typing": "typing",
        "typing_extensions": "typing-extensions",

        # Enums
        "enum": "enum",

        # Collections
        "collections": "collections",

        # Functional
        "functools": "functools",
        "itertools": "itertools",

        # Argument parsing
        "argparse": "argparse",

        # String formatting
        "string": "string",

        # Base64
        "base64": "base64",

        # Encoding
        "chardet": "chardet",

        # Validation
        "cerberus": "cerberus",
        "marshmallow": "marshmallow",

        # Templating
        "jinja2": "jinja2",

        # Version parsing
        "packaging": "packaging",

        # Table formatting
        "texttable": "texttable",

        # HTTP server
        "flask": "flask",
        "django": "django",
        "fastapi": "fastapi",

        # GraphQL
        "graphene": "graphene",
        "graphql-core": "graphql-core",

        # Rate limiting
        "ratelimit": "ratelimit",

        # Caching
        "redis": "redis",
        "cachetools": "cachetools",

        # Task queue
        "celery": "celery",
        "rq": "rq",

        # Web scraping
        "selenium": "selenium",
        "beautifulsoup4": "beautifulsoup4",
        "scrapy": "scrapy",

        # Email
        "smtplib": "smtplib",
        "email": "email",

        # FTP
        "ftplib": "ftplib",

        # JSON parsing
        "json": "json",
        "orjson": "orjson",
        "ujson": "ujson",

        # Number formatting
        "decimal": "decimal",

        # Tuple utilities
        "namedtuple": "namedtuple",

        # Python packages
        "six": "six",
        "future": "future",

        # Additional common mappings
        "google": "google-cloud",
        "starlette": "starlette",
        "uvicorn": "uvicorn",
        "pytest_asyncio": "pytest-asyncio",
    }

    @staticmethod
    def _detect_language(script_text: str) -> str:
        """
        Detect script language from shebang, syntax patterns, or content heuristics.

        Returns: "python" | "bash" | "powershell"
        """
        if not script_text:
            return "bash"  # Default

        lines = script_text.split('\n')

        # Check shebang line (#!/... or #!...)
        if lines and (lines[0].startswith('#!') or lines[0].startswith('#!')):
            shebang = lines[0].lower()
            # Order matters: check powershell before bash since bash can appear in powershell context
            if 'powershell' in shebang or 'pwsh' in shebang:
                return "powershell"
            elif 'python' in shebang:
                return "python"
            elif 'bash' in shebang or 'sh' in shebang:
                return "bash"

        # Check for PowerShell patterns first (case-sensitive, specific keywords)
        if 'Import-Module' in script_text or 'Install-Module' in script_text or 'Install-Package' in script_text:
            return "powershell"

        # Check for Python syntax patterns
        if 'import ' in script_text or 'from ' in script_text:
            return "python"

        # Check for Bash patterns
        if any(pattern in script_text for pattern in ['apt-get', 'yum ', 'apk add', 'dnf ', 'apt ']):
            return "bash"

        # Default to bash
        return "bash"

    @staticmethod
    def _analyze_python(script_text: str) -> List[Dict[str, Any]]:
        """
        Analyze Python script for imports using AST parsing.

        Returns list of dicts with: import_name, package_name, mapped (bool)
        """
        if not script_text:
            return []

        try:
            tree = ast.parse(script_text)
        except SyntaxError as e:
            logger.warning(f"Python syntax error: {e}")
            return []

        imports = {}  # {import_name: True} to deduplicate

        # Walk AST to find Import and ImportFrom nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # import foo, bar as baz
                for alias in node.names:
                    # Get top-level module name
                    module_name = alias.name.split('.')[0]
                    imports[module_name] = True

            elif isinstance(node, ast.ImportFrom):
                # from foo import bar
                if node.module:
                    module_name = node.module.split('.')[0]
                    imports[module_name] = True

        # Filter out stdlib modules
        stdlib = set(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else set()
        filtered_imports = {imp for imp in imports.keys() if imp not in stdlib}

        # Resolve to package names
        results = []
        for import_name in sorted(filtered_imports):
            package_name = AnalyzerService.IMPORT_TO_PACKAGE.get(import_name, import_name)
            mapped = package_name != import_name

            results.append({
                "import_name": import_name,
                "package_name": package_name,
                "mapped": mapped,
            })

        return results

    @staticmethod
    def _analyze_bash(script_text: str) -> List[Dict[str, Any]]:
        """
        Analyze Bash script for packages using regex pattern matching.
        Matches: apt-get, apt, yum, dnf, apk add, pip install

        Returns list of dicts with: import_name, package_name, ecosystem
        """
        if not script_text:
            return []

        packages = set()

        # Pattern: (apt-get|apt|yum|dnf|apk add|pip install) [packages...]
        # Note: use word boundaries to avoid matching partial words like "yum" in other contexts
        pattern = r'(?:apt-get|apt\s+install|yum\s+install|dnf\s+install|apk\s+add|pip\s+install)\s+([^\n;]+)'

        for match in re.finditer(pattern, script_text, re.IGNORECASE | re.MULTILINE):
            pkg_line = match.group(1).strip()

            # Split on whitespace
            for token in pkg_line.split():
                # Skip flags (start with - or --)
                if token.startswith('-'):
                    continue

                # Remove version specifiers (==1.0, >=2.0, <=3.0, ~=1.2, etc.)
                pkg_name = re.sub(r'[<>=!~]+.*', '', token).strip()

                # Clean up apt-specific syntax (package/distro, package:arch)
                pkg_name = re.sub(r'[/:].*', '', pkg_name).strip()

                if pkg_name:
                    packages.add(pkg_name)

        # Return as list of dicts
        results = []
        for pkg in sorted(packages):
            results.append({
                "import_name": pkg,
                "package_name": pkg,
                "ecosystem": "APT",  # Bash packages are typically APT ecosystem
            })

        return results

    @staticmethod
    def _analyze_powershell(script_text: str) -> List[Dict[str, Any]]:
        """
        Analyze PowerShell script for modules using regex pattern matching.
        Matches: Import-Module, Install-Module, Install-Package

        Returns list of dicts with: import_name, package_name, ecosystem
        """
        if not script_text:
            return []

        modules = set()

        # Patterns for PowerShell module/package installation
        patterns = [
            # Import-Module -Name ModuleName or positional
            r'(?:Import|Install)-Module\s+(?:-Name\s+)?([a-zA-Z0-9._-]+)',
            # Install-Package -Name PackageName
            r'Install-Package\s+(?:-Name\s+)?([a-zA-Z0-9._-]+)',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, script_text, re.IGNORECASE):
                module_name = match.group(1)
                modules.add(module_name)

        # Return as list of dicts
        results = []
        for module in sorted(modules):
            results.append({
                "import_name": module,
                "package_name": module,
                "ecosystem": "NUGET",  # PowerShell modules are typically NUGET ecosystem
            })

        return results

    @staticmethod
    async def analyze_script(
        script_text: str,
        language: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: analyze a script for package suggestions.

        Args:
            script_text: The script content to analyze
            language: Optional language override (python, bash, powershell)
            db: AsyncSession for ApprovedIngredient cross-reference (optional)

        Returns:
            {
                "detected_language": "python",
                "suggestions": [
                    {
                        "import_name": "requests",
                        "package_name": "requests",
                        "ecosystem": "PYPI",
                        "mapped": False,
                        ...
                    },
                    ...
                ]
            }
        """
        # Auto-detect language if not provided
        detected_lang = language or AnalyzerService._detect_language(script_text)

        # Extract imports based on language
        if detected_lang == "python":
            suggestions = AnalyzerService._analyze_python(script_text)
            ecosystem = "PYPI"
        elif detected_lang == "bash":
            suggestions = AnalyzerService._analyze_bash(script_text)
            ecosystem = "APT"
        elif detected_lang == "powershell":
            suggestions = AnalyzerService._analyze_powershell(script_text)
            ecosystem = "NUGET"
        else:
            suggestions = []
            ecosystem = None

        # Enrich suggestions with ecosystem if not already set
        for suggestion in suggestions:
            if "ecosystem" not in suggestion:
                suggestion["ecosystem"] = ecosystem or "UNKNOWN"

        return {
            "detected_language": detected_lang,
            "suggestions": suggestions
        }
