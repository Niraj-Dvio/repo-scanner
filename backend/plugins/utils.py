"""Utility functions for repository scanning"""
import os
import shutil
import subprocess
import logging
from typing import Tuple, Optional
from contextlib import contextmanager
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)


def sanitize_repo_name(repo_url: str) -> str:
    """Extract and sanitize repository name from URL"""
    parsed = urlparse(repo_url)
    path = parsed.path.rstrip('/')
    repo_name = os.path.basename(path)
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    # Add hash to avoid collisions
    url_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
    return f"{repo_name}_{url_hash}".replace(' ', '_').lower()


def validate_repo_url(repo_url: str) -> Tuple[bool, Optional[str]]:
    """Validate GitHub repository URL"""
    if not repo_url or not isinstance(repo_url, str):
        return False, "Invalid repo URL"
    if not ("github.com" in repo_url or "gitlab.com" in repo_url or ".git" in repo_url):
        return False, "URL must be a valid git repository"
    return True, None


def check_disk_space(path: str, required_mb: int = 100) -> bool:
    """Check if enough disk space is available"""
    try:
        stat = shutil.disk_usage(path)
        available_mb = stat.free / (1024 * 1024)
        return available_mb >= required_mb
    except Exception:
        return True  # Assume OK if check fails


@contextmanager
def temp_repo_context(repo_url: str, base_path: str):
    """Context manager for temporary repository cloning"""
    repo_name = sanitize_repo_name(repo_url)
    repo_path = os.path.join(base_path, repo_name)
    
    try:
        # Ensure base directory exists; handle race conditions
        try:
            os.makedirs(base_path, exist_ok=True)
        except FileExistsError:
            # Race condition: another process created it between check and creation
            if not os.path.isdir(base_path):
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


def clone_repository(repo_url: str, repo_path: str, timeout: int = 300) -> Tuple[bool, str]:
    """Clone repository with validation and timeout"""
    try:
        if os.path.exists(repo_path):
            logger.warning(f"Repository path exists, removing: {repo_path}")
            shutil.rmtree(repo_path, ignore_errors=True)
        
        logger.info(f"Cloning repository: {repo_url}")
        result = subprocess.run(
            ["git", "clone", "--depth=1", "--single-branch", "-v", repo_url, repo_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully cloned repository to {repo_path}")
            return True, ""
        else:
            error = result.stderr or result.stdout
            return False, error
    except subprocess.TimeoutExpired:
        return False, f"Clone timeout after {timeout}s"
    except Exception as e:
        return False, str(e)


def check_tool_version(tool: str) -> str:
    """Check tool version with fallbacks"""
    try:
        import shutil
        
        # Try direct invocation
        tool_path = shutil.which(tool)
        if tool_path:
            result = subprocess.run(
                [tool, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        
        # Try npx fallback for Node.js tools
        if shutil.which("npx"):
            result = subprocess.run(
                ["npx", "--yes", tool, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        
        # Try python -m for Python tools
        result = subprocess.run(
            ["python", "-m", tool, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
        
        return "not installed"
    except Exception:
        return "not installed"


def is_text_file(file_path: str, sample_size: int = 512) -> bool:
    """Check if a file is text-based"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(sample_size)
            if not chunk:
                return False
            # Check for null bytes (binary indicator)
            if b'\x00' in chunk:
                return False
            # Check ratio of printable characters
            try:
                chunk.decode('utf-8', errors='strict')
                return True
            except (UnicodeDecodeError, AttributeError):
                # Try with errors='ignore' for a rough check
                text = chunk.decode('utf-8', errors='ignore')
                printable = sum(c.isprintable() or c.isspace() for c in text)
                return printable / len(text) > 0.75
    except Exception:
        return False
