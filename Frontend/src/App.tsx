import { AppProvider, useApp } from "@/context/AppContext";
import { useHashRoute } from "@/hooks/useHashRoute";
import ErrorBoundary from "@/components/ErrorBoundary";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Stars from "@/components/Stars";
import Home from "@/pages/Home";
import Explorer from "@/pages/Explorer";
import Dashboard from "@/pages/Dashboard";
import Hazards from "@/pages/Hazards";
import Compare from "@/pages/Compare";
import Report from "@/pages/Report";
import Credits from "@/pages/Credits";

export default function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <Shell />
      </AppProvider>
    </ErrorBoundary>
  );
}

function Shell() {
  const [route, navigate] = useHashRoute();
  const { mode } = useApp();

  const isHome = route === "/";
  const isExplorer = route === "/explorer";

  return (
    <div className={`relative bg-space font-body text-ink ${isExplorer ? "h-screen overflow-hidden" : "min-h-screen"}`}>
      {/* Stars background — visible on all pages */}
      <Stars className="pointer-events-none fixed inset-0 z-0 opacity-50" density={150} />

      <div className={`relative z-10 flex flex-col ${isExplorer ? "h-screen overflow-hidden" : "min-h-screen"}`}>
        <Navbar route={route} navigate={navigate} />

        {/* Home manages hero offset; Explorer is full-screen 3D app; other views start cleanly below Level 1 navigation */}
        <main className={`flex-1 ${isHome ? "" : "pt-16 flex flex-col min-h-0"} ${isExplorer ? "h-[calc(100vh-4rem)] overflow-hidden" : ""}`}>
          {route === "/" && <Home navigate={navigate} />}
          {route === "/explorer" && <Explorer navigate={navigate} />}
          {route === "/dashboard" && <Dashboard navigate={navigate} />}
          {route === "/hazards" && <Hazards navigate={navigate} />}
          {route === "/compare" && <Compare navigate={navigate} />}
          {route === "/report" && <Report navigate={navigate} />}
          {route === "/credits" && <Credits navigate={navigate} />}
        </main>

        {/* No footer on Explorer (full-screen mode) */}
        {!isExplorer && <Footer />}
      </div>

      {mode === "mock" && (
        <div className="fixed bottom-4 left-4 z-50 flex items-center gap-2 rounded-sm border border-warn/30 bg-space/90 px-3 py-1.5 font-mono text-[0.65rem] tracking-[0.06em] text-warn backdrop-blur-sm">
          <span className="h-1.5 w-1.5 shrink-0 animate-blink rounded-full bg-warn" />
          DEMO MODE — MOCK DATA
        </div>
      )}
    </div>
  );
}
