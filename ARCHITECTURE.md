# 🏗️ RepoGuard Scanner - Architecture & Design

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER BROWSER                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              FRONTEND (React + Tailwind)              │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │  │
│  │  │   SearchBar  │  │  RepoCard(n) │  │   Modal     │ │  │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │  │
│  │         │                 │                   │         │  │
│  │         └─────────────────┴───────────────────┘         │  │
│  │              ↓ (HTTP/Axios)                            │  │
│  │         State Management                              │  │
│  │    - repos[]                                          │  │
│  │    - scanStatuses{}                                  │  │
│  │    - activeScans Set                                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↕                                   │
│                     Polling (2s interval)                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                            ↕↑
                         HTTPS/CORS
                            ↕↑
┌─────────────────────────────────────────────────────────────┐
│                      API SERVER (FastAPI)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐ │
│  │          Request Router & CORS Middleware              │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              API Endpoint Handlers                      │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │ GET  /repos/{username}        → GitHub API      │  │ │
│  │  │ POST /scan                    → Queue Scan      │  │ │
│  │  │ GET  /scan/{id}/status        → Check Status    │  │ │
│  │  │ GET  /scan/{id}/result        → Get Results     │  │ │
│  │  │ DELETE /scan/{id}             → Cleanup         │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          Scanner Engine (Background Tasks)             │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │ 1. Clone Repository (GitPython)                 │  │ │
│  │  │ 2. Secret Scan (Regex + TruffleHog)             │  │ │
│  │  │ 3. Dependency Scan (pip-audit, npm audit)       │  │ │
│  │  │ 4. Code Quality (Semgrep, Bandit)               │  │ │
│  │  │ 5. Generate Summary                             │  │ │
│  │  │ 6. Cleanup & Cache Results                      │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           External Services & Tools                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │ │
│  │  │  GitHub API  │  │ TruffleHog   │  │    Git     │  │ │
│  │  └──────────────┘  └──────────────┘  └────────────┘  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │ │
│  │  │ pip-audit    │  │  npm audit   │  │  Semgrep   │  │ │
│  │  └──────────────┘  └──────────────┘  └────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                           ↓                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           File System & Data Storage                   │ │
│  │  ┌────────────────────────────────────────────────┐   │ │
│  │  │ /repos/ (temporary cloned repos)               │   │ │
│  │  │ security_scan.log                              │   │ │
│  │  │ In-memory cache (scan results)                 │   │ │
│  │  └────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow Diagram

### User Workflow

```
User enters
Username
    ↓
[Frontend: fetchRepos()]
    ↓
GET /repos/{username}
    ↓
[Backend: query GitHub API]
    ↓
Display Repo Cards
    ↓
User clicks "Scan"
    ↓
[Frontend: initiateRepoScan()]
    ↓
POST /scan (with repo_url)
    ↓
[Backend: scan_repository()]
    │
    ├→ [Async: run_scan_background()]
    │   ├→ clone_repository()
    │   ├→ run_secret_scan()
    │   ├→ run_dependency_scan()
    │   ├→ generate_repo_summary()
    │   └→ cache results
    │
    └→ return scan_id + "queued"
    ↓
[Frontend: Poll every 2s]
    ↓
GET /scan/{scan_id}/status
    ↓
Status: queued → scanning → completed
    ↓
[On completion]
    ↓
GET /scan/{scan_id}/result
    ↓
Display Modal with Results
    ↓
[User: View/Export/Delete]
```

## 🎯 Component Hierarchy

```
App.jsx (Main)
├── State Management
│   ├── repos[]
│   ├── scanStatuses{}
│   ├── activeScans Set
│   ├── isFetching boolean
│   └── error string
│
├── Effects
│   └── useEffect (polling logic)
│
├── Functions
│   ├── fetchRepos()
│   ├── initiateRepoScan()
│   ├── deleteScanResult()
│   └── Polling handler
│
├── SearchBar
│   ├── Props: onFetch, isLoading
│   └── State: username, sortBy, includeForks
│
├── RepoCard[] (dynamic)
│   ├── Props: repo, onScan, scanStatus, isScanning, etc.
│   ├── State: showResults
│   └── Child: ScanResults (conditional)
│
└── ScanStatusModal (conditional)
    ├── Props: scanId, scanData, onClose, onDelete
    ├── State: copied
    └── Child: ScanResults
        ├── State: activeTab
        └── Tabs: Overview, Secrets, Dependencies, CodeQuality
```

## 📊 State Management Strategy

### Global State (App.jsx)

```javascript
{
  repos: [
    { name, url, html, language, stars, description, etc. }
  ],
  scanStatuses: {
    "repo-name": {
      scan_id: "scan_id_hash",
      status: "queued|scanning|completed|failed",
      results: { full scan result object }
    }
  },
  activeScans: Set(["scan_id_1", "scan_id_2"]),
  isFetching: boolean,
  error: string,
  selectedScanId: string|null
}
```

### Component Local State

```javascript
// SearchBar
{
  username, sortBy, includeForks;
}

// RepoCard
{
  showResults;
}

// ScanStatusModal
{
  copied;
}

// ScanResults
{
  activeTab;
}
```

## 🔄 Polling Mechanism

```
App mounts
    ↓
useEffect dependency: [activeScans]
    ↓
For each scanId in activeScans:
    ├→ Create setInterval (2s)
    ├→ GET /scan/{scanId}/status
    ├→ Update scanStatuses state
    └→ If completed/failed:
        ├→ GET /scan/{scanId}/result
        ├→ Update results in scanStatuses
        └→ Remove scanId from activeScans

Every state update triggers re-render
    ↓
Components receive new props
    ↓
UI updates (modal, cards, etc.)
```

## 🛡️ Security Architecture

### Frontend Security

```
Input Validation
    ↓
URL Validation (axios)
    ↓
CORS Header Check
    ↓
Error Sanitization
    ↓
Output Encoding (React auto)
```

### Backend Security

```
Request Validation
    ├→ URL validation (validate_repo_url)
    ├→ Parameter validation (Pydantic)
    └→ Rate limiting headers
    ↓
Processing
    ├→ Redact secrets
    ├→ Sanitize error messages
    └→ Cleanup temp files
    ↓
Response
    ├→ Error serialization
    └→ Result sanitization
```

## ⚙️ Scanning Pipeline

```
[Repository URL]
    ↓
validate_repo_url()
    ↓
check_disk_space()
    ↓
clone_repository()
    │   ├→ Shallow clone (depth=1)
    │   ├→ Validate repo size
    │   └→ Handle errors
    │
├→ run_secret_scan()
│   ├→ Collect sensitive files
│   ├→ Parallel scan (ThreadPool)
│   ├→ Pattern matching
│   ├→ Redact secrets
│   ├→ Run TruffleHog
│   └→ Deduplicate findings
│
├→ run_dependency_scan()
│   ├→ scan_python_dependencies()
│   │   ├→ pip-audit
│   │   └→ safety
│   ├→ scan_node_dependencies()
│   │   ├→ npm audit
│   │   └→ snyk
│   └→ scan_code_quality()
│       ├→ Semgrep
│       └→ Bandit
│
├→ generate_repo_summary()
│   ├→ File stats
│   ├→ Extension breakdown
│   ├→ Language classification
│   └→ Sensitive files list
│
└→ Cache + Return Results
```

## 📈 Performance Characteristics

### Frontend

- **Initial Load**: ~500ms (with deps cached)
- **Repository Fetch**: 1-2s (network dependent)
- **Polling Overhead**: ~20-50ms per poll
- **Memory**: ~50-100MB base + results

### Backend

- **Scan Duration**: 30-300s (repo size dependent)
- **Clone Time**: 5-30s
- **Secret Scan**: 5-60s
- **Dependency Scan**: 10-120s
- **Memory**: ~300-500MB per concurrent scan
- **Disk**: ~100-500MB per repo (temporary)

### Network

- **GET /repos**: ~100-500KB response
- **POST /scan**: ~1KB request
- **GET /scan/status**: ~500B response
- **GET /scan/result**: ~50KB-5MB response

## 🔌 Integration Points

### Frontend ↔ Backend

```
HTTP/HTTPS
│
├─ REST API
├─ JSON payload
├─ Standard HTTP methods
└─ CORS headers
```

### Backend ↔ External

```
GitHub API
    ↓ (Rest API v3)

Git CLI
    ↓ (subprocess)

External Tools (pip-audit, npm, etc.)
    ↓ (subprocess)

File System
    ↓ (local disk)
```

## 🚀 Deployment Topology

### Development

```
localhost:5173  ← Frontend (Vite)
localhost:8000  ← Backend (FastAPI)
Both on same machine
```

### Production

```
CDN / Static Host
    ↓
Frontend (built files)

API Server (Cloud)
    ↓
Backend (FastAPI + Gunicorn)
    ↓
Scan Workers (async tasks)
```

## 📝 Design Patterns

### Frontend

- **Component Composition**: Modular React components
- **State Management**: React hooks (useState, useEffect)
- **Polling Pattern**: Timer-based status checks
- **Modal Pattern**: Context-based modal display

### Backend

- **Async Task Pattern**: Background task execution
- **Factory Pattern**: Configuration objects
- **Context Manager Pattern**: Resource cleanup
- **Strategy Pattern**: Multiple scan tool options

## 🔐 Error Handling

### Frontend

```
User Input Error
    ↓ [Validation]
API Error
    ↓ [HTTP Status Code]
    ├→ 4xx: User input error (show message)
    ├→ 5xx: Server error (show message)
    └→ Network: Connection error (retry option)
Render Error
    ↓ [Error Boundary - future]
    Display fallback UI
```

### Backend

```
Request Error
    ↓ [Validation]
Processing Error
    ↓ [Try-Except]
    ├→ Log error
    ├→ Cleanup resources
    └→ Return error response
Cleanup
    ↓ [Finally block]
    Remove temp files
```

## 📊 Testing Strategy

### Frontend (to implement)

- Unit tests: Components (Jest)
- Integration tests: API calls (Axios mock)
- E2E tests: User workflows (Cypress)

### Backend (existing)

- Unit tests: Scanner functions
- Integration tests: API endpoints
- Security tests: Secret patterns

## 🔄 Update & Deployment

### Frontend Updates

1. Update components
2. Build: `npm run build`
3. Deploy `dist/` to static host
4. Clear CDN cache

### Backend Updates

1. Update scanner.py or main.py
2. Test locally
3. Deploy to backend server
4. Restart service

### Zero Downtime

- Backend: Deploy with load balancer
- Frontend: CDN-based deployment
- API versioning (future)

---

**Document Version**: 2.0
**Last Updated**: December 2025
**Architecture Style**: Microservices (Frontend + Backend)
**Scalability**: Horizontally scalable backend
