# Frontend Integration Guide

## 🚀 Setup Instructions

### Step 1: Ensure Backend is Running

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Backend will run on `http://localhost:8000`

### Step 2: Install Frontend Dependencies

```bash
cd frontend
npm install
```

### Step 3: Start Frontend Development Server

```bash
npm run dev
```

Frontend will run on `http://localhost:5173`

## 🔗 API Connection Flow

### 1. Fetch Repositories

User enters GitHub username → Frontend fetches repositories list → Display cards

### 2. Initiate Scan

User clicks "Scan" → POST request to `/scan` → Get `scan_id` → Start polling

### 3. Poll Scan Status

Every 2 seconds:

- Check `/scan/{scan_id}/status`
- If `completed` or `failed`, fetch `/scan/{scan_id}/result`
- Stop polling and display results

### 4. View Results

Results displayed in modal with tabs:

- Overview (stats, duration)
- Secrets (found secrets with severity)
- Dependencies (Python, Node.js, tools)
- Code Quality (Semgrep, Bandit results)

## 🎨 UI Components Architecture

```
App.jsx (Main)
├── SearchBar (User input)
├── RepoCard × N (Repository display)
│   ├── ScanResults (Results preview)
│   └── Status indicators
└── ScanStatusModal (Full results view)
    └── ScanResults (Full display)
```

## 📡 State Management

### Active Scans

```javascript
// Track which scans are running
const [activeScans, setActiveScans] = useState(new Set());

// Add to set when scan starts
setActiveScans((prev) => new Set([...prev, scanId]));

// Remove from set when complete
setActiveScans((prev) => {
  const newSet = new Set(prev);
  newSet.delete(scanId);
  return newSet;
});
```

### Scan Statuses

```javascript
// Store all scan states
const [scanStatuses, setScanStatuses] = useState({});

// Format: { scan_id: { status: "queued|scanning|completed|failed", results: {} } }
setScanStatuses((prev) => ({
  ...prev,
  [scanId]: { status, results },
}));
```

## 🔄 Real-time Updates

The frontend uses a polling mechanism instead of WebSockets for simplicity:

1. **Polling Interval**: 2 seconds
2. **Active Scans**: Only poll active scans
3. **Cleanup**: Remove completed scans from polling
4. **Auto-update**: Results update in real-time

## 🎯 Key Features Implemented

### ✅ Responsive Design

- Mobile-first approach
- Works on all screen sizes
- Smooth animations

### ✅ Dark Theme

- Glassmorphism effects
- Animated gradients
- Easy on the eyes

### ✅ Real-time Scanning

- Live status updates
- Progress indicators
- Auto-refresh results

### ✅ Comprehensive Results

- 4 tabs for different report sections
- JSON export capability
- Copy-to-clipboard
- Severity indicators

### ✅ Error Handling

- User-friendly error messages
- Network error recovery
- Validation feedback

### ✅ Advanced Search

- Sort by various criteria
- Filter forks
- Quick filters

## 🔧 Customization

### Change API URL

In `App.jsx`, line 7:

```javascript
const API_BASE_URL = "http://localhost:8000";
// Change to your backend URL
```

### Change Polling Interval

In `App.jsx`, line 10:

```javascript
const POLL_INTERVAL = 2000; // milliseconds
// Change to adjust polling frequency
```

### Change Color Scheme

Edit Tailwind classes throughout components or modify `tailwind.config.js`

### Modify Component Styling

All components use Tailwind CSS - edit className properties to customize look

## 🐛 Common Issues & Solutions

### Issue: CORS Error

```
Access to XMLHttpRequest blocked by CORS
```

**Solution**: Ensure backend has proper CORS configuration

```python
# In backend/main.py
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000"
]
```

### Issue: Scan Status Not Updating

```
Scan stuck on "scanning"
```

**Solutions**:

1. Check backend logs for errors
2. Verify API endpoints are correct
3. Check network tab in browser DevTools
4. Refresh page to reset polling

### Issue: No Results After Scan Completes

```
Modal shows "Scanning..." even after completion
```

**Solutions**:

1. Check browser console for errors
2. Verify `/scan/{scan_id}/result` endpoint works
3. Check backend for scan completion

## 📊 Performance Optimization

### Frontend

- Virtual scrolling for large repo lists (can add)
- Result caching (implemented in-memory)
- Lazy loading of components

### Backend

- Parallel scanning (enabled by default)
- Configurable worker threads (max 10)
- Timeout settings per scan

## 🚀 Deployment

### Build for Production

```bash
npm run build
```

### Serve Build

```bash
npm run preview
```

### Deploy to Vercel

```bash
npm install -g vercel
vercel
```

### Deploy to Netlify

```bash
npm run build
# Deploy the 'dist' folder to Netlify
```

## 📝 Environment Variables

Create `.env` file in frontend root:

```env
VITE_API_URL=http://localhost:8000
VITE_POLL_INTERVAL=2000
```

Then update App.jsx to use:

```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const POLL_INTERVAL = import.meta.env.VITE_POLL_INTERVAL || 2000;
```

## 🔒 Security Best Practices

1. **Never store secrets** in frontend code
2. **Always validate input** before sending to backend
3. **Sanitize output** to prevent XSS
4. **Use HTTPS** in production
5. **Implement rate limiting** on backend
6. **Validate API responses** for integrity

## 📈 Monitoring

### Browser DevTools

- Network tab: Monitor API calls
- Console: Check for errors/warnings
- Performance: Measure load times

### Backend Logs

```bash
# Stream logs from backend
tail -f security_scan.log
```

## 🤝 Integration Checklist

- [ ] Backend running on port 8000
- [ ] Frontend running on port 5173
- [ ] CORS properly configured
- [ ] API endpoints tested with Postman
- [ ] Environment variables set
- [ ] All dependencies installed
- [ ] No console errors
- [ ] Network requests successful
- [ ] Scans completing successfully
- [ ] Results displaying correctly

## 📞 Support

For issues or questions:

1. Check the troubleshooting section
2. Review backend logs
3. Check browser console
4. Verify API endpoints with curl/Postman
5. Check network requests in DevTools

## 🎓 Learning Resources

- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Axios Documentation](https://axios-http.com)
- [FastAPI Documentation](https://fastapi.tiangolo.com)

---

**Last Updated**: December 2025
**Version**: 2.0.0
**Status**: Production Ready
