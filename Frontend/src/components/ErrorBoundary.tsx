import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertIcon, RefreshIcon } from "./icons";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary — Catches render-time JavaScript and WebGL exceptions
 * and renders a recoverable mission-control fallback panel instead of crashing.
 */
export default class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("Moonscape Uncaught UI Error:", error, errorInfo);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
    window.location.hash = "#/";
  };

  public render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center p-6 text-center">
          <div className="panel max-w-lg p-8">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-bad/15 text-bad">
              <AlertIcon className="h-7 w-7" />
            </div>
            <span className="kicker mb-2 block !text-bad">System Telemetry Alert</span>
            <h2 className="font-display text-xl font-bold text-ink">
              Component Render Exception
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              An unexpected interface anomaly occurred while executing visual components.
              {this.state.error?.message && (
                <span className="mt-2 block rounded border border-divider/60 bg-space/60 p-2 font-mono text-[11px] text-slate-300">
                  {this.state.error.message}
                </span>
              )}
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button
                type="button"
                className="btn-primary !px-4 !py-2 !text-xs"
                onClick={this.handleReset}
              >
                <RefreshIcon className="h-4 w-4" /> Reset Interface
              </button>
              <button
                type="button"
                className="btn-ghost !px-4 !py-2 !text-xs"
                onClick={() => window.location.reload()}
              >
                Reload Window
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
