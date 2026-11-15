/** Moonscape logo mark — refined crescent in a clean ring. */
export default function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="moonscape-lg" x1="6" y1="6" x2="42" y2="42">
          <stop stopColor="#FFFFFF" />
          <stop offset="1" stopColor="#777777" />
        </linearGradient>
      </defs>
      <circle cx="24" cy="24" r="20.5" stroke="url(#moonscape-lg)" strokeWidth="1.5" opacity="0.8" />
      <path d="M31.5 11.5a14 14 0 1 0 5 22.5A16.5 16.5 0 0 1 31.5 11.5z" fill="url(#moonscape-lg)" />
      <circle cx="34.5" cy="12.5" r="1.8" fill="#FFFFFF" opacity="0.9" />
    </svg>
  );
}
