import { InfoIcon } from "./icons";

/**
 * DataUnavailable — shown whenever the backend returned null for a dataset.
 * Rule: a null is NEVER rendered as zero or as a fabricated number.
 */
export default function DataUnavailable({
  label = "Data unavailable",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[13px] font-medium text-warn ${className ?? ""}`}
    >
      <InfoIcon className="h-4 w-4 shrink-0" />
      {label}
    </span>
  );
}
