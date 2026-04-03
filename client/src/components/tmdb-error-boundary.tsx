import React from 'react';
import { Film, RefreshCw, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface TMDBErrorState {
  hasError: boolean;
  error?: Error;
}

interface TMDBErrorBoundaryProps {
  children: React.ReactNode;
  /** Optional section name shown in fallback (e.g. "Trending Movies") */
  section?: string;
}

/**
 * A specialised error boundary for TMDB-driven sections.
 * Shows a friendly, minimal card instead of crashing the whole page
 * when TMDB is unreachable or returns unexpected data.
 */
export class TMDBErrorBoundary extends React.Component<TMDBErrorBoundaryProps, TMDBErrorState> {
  constructor(props: TMDBErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): TMDBErrorState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[TMDBErrorBoundary] TMDB section crashed:', error, info);
  }

  reset = () => this.setState({ hasError: false, error: undefined });

  render() {
    if (!this.state.hasError) return this.props.children;

    const { section = 'Content' } = this.props;

    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 bg-card/40 p-10 text-center gap-4 my-4">
        <div className="relative">
          <Film className="h-12 w-12 text-muted-foreground/40" />
          <WifiOff className="h-5 w-5 text-destructive absolute -bottom-1 -right-1" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">{section} unavailable</p>
          <p className="text-xs text-muted-foreground mt-1">
            Could not load data from TMDB. Check your connection or try again.
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={this.reset} className="gap-2">
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </Button>
      </div>
    );
  }
}

/**
 * A lightweight functional wrapper for concise usage.
 *
 * @example
 * <WithTMDBFallback section="Trending">
 *   <TrendingSection />
 * </WithTMDBFallback>
 */
export function WithTMDBFallback({
  children,
  section,
}: {
  children: React.ReactNode;
  section?: string;
}) {
  return (
    <TMDBErrorBoundary section={section}>
      {children}
    </TMDBErrorBoundary>
  );
}
