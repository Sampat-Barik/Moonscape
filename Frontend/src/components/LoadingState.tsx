/** LoadingState — spinner + label shown while an API request is in flight. */
export default function LoadingState({
  label = "Loading…",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-3 text-muted ${className ?? ""}`} role="status">
      <span className="spinner" aria-hidden="true" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
