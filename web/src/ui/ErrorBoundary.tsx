import { Component, type ReactNode, type ErrorInfo } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[Apex ErrorBoundary]", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div
          role="alert"
          className="flex flex-col items-center justify-center h-64 rounded-card border border-critical/30 bg-panel animate-rise"
        >
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="mb-3 text-critical" aria-hidden="true">
            <path d="M12 9v4m0 4h.01M5.07 19h13.86a2 2 0 001.73-3L13.73 4a2 2 0 00-3.46 0L3.34 16a2 2 0 001.73 3z"
              stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div className="font-mono text-[10px] tracking-[.12em] text-fg3 mb-1">RENDER ERROR</div>
          <div className="text-[14px] text-fg2 mb-1 max-w-md text-center px-4">
            {this.state.error?.message || "Something went wrong"}
          </div>
          <button
            onClick={this.handleReset}
            className="mt-3 px-4 py-1.5 rounded-pill font-mono text-[10px] tracking-[.06em] font-semibold
              bg-cyan text-cyan-ink hover:brightness-110 transition-all
              focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none"
          >
            RETRY
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
