"""Code quality scanning plugin using Semgrep and Bandit"""
import os
import json
import subprocess
import logging
from models import DependencyResult
from .utils import check_tool_version

logger = logging.getLogger(__name__)


def has_python_files(repo_path: str) -> bool:
    """Check if repository has Python source files"""
    python_exts = {'.py'}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', '.git', 'dist', 'build'}]
        for file in files:
            if os.path.splitext(file)[1] in python_exts:
                return True
    return False


def has_javascript_files(repo_path: str) -> bool:
    """Check if repository has JavaScript/TypeScript source files"""
    js_exts = {'.js', '.ts', '.jsx', '.tsx'}
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '__pycache__', '.git', 'dist', 'build'}]
        for file in files:
            if os.path.splitext(file)[1] in js_exts:
                return True
    return False


def scan_code_quality(repo_path: str, config) -> DependencyResult:
    """Scan code quality using Semgrep and Bandit"""
    result = DependencyResult(applicable=False, status="not_applicable")
    
    # Check if applicable (has Python or JS files)
    has_python = has_python_files(repo_path)
    has_javascript = has_javascript_files(repo_path)
    
    if not has_python and not has_javascript:
        return result
    
    result.applicable = True
    result.status = "scanned"
    
    # Run Semgrep if enabled
    if config.enable_semgrep:
        logger.info("Running Semgrep...")
        try:
            semgrep_result = subprocess.run(
                ["semgrep", "--json", "--quiet", "."],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=config.default_timeout
            )
            
            if semgrep_result.stdout:
                try:
                    data = json.loads(semgrep_result.stdout)
                    findings = data.get("results", [])
                    if findings:
                        result.findings.append({"tool": "semgrep", "count": len(findings), "results": findings[:10]})
                except json.JSONDecodeError:
                    result.errors.append("semgrep output not JSON")
            
            if semgrep_result.returncode != 0 and semgrep_result.stderr:
                result.errors.append(f"semgrep: {semgrep_result.stderr.strip()}")
        except FileNotFoundError:
            result.errors.append("semgrep not installed")
        except Exception as e:
            result.errors.append(f"semgrep failed: {str(e)}")
    
    # Run Bandit on Python files if enabled
    if config.enable_bandit and has_python:
        logger.info("Running Bandit...")
        try:
            bandit_result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=config.default_timeout
            )
            
            if bandit_result.stdout:
                try:
                    data = json.loads(bandit_result.stdout)
                    results = data.get("results", [])
                    if results:
                        result.findings.append({"tool": "bandit", "count": len(results), "results": results[:10]})
                except json.JSONDecodeError:
                    pass
            
            if bandit_result.returncode != 0 and bandit_result.stderr:
                result.errors.append(f"bandit: {bandit_result.stderr.strip()}")
        except FileNotFoundError:
            result.errors.append("bandit not installed")
        except Exception as e:
            result.errors.append(f"bandit failed: {str(e)}")
    
    result.tool_versions["semgrep"] = check_tool_version("semgrep")
    result.tool_versions["bandit"] = check_tool_version("bandit")
    
    return result
