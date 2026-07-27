import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Typography } from '@openhands/ui';

interface Props {
  children: ReactNode;
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
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen items-center justify-center bg-white p-8 dark:bg-[#131417]">
          <div className="max-w-md text-center">
            <Typography.H3 className="mb-2 text-slate-900 dark:text-white">
              Something went wrong
            </Typography.H3>
            <Typography.Text fontSize="s" className="mb-4 block text-slate-500 dark:text-slate-400">
              {this.state.error?.message ?? 'An unexpected error occurred.'}
            </Typography.Text>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="cursor-pointer rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
