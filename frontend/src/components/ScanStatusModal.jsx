import { useState } from "react";
import ScanResults from "./ScanResults";

const statusConfig = {
  queued: { color: "yellow", icon: "⏳", text: "Queued" },
  scanning: { color: "blue", icon: "🔄", text: "Scanning" },
  completed: { color: "green", icon: "✅", text: "Completed" },
  failed: { color: "red", icon: "❌", text: "Failed" },
};

export default function ScanStatusModal({
  scanId,
  scanData,
  onClose,
  onDelete,
}) {
  const { status, results } = scanData;
  const config = statusConfig[status] || statusConfig.queued;
  const colorMap = {
    yellow: {
      bg: "bg-yellow-500/20",
      border: "border-yellow-500",
      text: "text-yellow-400",
    },
    blue: {
      bg: "bg-blue-500/20",
      border: "border-blue-500",
      text: "text-blue-400",
    },
    green: {
      bg: "bg-green-500/20",
      border: "border-green-500",
      text: "text-green-400",
    },
    red: {
      bg: "bg-red-500/20",
      border: "border-red-500",
      text: "text-red-400",
    },
  };

  const colorStyles = colorMap[config.color];
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(JSON.stringify(results, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fadeIn">
      <div className="bg-slate-900 border border-white/20 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl animate-slideUp">
        {/* Header */}
        <div
          className={`sticky top-0 border-b ${colorStyles.border} ${colorStyles.bg} p-6 flex items-start justify-between gap-4 z-10`}
        >
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-3xl">{config.icon}</span>
              <h2 className="text-2xl font-bold text-white">Scan Results</h2>
            </div>
            <p className={`text-sm font-mono ${colorStyles.text}`}>{scanId}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Status Badge */}
          <div
            className={`${colorStyles.bg} border ${colorStyles.border} rounded-xl p-4 flex items-center justify-between`}
          >
            <div>
              <p className={`text-sm font-semibold ${colorStyles.text}`}>
                Status
              </p>
              <p className="text-white text-lg font-bold mt-1">
                {config.text.charAt(0).toUpperCase() + config.text.slice(1)}
              </p>
            </div>
            <span className="text-4xl animate-pulse">{config.icon}</span>
          </div>

          {/* Results */}
          {status === "completed" && results ? (
            <>
              <ScanResults data={results} />

              {/* Repository Info */}
              {results.repo_name && (
                <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <h3 className="text-sm font-bold text-white mb-3">
                    📋 Repository Information
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Repository:</span>
                      <span className="text-white font-mono">
                        {results.repo_name}
                      </span>
                    </div>
                    {results.repo_url && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">URL:</span>
                        <a
                          href={results.repo_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 font-mono truncate"
                        >
                          {results.repo_url}
                        </a>
                      </div>
                    )}
                    {results.scan_duration && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">Scan Duration:</span>
                        <span className="text-white">
                          {results.scan_duration.toFixed(2)}s
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Export Options */}
              <div className="flex gap-3">
                <button
                  onClick={copyToClipboard}
                  className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
                >
                  {copied ? "✓ Copied!" : "📋 Copy JSON"}
                </button>
                <button
                  onClick={() => {
                    const element = document.createElement("a");
                    element.setAttribute(
                      "href",
                      "data:text/json;charset=utf-8," +
                        encodeURIComponent(JSON.stringify(results, null, 2))
                    );
                    element.setAttribute("download", `scan-${scanId}.json`);
                    element.style.display = "none";
                    document.body.appendChild(element);
                    element.click();
                    document.body.removeChild(element);
                  }}
                  className="flex-1 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
                >
                  ⬇️ Download JSON
                </button>
              </div>
            </>
          ) : status === "failed" ? (
            <div className="bg-red-500/20 border border-red-500 rounded-xl p-6 text-center">
              <p className="text-red-300 text-lg font-semibold mb-2">
                Scan Failed
              </p>
              {results?.error && (
                <p className="text-red-200 text-sm mb-4">{results.error}</p>
              )}
              <button
                onClick={onClose}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg transition"
              >
                Close
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-blue-500/20 border border-blue-500 rounded-xl p-6">
                <div className="flex items-center gap-3 justify-center">
                  <div className="w-8 h-8 border-4 border-blue-300 border-t-blue-500 rounded-full animate-spin"></div>
                  <p className="text-blue-300 font-semibold">
                    Scan in progress...
                  </p>
                </div>
              </div>

              {/* Scanning tips */}
              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <p className="text-xs font-semibold text-gray-300 mb-2">
                  💡 Tip:
                </p>
                <p className="text-xs text-gray-400">
                  This modal will automatically update as the scan progresses.
                  You can close it and view the results later from the
                  repository card.
                </p>
              </div>
            </div>
          )}

          {/* Delete Button */}
          {(status === "completed" || status === "failed") && (
            <div className="pt-4 border-t border-white/10">
              <button
                onClick={onDelete}
                className="w-full px-4 py-2 bg-red-500/20 border border-red-500 hover:bg-red-500/30 text-red-400 font-semibold rounded-lg transition"
              >
                🗑️ Delete Scan Results
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
