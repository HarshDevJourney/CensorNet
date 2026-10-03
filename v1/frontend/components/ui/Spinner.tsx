export default function Spinner({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <div
      role="presentation"
      className={`animate-spin rounded-full border-2 border-white/30 border-t-white ${className}`}
    />
  );
}
