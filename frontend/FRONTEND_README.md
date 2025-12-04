# RepoGuard Scanner - Frontend Documentation

## 🚀 Quick Start

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

## 🎨 UI Features

### Modern Design

- **Dark theme** with glassmorphism effects
- **Animated gradients** and blob backgrounds
- **Smooth animations** for all interactions
- **Responsive layout** that works on all devices

### Key Components

#### 1. **SearchBar** (`components/SearchBar.jsx`)

- Search GitHub users and repositories
- Filter by:
  - Sort order (updated, created, pushed, name)
  - Include/exclude forked repositories
- Real-time search with Enter key support

#### 2. **RepoCard** (`components/RepoCard.jsx`)

- Display repository information
- Show repository stats (language, stars, size)
- Initiate scans with one-click
- Show scan status with visual indicators
- Display repository link to GitHub

#### 3. **ScanStatusModal** (`components/ScanStatusModal.jsx`)

- Real-time scan status updates
- Display comprehensive scan results
- Tab-based interface for different report sections
- Export results as JSON
- Copy results to clipboard

#### 4. **ScanResults** (`components/ScanResults.jsx`)

- **Overview Tab**: Total issues, scan duration, repo stats
- **Secrets Tab**: Display detected secrets with severity levels
- **Dependencies Tab**: Python, Node.js, and tool versions
- **Code Quality Tab**: Code quality analysis results

## 🔄 API Integration

The frontend communicates with the backend at `http://localhost:8000`

### Key Endpoints Used

#### Fetch Repositories

```
GET /repos/{username}
Query Parameters:
  - sort: "updated" | "created" | "pushed" | "full_name"
  - include_forks: boolean
  - per_page: 1-100
```

#### Initiate Scan

```
POST /scan
Body:
{
  "repo_url": "string",
  "repo_name": "string",
  "enable_parallel": boolean,
  "max_workers": number,
  "timeout": number,
  "redact_secrets": boolean
}
Response:
{
  "scan_id": "string",
  "status": "queued",
  "message": "string"
}
```

#### Check Scan Status

```
GET /scan/{scan_id}/status
Response:
{
  "scan_id": "string",
  "status": "queued" | "scanning" | "completed" | "failed",
  "timestamp": "ISO string",
  "message": "string"
}
```

#### Get Scan Results

```
GET /scan/{scan_id}/result
Response: (ScanResult object with all findings)
```

#### Delete Scan Results

```
DELETE /scan/{scan_id}
```

## 📊 Scan Results Structure

```json
{
  "repo_name": "string",
  "repo_url": "string",
  "status": "completed" | "failed",
  "secrets": [
    {
      "file_path": "string",
      "line_number": "number",
      "secret_type": "string",
      "pattern": "string",
      "context": "string (redacted)",
      "severity": "HIGH" | "MEDIUM" | "LOW"
    }
  ],
  "dependencies": {
    "python": { "status": "string", "findings": [], "files": [] },
    "node": { "status": "string", "findings": [], "files": [] },
    "code_quality": { "findings": [], "errors": [] },
    "tool_versions": { "pip-audit": "string", ... }
  },
  "summary": {
    "total_size_kb": "number",
    "file_count": "number",
    "directory_count": "number",
    "by_extension": { "ext": "count" },
    "by_language": { "lang": "count" },
    "sensitive_files": ["string"]
  },
  "errors": ["string"],
  "scan_duration": "number"
}
```

## 🎯 Polling Implementation

The frontend automatically polls scan results every 2 seconds until completion:

1. **Initiate scan** → Get `scan_id`
2. **Add to active scans** → Trigger polling
3. **Poll status endpoint** → Get current status
4. **On completion** → Fetch full results
5. **Remove from active scans** → Stop polling

## 🎨 Styling

- **Framework**: Tailwind CSS v4
- **Color Scheme**: Dark slate with vibrant accents
- **Animations**: Custom keyframes for smooth transitions
- **Responsive**: Mobile-first design

### Tailwind Extensions

Added custom animations in `index.css`:

- `animate-blob`: Floating background animation
- `animate-slideDown`: Entrance animation
- `animate-slideUp`: Modal entrance animation
- `animate-fadeIn`: Fade entrance animation

## 🔐 Security Features

- Input validation on search
- URL validation for repositories
- Error handling with user-friendly messages
- Secure API communication
- Automatic secret redaction in display

## 📱 Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## 🐛 Troubleshooting

### Backend Not Responding

```
Error: Failed to fetch repositories
→ Ensure backend is running at http://localhost:8000
→ Check CORS configuration
```

### API Rate Limit

```
Error: GitHub API rate limit exceeded
→ Wait for 1 hour or authenticate with GitHub token
```

### Scan Stuck on "Scanning"

```
→ Check backend logs for errors
→ Try refreshing the page
→ Delete the scan and retry
```

## 📦 Dependencies

```json
{
  "react": "^19.2.0",
  "react-dom": "^19.2.0",
  "axios": "^1.13.2",
  "tailwindcss": "^4.1.17"
}
```

## 🚀 Performance Tips

1. **Parallel Scanning**: Enable `enable_parallel` for faster scans
2. **Batch Scans**: Use multiple worker threads (max 10)
3. **Timeout Settings**: Adjust based on repository size
4. **Caching**: Results are cached in memory (cleared on refresh)

## 📝 Future Improvements

- [ ] Scan history with local storage persistence
- [ ] Multiple scan comparison
- [ ] Custom alert thresholds
- [ ] Integration with CI/CD pipelines
- [ ] Scheduled scans
- [ ] Team collaboration features
- [ ] Advanced filtering and search
- [ ] Export to multiple formats (PDF, CSV)

## 📄 License

MIT - See LICENSE file for details
