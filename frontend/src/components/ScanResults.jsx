import { useState } from "react";

export default function ScanResults({ data }) {
  const [activeTab, setActiveTab] = useState("overview");

  if (!data) return null;

  const { summary, secrets, dependencies } = data;
  const hasSecrets = secrets && secrets.length > 0;
  const hasPythonIssues = dependencies?.python?.findings?.length > 0;
  const hasNodeIssues = dependencies?.node?.findings?.length > 0;
  const hasCodeQualityIssues = dependencies?.code_quality?.findings?.length > 0;

  const totalIssues =
    (secrets?.length || 0) +
    (dependencies?.python?.findings?.length || 0) +
    (dependencies?.node?.findings?.length || 0) +
    (dependencies?.code_quality?.findings?.length || 0);

  const severityColors = {
    HIGH: "text-red-400 bg-red-500/20 border-red-500",
    MEDIUM: "text-yellow-400 bg-yellow-500/20 border-yellow-500",
    LOW: "text-blue-400 bg-blue-500/20 border-blue-500",
  };

  const tabs = [
    { id: "overview", label: "📊 Overview", icon: "overview" },
    {
      id: "secrets",
      label: `🔐 Secrets (${secrets?.length || 0})`,
      icon: "secrets",
    },
    { id: "dependencies", label: `📦 Dependencies`, icon: "deps" },
    { id: "code", label: `🔍 Code Quality`, icon: "code" },
  ];

  return (
    <div className="space-y-4 bg-white/5 border border-white/10 rounded-xl p-4 backdrop-blur-sm">
      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-white/10 pb-3 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 rounded-lg text-sm font-semibold transition whitespace-nowrap ${
              activeTab === tab.id
                ? "bg-blue-500 text-white"
                : "text-gray-300 hover:text-white hover:bg-white/10"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="space-y-3">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              {/* Total Issues */}
              <div className="bg-linear-to-br from-red-500/20 to-red-600/10 border border-red-500/50 rounded-lg p-4">
                <div className="text-sm font-semibold text-red-300 mb-1">
                  Total Issues
                </div>
                <div className="text-3xl font-bold text-red-400">
                  {totalIssues}
                </div>
              </div>

              {/* Scan Duration */}
              <div className="bg-linear-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/50 rounded-lg p-4">
                <div className="text-sm font-semibold text-blue-300 mb-1">
                  Scan Duration
                </div>
                <div className="text-3xl font-bold text-blue-400">
                  {(data.scan_duration || 0).toFixed(1)}s
                </div>
              </div>
            </div>

            {/* Summary Stats */}
            {summary && (
              <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                <h4 className="text-sm font-bold text-white mb-3">
                  Repository Stats
                </h4>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-gray-400">Total Size</span>
                    <p className="text-blue-300 font-bold">
                      {(summary.total_size_kb / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-400">Files</span>
                    <p className="text-purple-300 font-bold">
                      {summary.file_count}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-400">Directories</span>
                    <p className="text-cyan-300 font-bold">
                      {summary.directory_count}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-400">Languages</span>
                    <p className="text-green-300 font-bold">
                      {Object.keys(summary.by_language || {}).length}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Secrets Tab */}
        {activeTab === "secrets" && (
          <div className="space-y-2">
            {hasSecrets ? (
              <>
                <div className="bg-red-500/20 border border-red-500 rounded-lg p-3">
                  <p className="text-red-300 text-sm font-semibold">
                    ⚠️ {secrets.length} potential secret(s) found
                  </p>
                </div>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {secrets.map((secret, idx) => (
                    <div
                      key={idx}
                      className={`border rounded-lg p-3 text-xs font-mono ${
                        severityColors[secret.severity] || severityColors.MEDIUM
                      }`}
                    >
                      <div className="flex justify-between items-start gap-2 mb-2">
                        <span className="font-bold">{secret.secret_type}</span>
                        <span className="px-2 py-1 rounded bg-white/10 border border-current text-xs">
                          {secret.severity}
                        </span>
                      </div>
                      <div className="text-gray-300 mb-1">
                        📄 {secret.file_path}
                        {secret.line_number > 0 && `:${secret.line_number}`}
                      </div>
                      <div className="text-gray-400 break-all">
                        {secret.context}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="bg-green-500/20 border border-green-500 rounded-lg p-4 text-center">
                <p className="text-green-300 font-semibold">
                  ✅ No secrets detected
                </p>
                <p className="text-green-300/70 text-sm mt-1">
                  Your repository appears to be secure
                </p>
              </div>
            )}
          </div>
        )}

        {/* Dependencies Tab */}
        {activeTab === "dependencies" && (
          <div className="space-y-3">
            {/* Python */}
            {dependencies?.python?.applicable && (
              <div className="border border-white/10 rounded-lg p-3 bg-white/5">
                <h4 className="text-sm font-bold text-blue-300 mb-2">
                  🐍 Python Dependencies
                </h4>
                {dependencies.python.errors?.length > 0 ? (
                  <div className="space-y-1 text-xs text-yellow-300">
                    {dependencies.python.errors.map((error, idx) => (
                      <p key={idx}>⚠️ {error}</p>
                    ))}
                  </div>
                ) : dependencies.python.findings?.length > 0 ? (
                  <div className="text-xs text-orange-300">
                    🔍 {dependencies.python.findings.length} vulnerabilities
                    found
                  </div>
                ) : (
                  <p className="text-xs text-green-400">
                    ✅ No vulnerabilities detected
                  </p>
                )}
              </div>
            )}

            {/* Node.js */}
            {dependencies?.node?.applicable && (
              <div className="border border-white/10 rounded-lg p-3 bg-white/5">
                <h4 className="text-sm font-bold text-yellow-300 mb-2">
                  📦 Node.js Dependencies
                </h4>
                {dependencies.node.errors?.length > 0 ? (
                  <div className="space-y-1 text-xs text-yellow-300">
                    {dependencies.node.errors.map((error, idx) => (
                      <p key={idx}>⚠️ {error}</p>
                    ))}
                  </div>
                ) : dependencies.node.findings?.length > 0 ? (
                  <div className="text-xs text-orange-300">
                    🔍 {dependencies.node.findings.length} vulnerabilities found
                  </div>
                ) : (
                  <p className="text-xs text-green-400">
                    ✅ No vulnerabilities detected
                  </p>
                )}
              </div>
            )}

            {/* Tool Versions */}
            {dependencies?.tool_versions && (
              <div className="border border-white/10 rounded-lg p-3 bg-white/5">
                <h4 className="text-sm font-bold text-purple-300 mb-2">
                  🛠️ Scan Tools
                </h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(dependencies.tool_versions).map(
                    ([tool, version]) => (
                      <div key={tool} className="text-gray-300">
                        <span className="font-mono">{tool}</span>:{" "}
                        <span className="text-gray-400">
                          {version === "not installed" ? "❌" : "✅"}
                        </span>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Code Quality Tab */}
        {activeTab === "code" && (
          <div className="space-y-2">
            {dependencies?.code_quality?.applicable ? (
              dependencies.code_quality.errors?.length > 0 ? (
                <div className="bg-yellow-500/20 border border-yellow-500 rounded-lg p-3">
                  <p className="text-yellow-300 text-sm font-semibold">
                    ⚠️ Code Quality Scan Issues
                  </p>
                  <div className="mt-2 space-y-1 text-xs text-yellow-300/80">
                    {dependencies.code_quality.errors.map((error, idx) => (
                      <p key={idx}>• {error}</p>
                    ))}
                  </div>
                </div>
              ) : dependencies.code_quality.findings?.length > 0 ? (
                <div className="bg-orange-500/20 border border-orange-500 rounded-lg p-3">
                  <p className="text-orange-300 text-sm font-semibold">
                    🔍 {dependencies.code_quality.findings.length} Code Quality
                    Issue(s)
                  </p>
                  <p className="text-orange-300/70 text-xs mt-1">
                    Review findings for improvements
                  </p>
                </div>
              ) : (
                <div className="bg-green-500/20 border border-green-500 rounded-lg p-4 text-center">
                  <p className="text-green-300 font-semibold">
                    ✅ Code Quality Clean
                  </p>
                  <p className="text-green-300/70 text-sm mt-1">
                    No critical code quality issues detected
                  </p>
                </div>
              )
            ) : (
              <div className="bg-gray-500/20 border border-gray-500 rounded-lg p-4 text-center">
                <p className="text-gray-300 font-semibold">
                  ℹ️ Code Quality Not Applicable
                </p>
                <p className="text-gray-300/70 text-sm mt-1">
                  No Python or JavaScript source files detected
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
