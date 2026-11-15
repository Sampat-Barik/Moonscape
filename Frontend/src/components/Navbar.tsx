import { useCallback, useEffect, useState } from "react";
import type { Route } from "@/hooks/useHashRoute";
import { useApp } from "@/context/AppContext";
import LogoMark from "./Logo";
import { MenuIcon, MoonIcon, SunIcon, XIcon } from "./icons";

const LINKS: { route: Route; label: string }[] = [
  { route: "/", label: "Home" },
  { route: "/explorer", label: "Lunar Explorer" },
  { route: "/dashboard", label: "Analysis" },
  { route: "/hazards", label: "Hazards" },
  { route: "/compare", label: "Comparison" },
  { route: "/report", label: "Report" },
  { route: "/credits", label: "Credits" },
];

export default function Navbar({
  route,
  navigate,
}: {
  route: Route;
  navigate: (r: Route) => void;
}) {
  const { mode, cycleMode } = useApp();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [contrastMode, setContrastMode] = useState<"standard" | "high-contrast">("standard");

  const toggleTheme = useCallback(() => {
    setContrastMode((prev) => {
      const next = prev === "standard" ? "high-contrast" : "standard";
      if (next === "high-contrast") {
        document.documentElement.classList.add("high-contrast");
      } else {
        document.documentElement.classList.remove("high-contrast");
      }
      return next;
    });
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const close = useCallback(() => setOpen(false), []);

  // Close mobile menu on Escape
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, close]);

  const modeColor =
    mode === "live" ? "bg-good" : mode === "mock" ? "bg-warn" : "bg-muted animate-blink";
  const modeLabel = mode === "live" ? "LIVE" : mode === "mock" ? "MOCK" : "…";

  const isHome = route === "/";

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 h-16 box-border transition-all duration-200 ${
        !isHome || scrolled
          ? "border-b border-divider/80 bg-space/95 backdrop-blur-md shadow-xs"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2.5 shrink-0 cursor-pointer"
          aria-label="Moonscape home"
        >
          <LogoMark className="h-8 w-8" />
          <span className="font-display text-sm font-semibold tracking-[0.22em] text-ink">
            MOONSCAPE
          </span>
        </button>

        {/* Desktop nav — centered */}
        <nav className="hidden flex-1 items-center justify-center gap-0.5 xl:gap-2 lg:flex">
          {LINKS.map((l) => (
            <button
              key={l.route}
              onClick={() => navigate(l.route)}
              className={`relative px-2.5 xl:px-3 py-1.5 font-mono text-[0.7rem] xl:text-[0.72rem] tracking-[0.1em] uppercase transition-colors duration-150 cursor-pointer ${
                route === l.route
                  ? "text-ink font-semibold"
                  : "text-muted hover:text-ink"
              }`}
            >
              {l.label}
              {route === l.route && (
                <span className="absolute inset-x-2 -bottom-[1px] h-[2px] bg-ink" />
              )}
            </button>
          ))}
        </nav>

        {/* Right controls: data status + theme control */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Data status */}
          <button
            onClick={cycleMode}
            title="Toggle between the live backend and mock data"
            className="flex items-center gap-2 border border-divider/60 bg-surface/40 px-2.5 py-1 text-[0.65rem] font-mono tracking-[0.1em] text-muted hover:border-accent/40 hover:text-ink transition-colors rounded-xs"
          >
            <span className={`h-1.5 w-1.5 rounded-full ${modeColor}`} />
            <span>DATA: {modeLabel}</span>
          </button>

          {/* Theme control */}
          <button
            onClick={toggleTheme}
            title={`Switch to ${contrastMode === "standard" ? "High-Contrast / Radar" : "Standard"} visual profile`}
            className="flex items-center gap-1.5 border border-divider/60 bg-surface/40 px-2.5 py-1 text-[0.65rem] font-mono tracking-[0.08em] text-muted hover:border-accent/40 hover:text-ink transition-colors rounded-xs"
          >
            {contrastMode === "standard" ? (
              <MoonIcon className="h-3 w-3 text-cyan" />
            ) : (
              <SunIcon className="h-3 w-3 text-warn" />
            )}
            <span className="hidden sm:inline">
              {contrastMode === "standard" ? "OPTICAL" : "HI-CONTRAST"}
            </span>
          </button>

          {/* Mobile menu toggle */}
          <button
            className="flex h-9 w-9 items-center justify-center text-muted hover:text-ink lg:hidden transition-colors"
            onClick={() => setOpen((v) => !v)}
            aria-label="Toggle menu"
            aria-expanded={open}
          >
            {open ? <XIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="glass-soft mx-4 mb-4 rounded-md lg:hidden">
          <nav className="flex flex-col py-2">
            {LINKS.map((l) => (
              <button
                key={l.route}
                onClick={() => {
                  close();
                  navigate(l.route);
                }}
                className={`px-5 py-3 text-left font-mono text-xs uppercase tracking-wider transition-colors ${
                  route === l.route
                    ? "text-ink bg-white/[0.06] font-medium"
                    : "text-muted hover:text-ink hover:bg-white/[0.03]"
                }`}
              >
                {l.label}
              </button>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
