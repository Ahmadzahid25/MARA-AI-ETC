import { Route, Routes } from 'react-router';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AuthGuard } from './components/AuthGuard';
import { AssessmentProvider } from './context/AssessmentContext';
import { CallbackPage } from './pages/CallbackPage';
import { LoginPage } from './pages/LoginPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { DashboardPage } from './pages/DashboardPage';
import { ReviewConsolePage } from './pages/ReviewConsolePage';
import { AdminConsolePage } from './pages/AdminConsolePage';
import { AuditorConsolePage } from './pages/AuditorConsolePage';

export function App() {
  return (
    <AssessmentProvider>
        <ErrorBoundary>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/callback" element={<CallbackPage />} />
            <Route path="/" element={<AuthGuard><WorkspacePage /></AuthGuard>} />
            <Route path="/dashboard" element={<AuthGuard><DashboardPage /></AuthGuard>} />
            <Route path="/review" element={<AuthGuard><ReviewConsolePage /></AuthGuard>} />
            <Route path="/admin" element={<AuthGuard><AdminConsolePage /></AuthGuard>} />
            <Route path="/auditor" element={<AuthGuard><AuditorConsolePage /></AuthGuard>} />
          </Routes>
        </ErrorBoundary>
      </AssessmentProvider>
  );
}
