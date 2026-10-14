// Empty lists get a plain sentence telling people what to do next — no box,
// no illustration.
export default function EmptyState({ children, className = '' }) {
  // Callers pass vertical padding (e.g. py-16) sized for the old boxed version.
  const spacing = className.replace(/py-\d+/g, '').trim();
  return <div className={`py-6 text-gray-600 ${spacing}`}>{children}</div>;
}
