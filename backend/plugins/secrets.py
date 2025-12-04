"""Secret scanning plugin using patterns and TruffleHog"""
import re
import json
import subprocess
import logging
import os
from typing import List, Dict
from models import SecretFinding
from .utils import is_text_file

logger = logging.getLogger(__name__)

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
    
    # Database
    (re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-@]{8,})"), "Password"),
    (re.compile(r"(?i)(db_password|database_password)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-@]{8,})"), "DB Password"),
    
    # Tokens
    (re.compile(r"(?i)(token|auth_token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{20,})"), "Auth Token"),
    (re.compile(r"(?i)(bearer|authorization)\s*[:=]\s*['\"]?Bearer\s+([a-zA-Z0-9_\-\.]{20,})"), "Bearer Token"),
    
    # Private Keys
    (re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PRIVATE) (?:PRIVATE KEY|KEY)-----"), "Private Key Header"),
]

SENSITIVE_EXTENSIONS = {
    ".env", ".key", ".pem", ".jks", ".p12", ".crt", ".cer",
    ".properties", ".credentials", ".config", ".yaml", ".yml",
    ".json", ".xml", ".ini", ".toml", ".conf"
}

SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "credentials", "secrets", "password", "token", "apikey",
    "aws_credentials", "gcp_credentials", "azure_credentials",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"
}

SOURCE_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.go', '.rb', '.php', '.cs', '.scala', '.kt', '.swift', '.cpp', '.c'}


def scan_file_for_secrets(file_path: str, file_name: str, redact: bool = True) -> List[SecretFinding]:
    """Scan a single file for secrets"""
    findings = []
    
    if not is_text_file(file_path):
        return findings
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for pattern, pattern_type in SECRET_PATTERNS:
                for match in pattern.finditer(line):
                    # Try to extract the actual secret value
                    matched_value = match.group(0)
                    if match.groups():
                        # Use the last capture group as the secret
                        matched_value = match.group(match.lastindex or 0) if match.lastindex else match.group(0)
                    
                    context = line if not redact else f"...{matched_value[:10]}***..."
                    
                    findings.append(SecretFinding(
                        secret_type=pattern_type,
                        severity="HIGH",
                        file_path=file_path,
                        line_number=line_num,
                        context=context,
                        start=match.start(),
                        end=match.end(),
                        matched_value=matched_value if not redact else matched_value[:10] + "***",
                        provider="pattern"
                    ))
    except Exception as e:
        logger.debug(f"Error scanning {file_path}: {e}")
    
    return findings


def run_trufflehog_scan(repo_path: str) -> List[Dict]:
    """Run TruffleHog scan on repository"""
    findings = []
    
    try:
        result = subprocess.run(
            ["trufflehog", "filesystem", repo_path, "--json"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        findings.append(data)
                    except json.JSONDecodeError:
                        pass
        
        logger.info(f"TruffleHog found {len(findings)} issues")
    except FileNotFoundError:
        logger.debug("TruffleHog not installed")
    except Exception as e:
        logger.error(f"TruffleHog scan failed: {e}")
    
    return findings


def run_secret_scan(repo_path: str, config) -> List[SecretFinding]:
    """Run complete secret scan"""
    findings = []
    
    # TruffleHog scan
    if config.enable_trufflehog:
        logger.info("Running TruffleHog scan...")
        # TODO: Integrate trufflehog findings
        run_trufflehog_scan(repo_path)
    
    # Pattern-based scanning
    logger.info("Scanning sensitive files...")
    sensitive_files = get_sensitive_files(repo_path, config)
    
    for file_path in sensitive_files:
        file_findings = scan_file_for_secrets(file_path, os.path.basename(file_path), config.redact_secrets)
        findings.extend(file_findings)
    
    # Deduplicate findings
    findings = dedupe_findings(findings)
    logger.info(f"Found {len(findings)} unique secrets")
    
    return findings


def get_sensitive_files(repo_path: str, config) -> List[str]:
    """Get list of sensitive files to scan"""
    sensitive_files = []
    
    try:
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden and common non-essential directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', '.git', 'dist', 'build'}]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_name = os.path.basename(file)
                
                # Check sensitive filenames
                if file_name in SENSITIVE_FILENAMES:
                    sensitive_files.append(file_path)
                    continue
                
                # Check file extension
                _, ext = os.path.splitext(file_name)
                if ext in SENSITIVE_EXTENSIONS:
                    sensitive_files.append(file_path)
                    continue
                
                # Check source files if enabled
                if config.scan_source_files and ext in SOURCE_EXTENSIONS:
                    sensitive_files.append(file_path)
    except Exception as e:
        logger.error(f"Error getting sensitive files: {e}")
    
    return sensitive_files


def dedupe_findings(findings: List[SecretFinding]) -> List[SecretFinding]:
    """Deduplicate findings by file, line, and match span"""
    deduped = {}
    
    for finding in findings:
        key = (finding.file_path, finding.line_number, finding.start, finding.end)
        if key not in deduped:
            deduped[key] = finding
        else:
            # Prefer more specific finding (with provider label)
            existing = deduped[key]
            if finding.provider != "pattern" and existing.provider == "pattern":
                deduped[key] = finding
    
    return list(deduped.values())
