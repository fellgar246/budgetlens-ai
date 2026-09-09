"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { copy } from "@/lib/copy";

type Props = { children: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    void error;
    void info;
  }

  render() {
    if (this.state.error) {
      return (
        <div className="mx-auto w-full max-w-3xl px-4 py-8">
          <ErrorBanner
            error={this.state.error.message || copy.unexpectedError}
            onRetry={() => this.setState({ error: null })}
          />
        </div>
      );
    }
    return this.props.children;
  }
}
