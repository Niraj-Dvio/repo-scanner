"""Dependency scanning plugin for Python, Node.js, and other package managers"""
import os
import json
import subprocess
import logging
import tempfile
import shutil
from typing import Dict, Any
from models import DependencyResult
from .utils import check_tool_version

logger = logging.getLogger(__name__)


def scan_python_dependencies(repo_path: str, config) -> DependencyResult:
    """Scan Python project dependencies"""
    result = DependencyResult(applicable=False, status="not_applicable")
    
    # Check if Python project
    requirements_file = os.path.join(repo_path, "requirements.txt")
    setup_py = os.path.join(repo_path, "setup.py")
    pyproject_toml = os.path.join(repo_path, "pyproject.toml")
    
    has_python_project = any(os.path.exists(f) for f in [requirements_file, setup_py, pyproject_toml])
    if not has_python_project:
        return result
    
    result.applicable = True
    result.status = "scanned"
    
    # Run pip-audit if enabled
    if config.enable_pip_audit:
        logger.info("Running pip-audit...")
        try:
            pip_audit_result = subprocess.run(
                ["pip-audit", "--desc"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=config.default_timeout
            )
            if pip_audit_result.returncode != 0 and pip_audit_result.stderr:
                result.errors.append(f"pip-audit: {pip_audit_result.stderr.strip()}")
            if pip_audit_result.stdout:
                result.findings.append({"tool": "pip-audit", "output": pip_audit_result.stdout})
        except Exception as e:
            result.errors.append(f"pip-audit failed: {str(e)}")
    
    # Run safety if enabled
    if config.enable_safety:
        logger.info("Running safety...")
        try:
            safety_result = subprocess.run(
                ["safety", "check", "--json"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=config.default_timeout
            )
            if safety_result.stdout:
                try:
                    data = json.loads(safety_result.stdout)
                    if data:
                        result.findings.append({"tool": "safety", "vulnerabilities": data})
                except json.JSONDecodeError:
                    result.errors.append("safety output not JSON")
        except Exception as e:
            result.errors.append(f"safety failed: {str(e)}")
    
    result.tool_versions["pip-audit"] = check_tool_version("pip-audit")
    result.tool_versions["safety"] = check_tool_version("safety")
    
    return result


def scan_node_dependencies(repo_path: str, config) -> DependencyResult:
    """Scan Node.js project dependencies"""
    result = DependencyResult(applicable=False, status="not_applicable")
    
    package_json = os.path.join(repo_path, "package.json")
    if not os.path.exists(package_json):
        return result
    
    result.applicable = True
    result.status = "scanned"
    
    # npm audit
    if config.enable_npm_audit:
        try:
            npm_result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=config.default_timeout
            )
            
            performed_audit = False
            if npm_result.returncode != 0 and npm_result.stderr:
                result.errors.append(f"npm audit: {npm_result.stderr.strip()}")
            
            if npm_result.stdout:
                try:
                    data = json.loads(npm_result.stdout)
                    result.findings.append({
                        "tool": "npm-audit",
                        "vulnerabilities": data.get("vulnerabilities", {}),
                        "metadata": data.get("metadata", {})
                    })
                    performed_audit = True
                except json.JSONDecodeError:
                    result.findings.append({"tool": "npm-audit", "output": npm_result.stdout})
            
            # Fallback: generate package-lock in temp dir
            if not performed_audit and config.generate_lockfile:
                try:
                    tmp = tempfile.mkdtemp(prefix="npm-audit-")
                    shutil.copy(package_json, os.path.join(tmp, "package.json"))
                    pkg_lock = os.path.join(repo_path, "package-lock.json")
                    if os.path.exists(pkg_lock):
                        shutil.copy(pkg_lock, os.path.join(tmp, "package-lock.json"))
                    
                    gen = subprocess.run([
                        "npm", "install", "--package-lock-only"
                    ], cwd=tmp, capture_output=True, text=True, timeout=config.default_timeout)
                    
                    if gen.returncode == 0:
                        aud = subprocess.run([
                            "npm", "audit", "--json"
                        ], cwd=tmp, capture_output=True, text=True, timeout=config.default_timeout)
                        
                        if aud.stdout:
                            try:
                                data = json.loads(aud.stdout)
                                result.findings.append({
                                    "tool": "npm-audit",
                                    "vulnerabilities": data.get("vulnerabilities", {}),
                                    "metadata": data.get("metadata", {})
                                })
                            except json.JSONDecodeError:
                                pass
                    else:
                        if gen.stderr:
                            result.errors.append(f"npm lockfile gen: {gen.stderr.strip()}")
                    
                    shutil.rmtree(tmp, ignore_errors=True)
                except Exception as e:
                    result.errors.append(f"npm fallback failed: {str(e)}")
        except Exception as e:
            result.errors.append(f"npm audit failed: {str(e)}")
    
    # Snyk
    if config.enable_snyk:
        try:
            snyk_result = subprocess.run(
                ["snyk", "test", "--json"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=config.default_timeout
            )
            
            if snyk_result.stdout:
                try:
                    data = json.loads(snyk_result.stdout)
                    result.findings.append({"tool": "snyk", "vulnerabilities": data.get("vulnerabilities", [])})
                except json.JSONDecodeError:
                    result.findings.append({"tool": "snyk", "output": snyk_result.stdout})
        except Exception as e:
            result.errors.append(f"snyk failed: {str(e)}")
    
    result.tool_versions["npm"] = check_tool_version("npm")
    result.tool_versions["snyk"] = check_tool_version("snyk")
    
    return result


def scan_dependencies(repo_path: str, config) -> Dict[str, Any]:
    """Scan all dependencies"""
    results = {
        "python": scan_python_dependencies(repo_path, config).to_dict(),
        "node": scan_node_dependencies(repo_path, config).to_dict(),
        "code_quality": {"applicable": False, "status": "not_applicable", "findings": [], "errors": [], "tool_versions": {}},
    }
    
    return results
