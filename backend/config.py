"""Configuration module for security scanner"""
import logging
from dataclasses import dataclass


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
    generate_lockfile: bool = True
    
    # Scanner toggles
    enable_trufflehog: bool = True
    enable_pip_audit: bool = True
    enable_safety: bool = True
    enable_npm_audit: bool = True
    enable_snyk: bool = True
    enable_semgrep: bool = True
    enable_bandit: bool = True


# Legacy constants for backward compatibility
BASE_PATH = ScanConfig().base_path
DEFAULT_TIMEOUT = ScanConfig().default_timeout
MAX_FILE_SIZE = ScanConfig().max_file_size


def setup_logging(name: str = "__name__", level: str = "INFO") -> logging.Logger:
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
    )
    return logging.getLogger(name)
