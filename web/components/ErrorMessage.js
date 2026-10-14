export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
      <p>{message || 'Something went wrong.'}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-2 underline text-red-600 hover:text-red-800">
          Try again
        </button>
      )}
    </div>
  );
}
