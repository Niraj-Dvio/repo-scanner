export default function LoadingSpinner({
  message = "Loading...",
  size = "md",
}) {
  const sizes = {
    sm: "w-6 h-6",
    md: "w-12 h-12",
    lg: "w-16 h-16",
  };

  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <div
        className={`${sizes[size]} border-4 border-slate-700 border-t-blue-400 rounded-full animate-spin`}
      ></div>
      {message && (
        <p className="text-gray-300 font-medium text-center">{message}</p>
      )}
    </div>
  );
}
