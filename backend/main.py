from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
import uvicorn
import logging
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import from enhanced scanner
from scanner import (
    scan_repository,
    ScanConfig,
    validate_repo_url,
    sanitize_repo_name,
    setup_logging,
    # Backward compatible imports
    clone_repo,
    run_secret_scan_legacy,
    dependency_scan,
    repo_summary
)

# Setup logging
logger = setup_logging("INFO")

app = FastAPI(
    title="Repository Security Scanner API",
    description="Scan GitHub repositories for secrets and vulnerabilities",
    version="2.0.0"
)

# ---------------- CORS ----------------
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- In-Memory Storage for Scan Results ----------------
scan_results_cache: Dict[str, Dict] = {}
scan_status_cache: Dict[str, str] = {}

# Thread pool for background scans
executor = ThreadPoolExecutor(max_workers=3)

# ---------------- MODELS ----------------
class ScanRequest(BaseModel):
    repo_url: str = Field(..., description="Git repository URL")
    repo_name: Optional[str] = Field(None, description="Repository name (auto-generated if not provided)")
    
    # Advanced options
    enable_parallel: bool = Field(True, description="Enable parallel scanning")
    max_workers: int = Field(4, ge=1, le=10, description="Number of worker threads")
    timeout: int = Field(120, ge=30, le=600, description="Scan timeout in seconds")
    redact_secrets: bool = Field(True, description="Redact found secrets in output")
    
    @validator('repo_url')
    def validate_url(cls, v):
        is_valid, error_msg = validate_repo_url(v)
        if not is_valid:
            raise ValueError(f"Invalid repository URL: {error_msg}")
        return v

class ScanResponse(BaseModel):
    scan_id: str
    status: str
    message: str

class RepoInfo(BaseModel):
    name: str
    url: str
    html: str
    language: Optional[str]
    stars: int
    description: Optional[str]
    updated_at: Optional[str]
    size: int

# ---------------- Health Check ----------------
@app.get("/")
def root():
    return {
        "service": "Repository Security Scanner",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "repos": "/repos/{username}",
            "scan": "/scan",
            "scan_status": "/scan/{scan_id}/status",
            "scan_result": "/scan/{scan_id}/result"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_scans": len([s for s in scan_status_cache.values() if s == "scanning"])
    }

# ---------------- GET REPOS ----------------
@app.get("/repos/{username}", response_model=Dict[str, List[RepoInfo]])
def get_repos(
    username: str,
    per_page: int = 30,
    sort: str = "updated",
    include_forks: bool = False
):
    """
    Fetch repositories for a GitHub user
    
    Args:
        username: GitHub username
        per_page: Number of repos per page (max 100)
        sort: Sort by (created, updated, pushed, full_name)
        include_forks: Include forked repositories
    """
    try:
        url = f"https://api.github.com/users/{username}/repos"
        params = {
            "per_page": min(per_page, 100),
            "sort": sort,
            "direction": "desc"
        }
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Repository-Security-Scanner"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        elif response.status_code == 403:
            raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded")
        elif response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="GitHub API error")
        
        repos = response.json()
        
        # Filter forks if needed
        if not include_forks:
            repos = [repo for repo in repos if not repo.get("fork")]
        
        results = [{
            "name": repo["name"],
            "url": repo["clone_url"],
            "html": repo["html_url"],
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0),
            "description": repo.get("description"),
            "updated_at": repo.get("updated_at"),
            "size": repo.get("size", 0)
        } for repo in repos]
        
        logger.info(f"Fetched {len(results)} repositories for user '{username}'")
        
        return {"repos": results}
    
    except requests.RequestException as e:
        logger.error(f"Failed to fetch repos for {username}: {e}")
        raise HTTPException(status_code=503, detail="GitHub API unavailable")
    except Exception as e:
        logger.error(f"Unexpected error fetching repos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------- SCAN REPO (Legacy - Synchronous) ----------------
@app.post("/scan/legacy")
def scan_repo_legacy(scan_req: ScanRequest):
    """
    Legacy synchronous scan endpoint (blocks until complete)
    Use /scan for async scanning with better error handling
    """
    try:
        repo_name = scan_req.repo_name or sanitize_repo_name(scan_req.repo_url)
        
        logger.info(f"Starting legacy scan for {repo_name}")
        
        # Clone repository
        repo_path = clone_repo(scan_req.repo_url, repo_name)
        
        # Run scans
        secrets = run_secret_scan_legacy(repo_path)
        deps = dependency_scan(repo_path, timeout=scan_req.timeout)
        summary = repo_summary(repo_path)
        
        result = {
            "repo": repo_name,
            "repo_url": scan_req.repo_url,
            "summary": summary,
            "secrets": secrets,
            "dependencies": deps,
            "scan_completed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Legacy scan completed for {repo_name}")
        return result
        
    except Exception as e:
        logger.error(f"Legacy scan failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

# ---------------- SCAN REPO (New - Asynchronous) ----------------
def run_scan_background(scan_id: str, repo_url: str, config: ScanConfig):
    """Background task to run repository scan"""
    try:
        scan_status_cache[scan_id] = "scanning"
        logger.info(f"Background scan started for {scan_id}")
        
        # Run the scan
        result = scan_repository(repo_url, config)
        
        # Store results
        scan_results_cache[scan_id] = result.to_dict()
        scan_status_cache[scan_id] = "completed"
        
        logger.info(f"Background scan completed for {scan_id}")
        
    except Exception as e:
        logger.error(f"Background scan failed for {scan_id}: {e}", exc_info=True)
        scan_status_cache[scan_id] = "failed"
        scan_results_cache[scan_id] = {
            "error": str(e),
            "status": "failed"
        }

@app.post("/scan", response_model=ScanResponse)
async def scan_repo_async(scan_req: ScanRequest, background_tasks: BackgroundTasks):
    """
    Initiate an asynchronous repository scan
    
    Returns a scan_id that can be used to check status and retrieve results
    """
    try:
        # Generate scan ID
        repo_name = scan_req.repo_name or sanitize_repo_name(scan_req.repo_url)
        scan_id = f"{repo_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Create scan config
        config = ScanConfig(
            enable_parallel=scan_req.enable_parallel,
            max_workers=scan_req.max_workers,
            default_timeout=scan_req.timeout,
            redact_secrets=scan_req.redact_secrets
        )
        
        # Initialize status
        scan_status_cache[scan_id] = "queued"
        
        # Submit to background
        background_tasks.add_task(run_scan_background, scan_id, scan_req.repo_url, config)
        
        logger.info(f"Scan queued: {scan_id}")
        
        return ScanResponse(
            scan_id=scan_id,
            status="queued",
            message=f"Scan initiated for {repo_name}. Use /scan/{scan_id}/status to check progress."
        )
        
    except Exception as e:
        logger.error(f"Failed to queue scan: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate scan: {str(e)}")

@app.get("/scan/{scan_id}/status")
def get_scan_status(scan_id: str):
    """Get the status of a scan"""
    if scan_id not in scan_status_cache:
        raise HTTPException(status_code=404, detail="Scan ID not found")
    
    status = scan_status_cache[scan_id]
    response = {
        "scan_id": scan_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if status == "completed":
        response["message"] = "Scan completed. Use /scan/{scan_id}/result to retrieve results."
    elif status == "failed":
        response["message"] = "Scan failed. Check results endpoint for error details."
    elif status == "scanning":
        response["message"] = "Scan in progress..."
    else:
        response["message"] = "Scan queued..."
    
    return response

@app.get("/scan/{scan_id}/result")
def get_scan_result(scan_id: str):
    """Retrieve scan results"""
    if scan_id not in scan_results_cache:
        if scan_id in scan_status_cache:
            status = scan_status_cache[scan_id]
            if status in ["queued", "scanning"]:
                raise HTTPException(
                    status_code=202,
                    detail=f"Scan still {status}. Please wait and try again."
                )
        raise HTTPException(status_code=404, detail="Scan results not found")
    
    return scan_results_cache[scan_id]

@app.delete("/scan/{scan_id}")
def delete_scan_result(scan_id: str):
    """Delete scan results from cache"""
    if scan_id not in scan_results_cache and scan_id not in scan_status_cache:
        raise HTTPException(status_code=404, detail="Scan ID not found")
    
    scan_results_cache.pop(scan_id, None)
    scan_status_cache.pop(scan_id, None)
    
    return {"message": f"Scan {scan_id} deleted successfully"}

@app.get("/scans")
def list_scans():
    """List all scans in cache"""
    scans = []
    for scan_id in scan_status_cache.keys():
        scans.append({
            "scan_id": scan_id,
            "status": scan_status_cache[scan_id],
            "has_results": scan_id in scan_results_cache
        })
    return {"scans": scans, "total": len(scans)}

# ---------------- Exception Handlers ----------------
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred",
            "error": str(exc)
        }
    )

# ---------------- Startup/Shutdown Events ----------------
@app.on_event("startup")
async def startup_event():
    logger.info("Repository Security Scanner API starting up...")
    logger.info(f"CORS enabled for: {origins}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Repository Security Scanner API shutting down...")
    executor.shutdown(wait=False)

# ---------------- Main ----------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )