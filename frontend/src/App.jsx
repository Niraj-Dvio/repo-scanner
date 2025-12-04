import { useState, useEffect } from "react";
import axios from "axios";
import SearchBar from "./components/SearchBar";
import RepoCard from "./components/RepoCard";
import ScanStatusModal from "./components/ScanStatusModal";

const API_BASE_URL = "http://localhost:8000";

// Polling interval in milliseconds
const POLL_INTERVAL = 2000;

export default function App() {
  const [repos, setRepos] = useState([]);
  const [scanStatuses, setScanStatuses] = useState({}); // { repo_name: { scan_id, status, results } }
  const [isFetching, setIsFetching] = useState(false);
  const [activeScans, setActiveScans] = useState(new Set()); // Track active scan IDs
  const [error, setError] = useState("");
  const [selectedScanId, setSelectedScanId] = useState(null); // For modal

  // Polling function for scan results
  useEffect(() => {
    const pollIntervals = [];

    activeScans.forEach((scanId) => {
      const interval = setInterval(async () => {
        try {
          // Check status
          const statusRes = await axios.get(
            `${API_BASE_URL}/scan/${scanId}/status`
          );
          const { status } = statusRes.data;

          setScanStatuses((prev) => ({
            ...prev,
            [scanId]: { ...prev[scanId], status },
          }));

          // If completed or failed, fetch results
          if (status === "completed" || status === "failed") {
            try {
              const resultRes = await axios.get(
                `${API_BASE_URL}/scan/${scanId}/result`
              );
              setScanStatuses((prev) => ({
                ...prev,
                [scanId]: { status, results: resultRes.data },
              }));
            } catch (err) {
              console.error("Error fetching results:", err);
            }

            // Remove from active scans
            setActiveScans((prev) => {
              const newSet = new Set(prev);
              newSet.delete(scanId);
              return newSet;
            });
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      }, POLL_INTERVAL);

      pollIntervals.push(interval);
    });

    // Cleanup
    return () => {
      pollIntervals.forEach((interval) => clearInterval(interval));
    };
  }, [activeScans]);

  const fetchRepos = async (
    username,
    sortBy = "updated",
    includeForks = false
  ) => {
    if (!username.trim()) {
      setError("Please enter a valid username");
      return;
    }

    setIsFetching(true);
    setError("");
    try {
      const res = await axios.get(`${API_BASE_URL}/repos/${username}`, {
        params: {
          sort: sortBy,
          include_forks: includeForks,
          per_page: 100,
        },
      });
      setRepos(res.data.repos || []);
      if (res.data.repos.length === 0) {
        setError("No repositories found for this user");
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError(`User "${username}" not found on GitHub`);
      } else if (err.response?.status === 429) {
        setError("GitHub API rate limit exceeded. Please try again later.");
      } else {
        setError(err.response?.data?.detail || "Failed to fetch repositories");
      }
      setRepos([]);
    } finally {
      setIsFetching(false);
    }
  };

  const initiateRepoScan = async (repo) => {
    setError("");
    try {
      const res = await axios.post(`${API_BASE_URL}/scan`, {
        repo_url: repo.url,
        repo_name: repo.name,
        enable_parallel: true,
        max_workers: 4,
        timeout: 300,
        redact_secrets: true,
      });

      const { scan_id, status } = res.data;

      // Initialize scan status mapped to repo name
      setScanStatuses((prev) => ({
        ...prev,
        [repo.name]: { scan_id, status, results: null },
      }));

      // Add to active scans
      setActiveScans((prev) => new Set([...prev, scan_id]));

      // Set as selected
      setSelectedScanId(scan_id);
    } catch (err) {
      setError(
        `Failed to start scan: ${err.response?.data?.detail || err.message}`
      );
    }
  };

  const deleteScanResult = async (scanId) => {
    try {
      await axios.delete(`${API_BASE_URL}/scan/${scanId}`);
      setScanStatuses((prev) => {
        const newStatuses = { ...prev };
        delete newStatuses[scanId];
        return newStatuses;
      });
    } catch (err) {
      console.error("Error deleting scan:", err);
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
        <div className="absolute top-40 right-10 w-72 h-72 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-10 left-1/2 w-72 h-72 bg-pink-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="mb-6 inline-block">
            <div className="text-6xl font-black bg-clip-text text-transparent bg-linear-to-r from-blue-400 via-purple-400 to-pink-400 animate-pulse">
              🔐 RepoGuard Scanner
            </div>
          </div>
          <p className="text-gray-300 text-lg max-w-2xl mx-auto">
            Scan your GitHub repositories for security vulnerabilities, secrets,
            and dependency issues with advanced AI-powered analysis
          </p>
        </div>

        {/* Search Bar */}
        <SearchBar onFetch={fetchRepos} isLoading={isFetching} />

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-100 flex items-center gap-2 backdrop-blur-sm animate-slideDown">
            <span className="text-2xl">⚠️</span>
            <div>
              <p className="font-semibold">Error</p>
              <p className="text-sm text-red-200">{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isFetching && (
          <div className="flex justify-center items-center py-16">
            <div className="text-center">
              <div className="inline-block mb-4">
                <div className="w-16 h-16 border-4 border-purple-300 border-t-blue-400 rounded-full animate-spin"></div>
              </div>
              <p className="text-gray-300 font-semibold text-lg">
                Fetching repositories...
              </p>
            </div>
          </div>
        )}

        {/* Repos Grid */}
        {!isFetching && repos.length > 0 && (
          <div className="animate-fadeIn">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">Repositories</h2>
                <p className="text-gray-400 mt-1">
                  Found{" "}
                  <span className="font-bold text-blue-400">
                    {repos.length}
                  </span>{" "}
                  repositories
                </p>
              </div>
              <div className="text-right">
                <div className="inline-block px-4 py-2 bg-linear-to-r from-blue-500/20 to-purple-500/20 rounded-full border border-blue-400/30">
                  <span className="text-sm font-semibold text-blue-300">
                    Active Scans:{" "}
                    <span className="text-blue-400">{activeScans.size}</span>
                  </span>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {repos.map((repo, index) => (
                <RepoCard
                  key={repo.name}
                  repo={repo}
                  onScan={initiateRepoScan}
                  scanStatus={scanStatuses[repo.name] || null}
                  isScanning={activeScans.has(scanStatuses[repo.name]?.scan_id)}
                  onViewResults={(scanId) => setSelectedScanId(scanId)}
                  onDelete={deleteScanResult}
                  index={index}
                />
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isFetching && repos.length === 0 && !error && (
          <div className="flex justify-center items-center py-24">
            <div className="text-center">
              <div className="text-7xl mb-6 animate-bounce">🔍</div>
              <h3 className="text-2xl font-bold text-white mb-2">
                Ready to scan?
              </h3>
              <p className="text-gray-400 text-lg max-w-md">
                Enter a GitHub username above to analyze your repositories for
                security vulnerabilities and code quality issues
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Scan Status Modal */}
      {selectedScanId && scanStatuses[selectedScanId] && (
        <ScanStatusModal
          scanId={selectedScanId}
          scanData={scanStatuses[selectedScanId]}
          onClose={() => setSelectedScanId(null)}
          onDelete={() => {
            deleteScanResult(selectedScanId);
            setSelectedScanId(null);
          }}
        />
      )}
    </div>
  );
}
