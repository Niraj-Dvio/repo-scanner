import os
import re
import json
import shutil
import subprocess
import logging
import hashlib
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
from contextlib import contextmanager

# ==================== Configuration ====================
@dataclass
class ScanConfig:
    """Configuration for security scanning"""
    max_file_size: int = 5 * 1024 * 1024  # 5 MB
    max_repo_size: int = 500 * 1024 * 1024  # 500 MB
    default_timeout: int = 120  # seconds
    base_path: str = "./repos"
    max_workers: int = 4
    scan_depth: int = 10  # max directory depth
    enable_parallel: bool = True
    log_level: str = "INFO"
    redact_secrets: bool = True
    include_line_numbers: bool = True
    scan_source_files: bool = True
    # If true, when package.json exists but no lockfile, try to generate a package-lock.json
    # in a temporary directory to allow `npm audit` to run. This can be slower and requires
    # network access — set to False to disable.
    generate_lockfile: bool = True
    
    # Scanner toggles
    enable_trufflehog: bool = True
    enable_pip_audit: bool = True
    enable_safety: bool = True
    enable_npm_audit: bool = True
    enable_snyk: bool = True
    enable_semgrep: bool = True
    enable_bandit: bool = True

# ==================== Legacy Constants (for backward compatibility) ====================
BASE_PATH = ScanConfig().base_path
DEFAULT_TIMEOUT = ScanConfig().default_timeout
MAX_FILE_SIZE = ScanConfig().max_file_size


# ==================== Logging Setup ====================
def setup_logging(level: str = "INFO"):
    """Configure logging with rotation"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('security_scan.log')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ==================== Constants ====================
SENSITIVE_EXTENSIONS = {
    ".env", ".key", ".pem", ".jks", ".p12", ".crt", ".cer",
    ".properties", ".credentials", ".config", ".yaml", ".yml",
    ".json", ".xml", ".ini", ".toml", ".conf"
}

# Include some common source/config extensions that often contain hard-coded keys
SENSITIVE_EXTENSIONS.update({'.java', '.gradle'})

# Optional set of common source extensions to search for secrets in code
SOURCE_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.go', '.rb', '.php', '.cs', '.scala', '.kt', '.swift', '.cpp', '.c'}

SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "credentials", "secrets", "password", "token", "apikey",
    "aws_credentials", "gcp_credentials", "azure_credentials",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"
}

# Enhanced secret patterns with named groups
SECRET_PATTERNS = [
    # AWS
    (re.compile(r"(AKIA[0-9A-Z]{16})"), "AWS Access Key"),
    (re.compile(r"(?i)aws(.{0,20})?[\'\"]([0-9a-zA-Z/+]{40})[\'\"]"), "AWS Secret Key"),
    
    # GitHub
    (re.compile(r"ghp_[A-Za-z0-9_]{36}"), "GitHub Personal Token"),
    (re.compile(r"gho_[A-Za-z0-9_]{36}"), "GitHub OAuth Token"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{82}"), "GitHub Fine-grained PAT"),
    
    # Generic API Keys
    (re.compile(r"(?i)(api[-_]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})"), "API Key"),
    (re.compile(r"(?i)(secret[-_]?key|secretkey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})"), "Secret Key"),
    
    # Passwords
    (re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]([^'\"]{8,})['\"]"), "Password"),
    
    # Database URLs
    (re.compile(r"(?i)(database_url|db_url)\s*[:=]\s*['\"]?([^'\"]+)"), "Database URL"),
    (re.compile(r"(mongodb(\+srv)?://[^\s]+)"), "MongoDB Connection String"),
    (re.compile(r"(postgres(ql)?://[^\s]+)"), "PostgreSQL Connection String"),
    
    # JWT
    (re.compile(r"(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"), "JWT Token"),
    
    # Private Keys
    (re.compile(r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----"), "Private Key"),
    
    # Slack
    (re.compile(r"xox[pborsa]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24,}"), "Slack Token"),
    
    # Google
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "Google API Key"),
    
    # Stripe
    (re.compile(r"sk_live_[0-9a-zA-Z]{24,}"), "Stripe Live Secret Key"),
    
    # Base64 encoded secrets (heuristic)
    (re.compile(r"(?i)(secret|password|key|token)\s*[:=]\s*['\"]?([A-Za-z0-9+/]{40,}={0,2})"), "Base64 Encoded Secret"),

    # Generic key-value pattern (properties/YAML) - more permissive on length and accepts dot/underscore/dash
    (re.compile(r"(?i)(?:[\w\.-]*\.)?(?:api[-_.]?key|apikey|apisecret|client[_\-.]?secret|access[_\-.]?token|access_token|client_secret|secret[-_]?key|secretkey|token|password|pwd)\s*[:=]\s*['\"]?([A-Za-z0-9\-_.+\/=]{4,200})"), "Generic Key-Value"),
]

ALLOWED_URL_SCHEMES = {'http', 'https', 'git', 'ssh'}

IGNORE_PATTERNS = {
    r"test[_/]",
    r"mock[_/]",
    r"fixture[_/]",
    r"example[_/]",
    r"\.example$",
    r"\.sample$",
    r"\.template$",
}

# ==================== Data Models ====================
@dataclass
class SecretFinding:
    """Represents a found secret"""
    file_path: str
    line_number: int
    secret_type: str
    pattern: str
    context: str  # Redacted context
    severity: str = "HIGH"
    start: int = 0
    end: int = 0
    matched_value: str = ""
    
    def to_dict(self):
        d = asdict(self)
        # ensure matched_value not too large
        if isinstance(d.get('matched_value'), str) and len(d.get('matched_value', '')) > 200:
            d['matched_value'] = d['matched_value'][:200] + '...'
        return d

@dataclass
class ScanResult:
    """Complete scan results"""
    repo_name: str
    repo_url: str
    status: str
    secrets: List[SecretFinding]
    dependencies: Dict
    summary: Dict
    errors: List[str]
    scan_duration: float
    
    def to_dict(self):
        return {
            "repo_name": self.repo_name,
            "repo_url": self.repo_url,
            "status": self.status,
            "secrets": [s.to_dict() for s in self.secrets],
            "dependencies": self.dependencies,
            "summary": self.summary,
            "errors": self.errors,
            "scan_duration": self.scan_duration,
        }

# ==================== Utilities ====================
def validate_repo_url(url: str) -> Tuple[bool, str]:
    """Validate repository URL"""
    try:
        parsed = urlparse(url)
        
        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            return False, f"Invalid scheme: {parsed.scheme}"
        
        # Block localhost and private IPs
        if parsed.hostname:
            if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                return False, "Localhost URLs not allowed"
            
            # Basic private IP check
            if parsed.hostname.startswith(('10.', '172.', '192.168.')):
                return False, "Private IP addresses not allowed"
        
        return True, ""
    except Exception as e:
        return False, f"URL parsing error: {str(e)}"

def sanitize_repo_name(url: str) -> str:
    """Generate safe repository name from URL"""
    parsed = urlparse(url)
    path = parsed.path.strip('/').replace('/', '_')
    if path.endswith('.git'):
        path = path[:-4]
    
    # Add hash for uniqueness
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{path}_{url_hash}"

def redact_secret(text: str, start: int, end: int) -> str:
    """Redact secret from text"""
    secret_len = end - start
    visible_chars = min(4, secret_len // 4)
    
    if secret_len <= visible_chars * 2:
        return '*' * secret_len
    
    return text[start:start+visible_chars] + '*' * (secret_len - visible_chars * 2) + text[end-visible_chars:end]

def should_ignore_file(filepath: str) -> bool:
    """Check if file should be ignored based on patterns"""
    filepath_lower = filepath.lower()
    return any(re.search(pattern, filepath_lower) for pattern in IGNORE_PATTERNS)

def is_text_file(filepath: str, sample_size: int = 8192) -> bool:
    """Check if file is text-based"""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(sample_size)
            if b'\x00' in chunk:
                return False
            
            # Check for high ratio of printable characters
            text_chars = sum(1 for byte in chunk if 32 <= byte <= 126 or byte in (9, 10, 13))
            return text_chars / len(chunk) > 0.85 if chunk else False
    except Exception:
        return False

def check_disk_space(path: str, required_mb: int = 100) -> bool:
    """Check if enough disk space is available"""
    try:
        stat = shutil.disk_usage(path)
        available_mb = stat.free / (1024 * 1024)
        return available_mb >= required_mb
    except Exception:
        return True  # Assume OK if check fails

@contextmanager
def temp_repo_context(repo_url: str, config: ScanConfig):
    """Context manager for temporary repository cloning"""
    repo_name = sanitize_repo_name(repo_url)
    repo_path = os.path.join(config.base_path, repo_name)
    
    try:
        # Ensure base directory exists; handle race conditions
        try:
            os.makedirs(config.base_path, exist_ok=True)
        except FileExistsError:
            # Race condition: another process created it between check and creation
            if not os.path.isdir(config.base_path):
                raise
            pass
        
        yield repo_path
    finally:
        # Cleanup
        if os.path.exists(repo_path):
            try:
                shutil.rmtree(repo_path, ignore_errors=True)
                logger.info(f"Cleaned up repository: {repo_path}")
            except Exception as e:
                logger.error(f"Cleanup failed for {repo_path}: {e}")

# ==================== Repository Operations ====================
def clone_repository(repo_url: str, repo_path: str, timeout: int = 300) -> Tuple[bool, str]:
    """Clone repository with validation and timeout"""
    try:
        # Validate URL
        is_valid, error_msg = validate_repo_url(repo_url)
        if not is_valid:
            return False, error_msg
        
        # Check disk space
        if not check_disk_space(os.path.dirname(repo_path)):
            return False, "Insufficient disk space"
        
        # Clone with timeout
        from git import Repo
        
        if os.path.exists(repo_path):
            logger.warning(f"Repository path exists, removing: {repo_path}")
            shutil.rmtree(repo_path, ignore_errors=True)
        
        logger.info(f"Cloning repository: {repo_url}")
        Repo.clone_from(
            repo_url, 
            repo_path,
            depth=1,  # Shallow clone
            single_branch=True
        )
        
        # Validate repo size
        total_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(repo_path)
            for filename in filenames
        )
        
        if total_size > ScanConfig().max_repo_size:
            return False, f"Repository too large: {total_size / (1024*1024):.2f} MB"
        
        logger.info(f"Successfully cloned repository to {repo_path}")
        return True, ""
        
    except Exception as e:
        logger.error(f"Clone failed: {e}")
        return False, f"Clone failed: {str(e)}"

# ==================== Secret Scanning ====================
def scan_file_for_secrets(
    filepath: str, 
    repo_path: str, 
    config: ScanConfig
) -> List[SecretFinding]:
    """Scan a single file for secrets"""
    findings = []
    
    try:
        # Skip if should be ignored
        if should_ignore_file(filepath):
            return findings
        
        # Check file size
        file_size = os.path.getsize(filepath)
        if file_size > config.max_file_size:
            logger.debug(f"Skipping large file: {filepath}")
            return findings
        
        # Check if text file
        if not is_text_file(filepath):
            return findings
        
        # Read file
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Check each line
        for line_num, line in enumerate(lines, 1):
            for pattern, secret_type in SECRET_PATTERNS:
                for match in pattern.finditer(line):
                    try:
                        # Prefer capturing group value if present
                        if match.lastindex:
                            start, end = match.span(match.lastindex)
                            matched_value = match.group(match.lastindex)
                        else:
                            start, end = match.span()
                            matched_value = match.group(0)
                    except Exception:
                        start, end = match.span()
                        matched_value = match.group(0)

                    # Redact only the secret value portion when possible
                    if config.redact_secrets:
                        try:
                            redacted = redact_secret(line, start, end)
                            context = line[:start] + redacted + line[end:]
                        except Exception:
                            context = line
                    else:
                        context = line

                    # Build finding including match span and matched_value
                    finding = SecretFinding(
                        file_path=os.path.relpath(filepath, repo_path),
                        line_number=line_num if config.include_line_numbers else 0,
                        secret_type=secret_type,
                        pattern=pattern.pattern[:200],  # keep a longer pattern fragment for context
                        context=context.strip(),
                        severity=("HIGH" if "password" in secret_type.lower() or "key" in secret_type.lower() or "token" in secret_type.lower() else "MEDIUM"),
                        start=start,
                        end=end,
                        matched_value=matched_value
                    )
                    findings.append(finding)
        
    except Exception as e:
        logger.debug(f"Error scanning {filepath}: {e}")
    
    return findings

def run_trufflehog(repo_path: str, timeout: int = 120) -> List[str]:
    """Run TruffleHog scanner"""
    findings = []
    try:
        trufflehog_bin = shutil.which("trufflehog")
        if not trufflehog_bin:
            logger.warning("TruffleHog not found, skipping")
            return findings
        
        logger.info("Running TruffleHog scan...")
        result = subprocess.run(
            [trufflehog_bin, "filesystem", repo_path, "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        if result.stdout:
            for line in result.stdout.splitlines():
                try:
                    data = json.loads(line)
                    findings.append(f"TruffleHog: {data.get('DetectorName', 'Unknown')} in {data.get('SourceMetadata', {}).get('file', 'unknown')}")
                except json.JSONDecodeError:
                    findings.append(line.strip())
        
        logger.info(f"TruffleHog found {len(findings)} issues")
    except subprocess.TimeoutExpired:
        logger.error("TruffleHog scan timed out")
        findings.append("TruffleHog scan timed out")
    except Exception as e:
        logger.error(f"TruffleHog scan failed: {e}")
        findings.append(f"TruffleHog error: {str(e)}")
    
    return findings

def run_secret_scan(repo_path: str, config: ScanConfig) -> Dict:
    """Run comprehensive secret scanning"""
    all_findings = []
    errors = []
    
    # Run TruffleHog if enabled
    trufflehog_results = []
    if config.enable_trufflehog:
        try:
            trufflehog_results = run_trufflehog(repo_path, config.default_timeout)
        except Exception as e:
            errors.append(f"TruffleHog failed: {str(e)}")
    
    # Collect all files to scan
    files_to_scan = []
    for root, dirs, files in os.walk(repo_path):
        # Skip .git directory
        dirs[:] = [d for d in dirs if d != '.git']
        
        # Check depth
        depth = root[len(repo_path):].count(os.sep)
        if depth > config.scan_depth:
            continue
        
        for file in files:
            filepath = os.path.join(root, file)
            
            # Check if sensitive file
            filename_lower = file.lower()
            ext = os.path.splitext(file)[1].lower()
            
            # Add file if it's a known sensitive extension or filename, or (optionally) a common source file
            if (ext in SENSITIVE_EXTENSIONS or 
                any(sens in filename_lower for sens in SENSITIVE_FILENAMES) or
                (config.scan_source_files and ext in SOURCE_EXTENSIONS)):
                files_to_scan.append(filepath)
    
    logger.info(f"Scanning {len(files_to_scan)} sensitive files...")
    
    # Parallel scanning
    if config.enable_parallel and len(files_to_scan) > 10:
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            futures = {
                executor.submit(scan_file_for_secrets, fp, repo_path, config): fp 
                for fp in files_to_scan
            }
            
            for future in as_completed(futures):
                try:
                    findings = future.result()
                    all_findings.extend(findings)
                except Exception as e:
                    filepath = futures[future]
                    logger.error(f"Error scanning {filepath}: {e}")
                    errors.append(f"Scan error in {filepath}: {str(e)}")
    else:
        # Sequential scanning
        for filepath in files_to_scan:
            try:
                findings = scan_file_for_secrets(filepath, repo_path, config)
                all_findings.extend(findings)
            except Exception as e:
                logger.error(f"Error scanning {filepath}: {e}")
                errors.append(f"Scan error in {filepath}: {str(e)}")
    
    # Deduplicate findings by merging overlapping spans on the same file/line.
    # For overlapping/identical spans, keep the most specific finding.
    def specificity_score(f: SecretFinding) -> int:
        s = 0
        t = f.secret_type.lower() if f.secret_type else ''
        providers = ('google', 'aws', 'github', 'stripe', 'slack', 'jwt', 'mongodb', 'postgres', 'postgresql')
        if any(p in t for p in providers):
            s += 100
        try:
            s += len(f.matched_value or '')
        except Exception:
            pass
        if 'generic' in t or 'key-value' in t or 'possible' in t:
            s -= 10
        return s

    grouped = {}
    for f in all_findings:
        grouped.setdefault((f.file_path, f.line_number), []).append(f)

    unique_findings = []
    for (fp, ln), items in grouped.items():
        # sort by start position
        items.sort(key=lambda x: (x.start, x.end))
        kept = []
        for item in items:
            replaced = False
            for idx, existing in enumerate(kept):
                # check overlap
                if not (item.end <= existing.start or item.start >= existing.end):
                    # overlapping spans: pick the more specific
                    if specificity_score(item) > specificity_score(existing):
                        kept[idx] = item
                    replaced = True
                    break
            if not replaced:
                kept.append(item)

        unique_findings.extend(kept)
    
    logger.info(f"Found {len(unique_findings)} unique secrets")
    
    return {
        "findings": unique_findings,
        "trufflehog_results": trufflehog_results,
        "errors": errors,
        "files_scanned": len(files_to_scan)
    }

# ==================== Dependency Scanning ====================
def check_tool_version(tool_name: str) -> Optional[str]:
    """Check if tool is installed and get version"""
    try:
        tool_path = shutil.which(tool_name)
        if tool_path:
            try:
                result = subprocess.run(
                    [tool_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result and result.stdout:
                    return result.stdout.strip().split('\n')[0]
            except Exception:
                pass

        # Fallbacks: try python -m <tool> (for semgrep) or use npx if npm is available
        if tool_name == 'semgrep':
            try:
                result = subprocess.run([sys.executable, '-m', 'semgrep', '--version'], capture_output=True, text=True, timeout=10)
                if result and result.stdout:
                    return result.stdout.strip().split('\n')[0]
            except Exception:
                pass

        # Try using npx if available (useful for snyk and other npm-based CLIs)
        npx_path = shutil.which('npx') or shutil.which('npm')
        if npx_path:
            try:
                # Use npx to run the tool's version command; allow network install if needed
                result = subprocess.run(['npx', '--yes', tool_name, '--version'], capture_output=True, text=True, timeout=20)
                if result and result.returncode == 0 and result.stdout:
                    return result.stdout.strip().split('\n')[0]
            except Exception:
                pass

        return None
    except Exception:
        return None

def scan_python_dependencies(repo_path: str, config: ScanConfig) -> Dict:
    """Scan Python dependencies with pip-audit and safety"""
    results = {"status": "not_applicable", "findings": [], "errors": [], "applicable": False}
    
    req_files = [
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-test.txt",
        "dev-requirements.txt"
    ]
    
    found_files = [f for f in req_files if os.path.exists(os.path.join(repo_path, f))]
    
    if not found_files:
        results["applicable"] = False
        return results

    results["applicable"] = True
    
    results["status"] = "scanned"
    results["files"] = found_files
    
    # pip-audit
    if config.enable_pip_audit:
        try:
            pip_audit = shutil.which("pip-audit")
            if pip_audit:
                logger.info("Running pip-audit...")
                for req_file in found_files:
                    result = subprocess.run(
                        [pip_audit, "-r", os.path.join(repo_path, req_file), "--format", "json"],
                        capture_output=True,
                        text=True,
                        timeout=config.default_timeout
                    )
                    if result.returncode != 0 and result.stderr:
                        results["errors"].append(f"pip-audit error for {req_file}: {result.stderr.strip()}")

                    if result.stdout:
                        try:
                            data = json.loads(result.stdout)
                            results["findings"].append({
                                "tool": "pip-audit",
                                "file": req_file,
                                "vulnerabilities": data.get("dependencies", [])
                            })
                        except json.JSONDecodeError:
                            results["findings"].append({
                                "tool": "pip-audit",
                                "file": req_file,
                                "output": result.stdout
                            })
            else:
                results["errors"].append("pip-audit not installed")
        except Exception as e:
            results["errors"].append(f"pip-audit failed: {str(e)}")
    
    # safety
    if config.enable_safety:
        try:
            safety = shutil.which("safety")
            if safety:
                logger.info("Running safety check...")
                for req_file in found_files:
                    result = subprocess.run(
                        [safety, "check", "-r", os.path.join(repo_path, req_file), "--json"],
                        capture_output=True,
                        text=True,
                        timeout=config.default_timeout
                    )
                    if result.returncode != 0 and result.stderr:
                        results["errors"].append(f"safety error for {req_file}: {result.stderr.strip()}")

                    if result.stdout:
                        try:
                            data = json.loads(result.stdout)
                            results["findings"].append({
                                "tool": "safety",
                                "file": req_file,
                                "vulnerabilities": data
                            })
                        except json.JSONDecodeError:
                            results["errors"].append(f"safety output not JSON for {req_file}")
            else:
                results["errors"].append("safety not installed")
        except Exception as e:
            results["errors"].append(f"safety check failed: {str(e)}")
    
    return results

def scan_node_dependencies(repo_path: str, config: ScanConfig) -> Dict:
    """Scan Node.js dependencies"""
    results = {"status": "not_applicable", "findings": [], "errors": [], "applicable": False}

    package_json = os.path.join(repo_path, "package.json")
    if not os.path.exists(package_json):
        results["applicable"] = False
        return results

    results["applicable"] = True
    results["status"] = "scanned"
    # npm audit
    if config.enable_npm_audit:
        try:
            npm = shutil.which("npm")
            if npm:
                logger.info("Running npm audit...")
                result = subprocess.run(
                    [npm, "audit", "--json"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=config.default_timeout,
                )

                performed_audit = False
                if result.returncode != 0 and result.stderr:
                    results["errors"].append(f"npm audit error: {result.stderr.strip()}")

                if result.stdout:
                    try:
                        data = json.loads(result.stdout)
                        results["findings"].append({
                            "tool": "npm-audit",
                            "vulnerabilities": data.get("vulnerabilities", {}),
                            "metadata": data.get("metadata", {}),
                        })
                        performed_audit = True
                    except json.JSONDecodeError:
                        results["findings"].append({"tool": "npm-audit", "output": result.stdout})

                # Fallback: try generating a package-lock.json in a temp dir and re-run audit
                if not performed_audit and config.generate_lockfile:
                    try:
                        import tempfile
                        tmp = tempfile.mkdtemp(prefix="npm-audit-")
                        shutil.copy(package_json, os.path.join(tmp, "package.json"))
                        pkg_lock = os.path.join(repo_path, "package-lock.json")
                        if os.path.exists(pkg_lock):
                            shutil.copy(pkg_lock, os.path.join(tmp, "package-lock.json"))

                        gen = subprocess.run([npm, "install", "--package-lock-only"], cwd=tmp, capture_output=True, text=True, timeout=config.default_timeout)
                        if gen.returncode != 0:
                            if gen.stderr:
                                results["errors"].append(f"npm lockfile generation failed: {gen.stderr.strip()}")
                        else:
                            aud = subprocess.run([npm, "audit", "--json"], cwd=tmp, capture_output=True, text=True, timeout=config.default_timeout)
                            if aud.returncode == 0 and aud.stdout:
                                try:
                                    data = json.loads(aud.stdout)
                                    results["findings"].append({
                                        "tool": "npm-audit",
                                        "vulnerabilities": data.get("vulnerabilities", {}),
                                        "metadata": data.get("metadata", {}),
                                    })
                                    performed_audit = True
                                except json.JSONDecodeError:
                                    results["errors"].append("npm audit (temp) output not JSON")
                            else:
                                if aud.stderr:
                                    results["errors"].append(f"npm audit (temp) failed: {aud.stderr.strip()}")
                        try:
                            shutil.rmtree(tmp, ignore_errors=True)
                        except Exception:
                            pass
                    except Exception as e:
                        results["errors"].append(f"npm audit fallback failed: {str(e)}")
            else:
                results["errors"].append("npm not installed")
        except Exception as e:
            results["errors"].append(f"npm audit failed: {str(e)}")

    # Snyk
    if config.enable_snyk:
        try:
            snyk = shutil.which("snyk")
            run_cmd = None
            if snyk:
                run_cmd = [snyk, "test", "--json"]
            elif shutil.which("npx") or shutil.which("npm"):
                run_cmd = ["npx", "--yes", "snyk", "test", "--json"]

            if run_cmd:
                logger.info("Running Snyk test...")
                result = subprocess.run(
                    run_cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=config.default_timeout,
                )

                if result.stdout:
                    try:
                        data = json.loads(result.stdout)
                        results["findings"].append({"tool": "snyk", "vulnerabilities": data.get("vulnerabilities", [])})
                    except json.JSONDecodeError:
                        results["findings"].append({"tool": "snyk", "output": result.stdout})
            else:
                results["errors"].append("snyk not installed. Install via `npm install -g snyk` or ensure `npx` is available.")
        except Exception as e:
            results["errors"].append(f"snyk test failed: {str(e)}")
    
    return results


def scan_code_quality(repo_path: str, config: ScanConfig) -> Dict:
    """Scan code quality with Semgrep and Bandit"""
    results = {"findings": [], "errors": [], "applicable": False}
    
    # Semgrep
    # Determine if code-quality scanning is applicable (any source files present)
    source_files = False
    for ext in SOURCE_EXTENSIONS:
        if list(Path(repo_path).rglob(f"*{ext}")):
            source_files = True
            break
    if source_files:
        results["applicable"] = True

    if config.enable_semgrep and source_files:
        try:
            semgrep = shutil.which("semgrep")
            # Prefer system semgrep, else try python -m semgrep, else try npx
            run_cmd = None
            if semgrep:
                run_cmd = [semgrep, "--config=auto", "--json", repo_path]
            else:
                # try python -m semgrep
                try:
                    run_cmd = [sys.executable, '-m', 'semgrep', '--config=auto', '--json', repo_path]
                except Exception:
                    run_cmd = None

            if not run_cmd and (shutil.which('npx') or shutil.which('npm')):
                run_cmd = ['npx', '--yes', 'semgrep', '--config=auto', '--json', repo_path]

            if run_cmd:
                logger.info("Running Semgrep...")
                result = subprocess.run(
                    run_cmd,
                    capture_output=True,
                    text=True,
                    timeout=config.default_timeout
                )

                if result.stdout:
                    try:
                        data = json.loads(result.stdout)
                        results["findings"].append({
                            "tool": "semgrep",
                            "results": data.get("results", [])
                        })
                    except json.JSONDecodeError:
                        results["errors"].append("semgrep output not JSON or parsing failed")
            else:
                results["errors"].append("semgrep not installed. Install via `pip install semgrep` or ensure `npx` is available.")
        except Exception as e:
            results["errors"].append(f"semgrep failed: {str(e)}")
    
    # Bandit (Python)
    if config.enable_bandit:
        python_files = list(Path(repo_path).rglob("*.py"))
        if python_files:
            try:
                bandit = shutil.which("bandit")
                if bandit:
                    logger.info("Running Bandit...")
                    result = subprocess.run(
                        [bandit, "-r", repo_path, "-f", "json"],
                        capture_output=True,
                        text=True,
                        timeout=config.default_timeout
                    )
                    
                    if result.stdout:
                        try:
                            data = json.loads(result.stdout)
                            results["findings"].append({
                                "tool": "bandit",
                                "results": data.get("results", [])
                            })
                        except json.JSONDecodeError:
                            pass
                else:
                    results["errors"].append("bandit not installed")
            except Exception as e:
                results["errors"].append(f"bandit failed: {str(e)}")
    
    return results

def run_dependency_scan(repo_path: str, config: ScanConfig) -> Dict:
    """Run all dependency scans"""
    results = {
        "python": {},
        "node": {},
        "code_quality": {},
        "tool_versions": {}
    }
    
    # Check tool versions
    tools = ["pip-audit", "safety", "npm", "snyk", "semgrep", "bandit", "trufflehog"]
    for tool in tools:
        version = check_tool_version(tool)
        results["tool_versions"][tool] = version if version else "not installed"
    
    # Run scans
    try:
        results["python"] = scan_python_dependencies(repo_path, config)
    except Exception as e:
        logger.error(f"Python dependency scan failed: {e}")
        results["python"] = {"status": "error", "error": str(e)}
    
    try:
        results["node"] = scan_node_dependencies(repo_path, config)
    except Exception as e:
        logger.error(f"Node dependency scan failed: {e}")
        results["node"] = {"status": "error", "error": str(e)}
    
    try:
        results["code_quality"] = scan_code_quality(repo_path, config)
    except Exception as e:
        logger.error(f"Code quality scan failed: {e}")
        results["code_quality"] = {"status": "error", "error": str(e)}
    
    return results

# ==================== Repository Summary ====================
def generate_repo_summary(repo_path: str) -> Dict:
    """Generate repository summary"""
    summary = {
        "total_size_kb": 0,
        "file_count": 0,
        "directory_count": 0,
        "by_extension": {},
        "by_language": {},
        "sensitive_files": [],
    }
    
    try:
        for root, dirs, files in os.walk(repo_path):
            # Skip .git
            dirs[:] = [d for d in dirs if d != '.git']
            
            summary["directory_count"] += len(dirs)
            
            for file in files:
                try:
                    filepath = os.path.join(root, file)
                    size = os.path.getsize(filepath)
                    summary["total_size_kb"] += size / 1024
                    summary["file_count"] += 1
                    
                    # Extension stats
                    ext = os.path.splitext(file)[1].lower() or 'no_extension'
                    summary["by_extension"][ext] = summary["by_extension"].get(ext, 0) + 1
                    
                    # Track sensitive files
                    if any(file.lower().endswith(e) for e in SENSITIVE_EXTENSIONS):
                        summary["sensitive_files"].append(os.path.relpath(filepath, repo_path))
                    
                except Exception as e:
                    logger.debug(f"Error processing file {file}: {e}")
        
        # Language mapping
        lang_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.java': 'Java', '.go': 'Go', '.rb': 'Ruby',
            '.php': 'PHP', '.cs': 'C#', '.cpp': 'C++', '.c': 'C',
            '.rs': 'Rust', '.swift': 'Swift', '.kt': 'Kotlin'
        }
        
        for ext, count in summary["by_extension"].items():
            lang = lang_map.get(ext, 'Other')
            summary["by_language"][lang] = summary["by_language"].get(lang, 0) + count
        
        summary["total_size_kb"] = round(summary["total_size_kb"], 2)
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
    
    return summary

# ==================== Main Scan Function ====================
def scan_repository(repo_url: str, config: Optional[ScanConfig] = None) -> ScanResult:
    """
    Main function to scan a repository for secrets and vulnerabilities
    
    Args:
        repo_url: URL of the git repository
        config: Optional ScanConfig object
    
    Returns:
        ScanResult object with all findings
    """
    import time
    
    if config is None:
        config = ScanConfig()
    
    start_time = time.time()
    repo_name = sanitize_repo_name(repo_url)
    errors = []
    
    logger.info(f"Starting scan for repository: {repo_url}")
    
    try:
        with temp_repo_context(repo_url, config) as repo_path:
            # Clone repository
            success, error_msg = clone_repository(repo_url, repo_path, config.default_timeout)
            if not success:
                return ScanResult(
                    repo_name=repo_name,
                    repo_url=repo_url,
                    status="failed",
                    secrets=[],
                    dependencies={},
                    summary={},
                    errors=[f"Clone failed: {error_msg}"],
                    scan_duration=time.time() - start_time
                )
            
            # Run secret scan
            logger.info("Starting secret scan...")
            secret_results = run_secret_scan(repo_path, config)
            
            # Run dependency scan
            logger.info("Starting dependency scan...")
            dependency_results = run_dependency_scan(repo_path, config)
            
            # Generate summary
            logger.info("Generating repository summary...")
            summary = generate_repo_summary(repo_path)
            
            # Collect all errors
            errors.extend(secret_results.get("errors", []))
            
            scan_duration = time.time() - start_time
            
            result = ScanResult(
                repo_name=repo_name,
                repo_url=repo_url,
                status="completed",
                secrets=secret_results["findings"],
                dependencies=dependency_results,
                summary=summary,
                errors=errors,
                scan_duration=scan_duration
            )
            
            logger.info(f"Scan completed in {scan_duration:.2f}s - Found {len(result.secrets)} secrets")
            return result
            
    except Exception as e:
        logger.error(f"Scan failed with exception: {e}", exc_info=True)
        return ScanResult(
            repo_name=repo_name,
            repo_url=repo_url,
            status="error",
            secrets=[],
            dependencies={},
            summary={},
            errors=[f"Scan error: {str(e)}"],
            scan_duration=time.time() - start_time
        )

# ==================== Backward Compatibility ====================
# Maintain backward compatibility with old function names
def clone_repo(repo_url: str, name: str) -> str:
    """
    Backward compatible wrapper for clone_repository
    
    Args:
        repo_url: Repository URL
        name: Repository name (will be sanitized)
    
    Returns:
        Path to cloned repository
    """
    repo_path = os.path.join(BASE_PATH, name)
    os.makedirs(BASE_PATH, exist_ok=True)
    
    success, error_msg = clone_repository(repo_url, repo_path)
    if not success:
        raise RuntimeError(error_msg)
    
    return repo_path

def repo_summary(repo_path: str) -> Dict:
    """Backward compatible wrapper for generate_repo_summary"""
    return generate_repo_summary(repo_path)

def dependency_scan(repo_path: str, timeout: int = DEFAULT_TIMEOUT) -> Dict:
    """Backward compatible wrapper for run_dependency_scan"""
    config = ScanConfig(default_timeout=timeout)
    return run_dependency_scan(repo_path, config)

def run_secret_scan_legacy(repo_path: str, max_file_bytes: int = MAX_FILE_SIZE) -> List[str]:
    """
    Backward compatible wrapper that returns list of strings like the old version
    
    Args:
        repo_path: Path to repository
        max_file_bytes: Maximum file size to scan
    
    Returns:
        List of finding strings
    """
    config = ScanConfig(max_file_size=max_file_bytes)
    results = run_secret_scan(repo_path, config)
    
    # Convert findings to old string format
    findings = []
    
    # Add TruffleHog results
    findings.extend(results.get("trufflehog_results", []))
    
    # Convert SecretFinding objects to strings
    for finding in results.get("findings", []):
        finding_str = f"Possible {finding.secret_type} in {finding.file_path}"
        if finding.line_number > 0:
            finding_str += f" (line {finding.line_number})"
        findings.append(finding_str)
    
    return findings

# ==================== Public API ====================
__all__ = [
    # Main functions
    'scan_repository',
    'clone_repository',
    'run_secret_scan',
    'run_dependency_scan',
    'generate_repo_summary',
    
    # Configuration
    'ScanConfig',
    'ScanResult',
    'SecretFinding',
    
    # Backward compatibility
    'clone_repo',
    'repo_summary',
    'dependency_scan',
    
    # Utilities
    'validate_repo_url',
    'sanitize_repo_name',
    'setup_logging',
]

# ==================== CLI Entry Point ====================
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Repository Security Scanner")
    parser.add_argument("repo_url", help="Git repository URL to scan")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel scanning")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker threads")
    parser.add_argument("--timeout", type=int, default=120, help="Scan timeout in seconds")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.log_level)
    
    # Create config
    config = ScanConfig(
        enable_parallel=not args.no_parallel,
        max_workers=args.workers,
        default_timeout=args.timeout,
        log_level=args.log_level
    )
    
    # Run scan
    result = scan_repository(args.repo_url, config)
    
    # Output results
    result_dict = result.to_dict()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result_dict, f, indent=2)
        logger.info(f"Results written to {args.output}")
    else:
        print(json.dumps(result_dict, indent=2))
    
    # Exit code based on findings
    if result.status == "failed" or result.status == "error":
        sys.exit(1)
    elif len(result.secrets) > 0:
        sys.exit(2)  # Secrets found
    else:
        sys.exit(0)