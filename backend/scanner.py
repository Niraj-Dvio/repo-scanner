"""Main scanning orchestration module"""
import os
import time
from typing import Dict, Any
from config import ScanConfig, setup_logging
from models import ScanResult
from plugins.utils import temp_repo_context, clone_repository, validate_repo_url, sanitize_repo_name
from plugins.secrets import run_secret_scan
from plugins.dependencies import scan_dependencies
from plugins.code_quality import scan_code_quality

logger = setup_logging(__name__)


def generate_repo_summary(repo_path: str) -> Dict[str, Any]:
    """Generate summary of repository"""
    summary = {
        "total_size_kb": 0,
        "file_count": 0,
        "directory_count": 0,
        "by_language": {}
    }
    
    language_exts = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.go': 'Go',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.cs': 'C#',
        '.cpp': 'C++',
        '.c': 'C',
    }
    
    try:
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', '.git', 'dist', 'build'}]
            summary["directory_count"] += len(dirs)
            
            for file in files:
                summary["file_count"] += 1
                file_path = os.path.join(root, file)
                try:
                    summary["total_size_kb"] += os.path.getsize(file_path) / 1024
                except OSError:
                    pass
                
                _, ext = os.path.splitext(file)
                if ext in language_exts:
                    lang = language_exts[ext]
                    summary["by_language"][lang] = summary["by_language"].get(lang, 0) + 1
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
    
    return summary


def scan_repository(repo_url: str, config: ScanConfig = None) -> ScanResult:
    """
    Scan a repository for secrets, vulnerabilities, and code quality issues
    
    Args:
        repo_url: GitHub/GitLab repository URL
        config: ScanConfig object with scanning preferences
    
    Returns:
        ScanResult with findings and summary
    """
    if config is None:
        config = ScanConfig()
    
    start_time = time.time()
    repo_name = sanitize_repo_name(repo_url)
    errors = []
    
    logger.info(f"Starting scan for repository: {repo_url}")
    
    # Validate URL
    is_valid, error_msg = validate_repo_url(repo_url)
    if not is_valid:
        return ScanResult(
            repo_name=repo_name,
            repo_url=repo_url,
            status="failed",
            secrets=[],
            dependencies={},
            summary={},
            errors=[error_msg],
            scan_duration=time.time() - start_time
        )
    
    try:
        with temp_repo_context(repo_url, config.base_path) as repo_path:
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
            
            # Run scans
            logger.info("Starting secret scan...")
            secrets = run_secret_scan(repo_path, config)
            
            logger.info("Starting dependency scan...")
            dependencies = scan_dependencies(repo_path, config)
            
            logger.info("Starting code quality scan...")
            code_quality_result = scan_code_quality(repo_path, config)
            dependencies["code_quality"] = code_quality_result.to_dict()
            
            # Generate summary
            logger.info("Generating repository summary...")
            summary = generate_repo_summary(repo_path)
            
            # Build result
            result = ScanResult(
                repo_name=repo_name,
                repo_url=repo_url,
                status="completed",
                secrets=secrets,
                dependencies=dependencies,
                summary=summary,
                errors=errors,
                scan_duration=time.time() - start_time
            )
            
            logger.info(f"Scan completed in {result.scan_duration:.2f}s - Found {len(secrets)} secrets")
            return result
    
    except Exception as e:
        logger.error(f"Scan failed with exception: {e}", exc_info=True)
        return ScanResult(
            repo_name=repo_name,
            repo_url=repo_url,
            status="failed",
            secrets=[],
            dependencies={},
            summary={},
            errors=[str(e)],
            scan_duration=time.time() - start_time
        )


# Backward compatibility exports
def clone_repo(repo_url: str, repo_path: str):
    """Legacy function"""
    return clone_repository(repo_url, repo_path)


def run_secret_scan_legacy(repo_path: str, config: ScanConfig):
    """Legacy function"""
    return run_secret_scan(repo_path, config)


def dependency_scan(repo_path: str, config: ScanConfig):
    """Legacy function"""
    return scan_dependencies(repo_path, config)


def repo_summary(repo_path: str):
    """Legacy function"""
    return generate_repo_summary(repo_path)
