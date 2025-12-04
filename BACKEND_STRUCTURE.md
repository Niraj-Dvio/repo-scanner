# Backend Architecture & Module Structure

## Overview

The backend is organized as a modular scanning engine with a FastAPI HTTP layer. Core scanning logic is separated into plugin modules for maintainability and extensibility.

## Module Organization

```
backend/
├── main.py              # FastAPI application & REST routes
├── config.py            # Configuration & logging
├── models.py            # Data classes (ScanResult, SecretFinding, etc.)
├── scanner.py           # Main orchestration engine
├── db.py                # SQLAlchemy models & DB operations
└── plugins/
    ├── utils.py         # Common utilities (git, tools, file utilities)
    ├── secrets.py       # Secret scanning with patterns & TruffleHog
    ├── dependencies.py  # Python/Node.js dependency scanning
    └── code_quality.py  # Code quality scanning (Semgrep, Bandit)
```

## Key Modules

### `config.py`

Configuration management and logging setup.

**Exports:**

- `ScanConfig` - Dataclass with all scanning parameters
- `setup_logging()` - Configure logging

**Usage:**

```python
from config import ScanConfig, setup_logging
config = ScanConfig(enable_semgrep=True, generate_lockfile=True)
logger = setup_logging("module_name")
```

### `models.py`

Data models for scan results and API responses.

**Exports:**

- `SecretFinding` - Represents a detected secret
- `DependencyResult` - Dependency scan results
- `ScanResult` - Complete scan result

**Usage:**

```python
from models import ScanResult, SecretFinding
result = ScanResult(repo_name="repo", repo_url="...", status="completed", ...)
```

### `scanner.py`

Main scanning orchestration engine.

**Key Functions:**

- `scan_repository(repo_url, config)` - Main scanning entry point
- `generate_repo_summary(repo_path)` - Generate repository statistics

**Example:**

```python
from scanner import scan_repository
from config import ScanConfig

config = ScanConfig()
result = scan_repository("https://github.com/user/repo.git", config)
print(result.secrets)  # List of SecretFinding objects
```

### `db.py`

Database persistence layer using SQLAlchemy.

**Exports:**

- `ScanModel` - SQLAlchemy ORM model
- `init_db()` - Initialize database
- `save_scan_to_db()` - Persist scan results
- `get_scan_from_db()` - Retrieve scan results

**Environment Variables:**

- `DATABASE_URL` - PostgreSQL connection string (default: `postgresql://postgres:postgres@db:5432/scanner`)

### `plugins/utils.py`

Common utilities for all plugins.

**Key Functions:**

- `sanitize_repo_name()` - Clean repository name
- `validate_repo_url()` - Validate git repository URLs
- `clone_repository()` - Clone repo with timeout handling
- `check_tool_version()` - Detect tools with fallbacks
- `is_text_file()` - Detect text vs. binary files
- `temp_repo_context()` - Context manager for safe repo cloning

### `plugins/secrets.py`

Secret scanning with pattern matching and TruffleHog integration.

**Key Functions:**

- `run_secret_scan(repo_path, config)` - Main secret scanning
- `scan_file_for_secrets()` - Pattern-based file scanning
- `run_trufflehog_scan()` - TruffleHog integration
- `dedupe_findings()` - Merge duplicate findings

**Supported Secrets:**

- AWS keys & secrets
- GitHub tokens (personal, OAuth, fine-grained)
- API keys & secret keys
- Passwords & tokens
- Private key headers
- Custom patterns

### `plugins/dependencies.py`

Dependency scanning for Python and Node.js projects.

**Key Functions:**

- `scan_python_dependencies()` - Python package scanning
  - Tools: pip-audit, safety
- `scan_node_dependencies()` - Node.js package scanning
  - Tools: npm audit, snyk
  - Includes fallback: generates package-lock in temp dir if missing
- `scan_dependencies()` - Runs all dependency scans

### `plugins/code_quality.py`

Code quality scanning with Semgrep and Bandit.

**Key Functions:**

- `scan_code_quality()` - Main code quality scanning
  - Detects applicable languages (Python, JavaScript)
  - Tools: semgrep, bandit

## Data Flow

```
HTTP Request (POST /scan)
    ↓
main.py (API route handler)
    ↓
scanner.py (Orchestration)
    ├→ clone_repository (via plugins/utils.py)
    ├→ run_secret_scan (via plugins/secrets.py)
    ├→ scan_dependencies (via plugins/dependencies.py)
    │  ├→ scan_python_dependencies
    │  └→ scan_node_dependencies
    ├→ scan_code_quality (via plugins/code_quality.py)
    └→ generate_repo_summary
    ↓
ScanResult (models.py)
    ↓
db.py (Persist if enabled)
    ↓
HTTP Response

```

## Scanning Features

### Secret Detection

- Pattern-based scanning with regex
- TruffleHog integration (optional)
- Sensitive file detection (.env, .key, .pem, etc.)
- Source code scanning (.py, .js, .java, etc.)
- Configurable redaction

### Dependency Scanning

- **Python:** requirements.txt, setup.py, pyproject.toml
  - pip-audit, safety
- **Node.js:** package.json, package-lock.json
  - npm audit, snyk
  - Auto-generate package-lock if missing
- Deduplication by tool

### Code Quality

- **Python:** Bandit (security linter)
- **JavaScript/TypeScript:** Semgrep (pattern-based)
- Language detection
- Finds top 10 issues per tool

## Configuration

Configure scanning behavior via `ScanConfig`:

```python
config = ScanConfig(
    # Limits
    max_file_size=5 * 1024 * 1024,      # 5 MB
    max_repo_size=500 * 1024 * 1024,    # 500 MB
    default_timeout=120,                 # seconds

    # Behavior
    redact_secrets=True,                 # Redact secret values
    generate_lockfile=True,              # Generate npm lockfile if missing

    # Toggles
    enable_trufflehog=True,
    enable_semgrep=True,
    enable_pip_audit=True,
    enable_npm_audit=True,
    # ... more toggles
)
```

## Extension Points

### Adding a New Scanner

1. Create `plugins/myscanner.py`:

```python
from models import DependencyResult
from .utils import check_tool_version

def scan_myscan(repo_path: str, config) -> DependencyResult:
    result = DependencyResult(applicable=False, status="not_applicable")
    # ... scanning logic
    return result
```

2. Import and call in `scanner.py`:

```python
from plugins.myscan import scan_myscan

myscan_result = scan_myscan(repo_path, config)
dependencies["myscan"] = myscan_result.to_dict()
```

## Error Handling

All plugins:

- Capture stderr and return codes
- Append errors to `result.errors` list
- Continue scanning even if one tool fails
- Return `applicable=False` when not relevant

## Tool Detection

Tools are detected in order:

1. Direct invocation (`tool --version`)
2. `npx` fallback (for Node.js tools)
3. `python -m` fallback (for Python tools)
4. Report "not installed" if not found

## Testing

Run syntax checks:

```bash
python -m py_compile config.py models.py scanner.py db.py
python -m py_compile plugins/*.py
```

Verify imports:

```python
from config import ScanConfig
from models import ScanResult
from scanner import scan_repository
from plugins import secrets, dependencies, code_quality
```

## Performance

- Parallel file scanning (configurable workers)
- Async repository operations via FastAPI background tasks
- Context managers for safe cleanup
- Disk space checks before cloning
- Timeout protection on all subprocess calls
