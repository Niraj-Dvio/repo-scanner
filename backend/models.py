"""Data models for scanner results and API"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class SecretFinding:
    """Represents a found secret"""
    secret_type: str
    severity: str
    file_path: str
    line_number: int
    context: str
    start: int = 0
    end: int = 0
    matched_value: str = ""
    provider: str = "custom"
    
    def to_dict(self):
        data = asdict(self)
        # Truncate matched_value in output for safety
        if data["matched_value"] and len(data["matched_value"]) > 20:
            data["matched_value"] = data["matched_value"][:20] + "..."
        return data


@dataclass
class DependencyResult:
    """Result from dependency scanning"""
    applicable: bool
    status: str
    findings: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    tool_versions: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ScanResult:
    """Result from a complete repository scan"""
    repo_name: str
    repo_url: str
    status: str
    secrets: List[SecretFinding]
    dependencies: Dict[str, Any]
    summary: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    scan_duration: float = 0.0
    
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
