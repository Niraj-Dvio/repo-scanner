import { useState } from "react";
import ScanResults from "./ScanResults";

const statusColors = {
  completed: {
    bg: "bg-green-500/20",
    border: "border-green-500",
    text: "text-green-400",
    icon: "✅",
  },
  failed: {
    bg: "bg-red-500/20",
    border: "border-red-500",
    text: "text-red-400",
    icon: "❌",
  },
  scanning: {
    bg: "bg-blue-500/20",
    border: "border-blue-500",
    text: "text-blue-400",
    icon: "🔄",
  },
  queued: {
    bg: "bg-yellow-500/20",
    border: "border-yellow-500",
    text: "text-yellow-400",
    icon: "⏳",
  },
};

export default function RepoCard({
  repo,
  onScan,
  scanStatus,
  isScanning,
  onViewResults,
  onDelete,
  index,
}) {
  const [showResults, setShowResults] = useState(false);
  const hasResults = scanStatus?.results;
  const status = scanStatus?.status;
  const scanId = scanStatus?.scan_id;
  const statusConfig = statusColors[status] || statusColors.queued;

  const handleScan = () => {
    onScan(repo);
  };

  const handleViewResults = () => {
    setShowResults(true);
    onViewResults(repo.name);
  };

  return (
    <div
      className="group animate-fadeIn h-full"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div
        className={`relative h-full backdrop-blur-md border rounded-xl overflow-hidden transition-all duration-300 hover:shadow-2xl hover:shadow-blue-500/20 ${
          status
            ? statusConfig.border + " border-opacity-50"
            : "border-white/10"
        }`}
      >
        {/* Status indicator bar */}
        {status && (
          <div
            className={`h-1 w-full bg-linear-to-r ${statusConfig.text}`}
          ></div>
        )}

        <div className="bg-white/5 backdrop-blur-sm p-6 h-full flex flex-col">
          {/* Header */}
          <div className="mb-4">
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex-1">
                <h3 className="text-xl font-bold text-white group-hover:text-blue-300 transition">
                  {repo.name}
                </h3>
                {status && (
                  <div
                    className={`inline-block mt-2 px-2 py-1 rounded-full text-xs font-semibold ${statusConfig.bg} ${statusConfig.text} border ${statusConfig.border}`}
                  >
                    {statusConfig.icon}{" "}
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </div>
                )}
              </div>
            </div>

            <p className="text-sm text-gray-400 line-clamp-2 group-hover:text-gray-300 transition">
              {repo.description || "No description provided"}
            </p>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className="bg-white/5 border border-white/10 rounded-lg p-3 hover:bg-white/10 transition">
              <div className="text-xs font-semibold text-gray-400 mb-1">
                Language
              </div>
              <p className="text-sm font-bold text-blue-300">
                {repo.language || "—"}
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-lg p-3 hover:bg-white/10 transition">
              <div className="text-xs font-semibold text-gray-400 mb-1">
                ⭐ Stars
              </div>
              <p className="text-sm font-bold text-yellow-300">
                {repo.stars > 999
                  ? (repo.stars / 1000).toFixed(1) + "k"
                  : repo.stars}
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-lg p-3 hover:bg-white/10 transition">
              <div className="text-xs font-semibold text-gray-400 mb-1">
                Size
              </div>
              <p className="text-sm font-bold text-purple-300">
                {(repo.size / 1024).toFixed(1)}M
              </p>
            </div>
          </div>

          {/* Repo Link */}
          <a
            href={repo.html}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-400 hover:text-blue-300 underline mb-4 truncate"
          >
            🔗 View on GitHub
          </a>

          {/* Actions */}
          <div className="flex gap-2 mt-auto pt-4 border-t border-white/10">
            <button
              onClick={handleScan}
              disabled={isScanning}
              className={`flex-1 relative px-4 py-2 rounded-lg font-semibold text-sm transition-all duration-200 overflow-hidden group/btn ${
                isScanning
                  ? "bg-gray-600 cursor-not-allowed opacity-50"
                  : hasResults
                  ? "bg-linear-to-r from-purple-500 to-pink-500 hover:shadow-lg hover:shadow-purple-500/50"
                  : "bg-linear-to-r from-blue-500 to-cyan-500 hover:shadow-lg hover:shadow-blue-500/50"
              } text-white`}
            >
              <div className="absolute inset-0 bg-white/20 transform -skew-x-12 group-hover/btn:translate-x-full transition-transform duration-300"></div>
              <span className="relative flex items-center justify-center gap-2">
                {isScanning ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    Scanning...
                  </>
                ) : hasResults ? (
                  <>🔄 Rescan</>
                ) : (
                  <>🚀 Scan</>
                )}
              </span>
            </button>

            {hasResults && (
              <button
                onClick={() => {
                  handleViewResults();
                  onViewResults(scanId);
                }}
                className="flex-1 px-4 py-2 rounded-lg font-semibold text-sm bg-white/10 border border-white/20 text-white hover:bg-white/20 transition"
              >
                📊 Results
              </button>
            )}
          </div>

          {/* Results Preview */}
          {hasResults && showResults && (
            <div className="mt-4 pt-4 border-t border-white/10">
              <ScanResults data={hasResults} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
