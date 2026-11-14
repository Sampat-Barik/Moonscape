import { AlertIcon, RefreshIcon } from "./icons";

/** ErrorState — meaningful error panel with optional retry action. */
export default function ErrorState({
  title = "Request failed",
  message,
  onRetry,
  retryLabel = "Retry",
  className,
}: {
  title?: string;
  message: string | null | undefined;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}) {
  return (
    <div className={`panel panel-bad p-4 ${className ?? ""}`} role="alert">
      <div className="flex items-start gap-3">
        <AlertIcon className="mt-0.5 h-5 w-5 shrink-0 text-bad" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-bad">{title}</p>
          {message && <p className="mt-1 break-words text-[13px] text-muted">{message}</p>}
          {onRetry && (
            <button className="btn-ghost mt-3 !px-3 !py-1.5 !text-xs" onClick={onRetry}>
              <RefreshIcon className="h-3.5 w-3.5" /> {retryLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
