import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LandingView from './views/LandingView';
import AppShell from './components/AppShell';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingView />} />
        <Route path="/c/:conversationId" element={<AppShell />} />
      </Routes>
    </BrowserRouter>
  );
}
