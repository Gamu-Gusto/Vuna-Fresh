// Statuses are plain words, not pills. Colour is reserved for meaning:
// green when something is finished, amber when someone needs to act,
// red when it went wrong, and ordinary text for everything in between.
const TONES = {
  done: 'text-brand-green',
  action: 'text-amber-800',
  problem: 'text-ember',
  normal: 'text-gray-800',
  quiet: 'text-gray-500',
};

export default function StatusText({ label, tone = 'normal', className = '' }) {
  return <span className={`text-sm font-medium whitespace-nowrap ${TONES[tone] ?? TONES.normal} ${className}`}>{label}</span>;
}
