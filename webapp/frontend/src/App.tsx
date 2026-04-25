import { Component } from 'react';
import type { ReactNode } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LandingView from './views/LandingView';
import AppShell from './components/AppShell';

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 32, color: '#f87171', background: '#0B0B0C', minHeight: '100vh', fontFamily: 'monospace' }}>
          <h2 style={{ color: '#2DD4BF', marginBottom: 12 }}>Render error — check console</h2>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{this.state.error.message}</pre>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, color: '#6b7280', marginTop: 8 }}>{this.state.error.stack}</pre>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ marginTop: 16, padding: '8px 16px', background: '#2DD4BF', color: '#000', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingView />} />
          <Route path="/c/:conversationId" element={<AppShell />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
