import { useState } from "react";

export default function SearchBar({ onFetch, isLoading }) {
  const [username, setUsername] = useState("");
  const [sortBy, setSortBy] = useState("updated");
  const [includeForks, setIncludeForks] = useState(false);

  const handleFetch = () => {
    if (username.trim()) {
      onFetch(username, sortBy, includeForks);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !isLoading) {
      handleFetch();
    }
  };

  return (
    <div className="mb-8 animate-fadeIn">
      <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded-2xl p-8 shadow-2xl">
        {/* Main Search */}
        <div className="flex gap-3 mb-4">
          <div className="flex-1 relative group">
            <div className="absolute inset-0 bg-linear-to-r from-blue-500 to-purple-500 rounded-xl blur opacity-0 group-hover:opacity-75 transition duration-300"></div>
            <input
              className="relative w-full border border-white/20 bg-white/5 backdrop-blur-sm px-5 py-3 rounded-xl outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/50 transition text-white placeholder-gray-400"
              type="text"
              placeholder="Enter GitHub username (e.g., torvalds)..."
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
            />
          </div>

          <button
            onClick={handleFetch}
            disabled={isLoading || !username.trim()}
            className={`relative px-8 py-3 rounded-xl font-bold text-white transition-all duration-300 whitespace-nowrap overflow-hidden group ${
              isLoading || !username.trim()
                ? "bg-gray-600 cursor-not-allowed opacity-50"
                : "bg-linear-to-r from-blue-500 to-purple-600 hover:shadow-lg hover:shadow-blue-500/50 active:scale-95"
            }`}
          >
            <div className="absolute inset-0 bg-white/20 transform -skew-x-12 group-hover:translate-x-full transition-transform duration-500"></div>
            <span className="relative flex items-center gap-2 justify-center">
              {isLoading ? (
                <>
                  <span className="inline-block animate-spin">⏳</span>
                  Fetching...
                </>
              ) : (
                <>
                  <span>🔍</span> Search Repos
                </>
              )}
            </span>
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 items-center justify-between pt-4 border-t border-white/10">
          <div className="flex gap-4 flex-wrap">
            {/* Sort By */}
            <div className="flex items-center gap-2">
              <label className="text-sm font-semibold text-gray-300">
                Sort by:
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                disabled={isLoading}
                className="bg-white/5 border border-white/20 text-white text-sm px-3 py-2 rounded-lg outline-none focus:border-blue-400 transition"
              >
                <option value="updated">Last Updated</option>
                <option value="created">Recently Created</option>
                <option value="pushed">Last Pushed</option>
                <option value="full_name">Name (A-Z)</option>
              </select>
            </div>

            {/* Include Forks */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeForks}
                onChange={(e) => setIncludeForks(e.target.checked)}
                disabled={isLoading}
                className="w-4 h-4 rounded cursor-pointer"
              />
              <span className="text-sm font-medium text-gray-300">
                Include forks
              </span>
            </label>
          </div>

          {/* Quick Stats */}
          <div className="text-xs text-gray-400">
            💡 Tip: Use keyboard shortcut Enter to search
          </div>
        </div>
      </div>
    </div>
  );
}
