export default function ErrorBoundary({ error, onRetry }) {
  return (
    <div className="min-h-screen bg-linear-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full animate-slideUp">
        <div className="bg-red-500/20 border-2 border-red-500 rounded-2xl p-8 text-center backdrop-blur-sm">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-red-300 mb-2">
            Oops! Something went wrong
          </h1>
          <p className="text-red-200 text-sm mb-4">
            {error?.message ||
              "An unexpected error occurred. Please try again."}
          </p>

          <div className="bg-red-900/30 rounded-lg p-3 mb-6 text-left">
            <p className="text-xs font-mono text-red-200 wrap-break-word">
              {error?.toString()}
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => window.location.reload()}
              className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg transition"
            >
              🔄 Reload
            </button>
            {onRetry && (
              <button
                onClick={onRetry}
                className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg transition"
              >
                🔙 Retry
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
