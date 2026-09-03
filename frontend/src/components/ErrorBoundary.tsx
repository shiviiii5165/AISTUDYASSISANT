import React from 'react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * App-wide error boundary.
 *
 * Without this, a single render-time throw anywhere in the tree (e.g. calling
 * .map() on a value that unexpectedly isn't an array) unmounts the whole React
 * tree and leaves users staring at a blank white screen with no way to recover
 * short of a manual refresh — which just repeats the crash. This catches the
 * throw, keeps the shell alive, and offers a reload instead of white-screening.
 */
class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Surface the real (unminified in dev) component stack for debugging.
    console.error('[ErrorBoundary] Uncaught render error:', error, info.componentStack);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[100dvh] flex-col items-center justify-center gap-4 bg-[var(--bg-primary)] px-6 text-center">
          <h1 className="font-display text-xl font-bold text-[var(--text-primary)]">
            Something went wrong
          </h1>
          <p className="max-w-md text-sm text-[var(--text-secondary)]">
            The page hit an unexpected error. Reloading usually fixes it. If it keeps
            happening, please let us know.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="rounded-xl bg-[var(--accent-green)] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-green-hover)]"
          >
            Reload page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
