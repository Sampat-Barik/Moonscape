import type { ReactNode } from "react";

/** PageHeader — consistent page heading with kicker, title, subtitle and actions. */
export default function PageHeader({
  kicker,
  title,
  subtitle,
  children,
}: {
  kicker: string;
  title: string;
  subtitle?: string;
  children?: ReactNode;
}) {
  return (
    <div className="mb-10 flex flex-wrap items-end justify-between gap-6">
      <div>
        <p className="kicker">{kicker}</p>
        <h1 className="mt-3 font-display text-3xl font-bold tracking-[-0.01em] text-ink sm:text-4xl">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">{subtitle}</p>
        )}
      </div>
      {children}
    </div>
  );
}
