import { Route, Routes } from 'react-router';
import { AuthGuard } from './components/AuthGuard';
import { AssessmentProvider } from './context/AssessmentContext';
import { CallbackPage } from './pages/CallbackPage';
import { LoginPage } from './pages/LoginPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { DashboardPage } from './pages/DashboardPage';
import { ReviewConsolePage } from './pages/ReviewConsolePage';
import { AdminConsolePage } from './pages/AdminConsolePage';

export function App() {
  return (
    <AssessmentProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        {/* OIDC redirect-callback — must be public (no AuthGuard) */}
        <Route path="/callback" element={<CallbackPage />} />
        <Route
          path="/"
          element={
            <AuthGuard>
              <WorkspacePage />
            </AuthGuard>
          }
        />
        <Route
          path="/dashboard"
          element={
            <AuthGuard>
              <DashboardPage />
            </AuthGuard>
          }
        />
        <Route
          path="/review"
          element={
            <AuthGuard>
              <ReviewConsolePage />
            </AuthGuard>
          }
        />
        <Route
          path="/admin"
          element={
            <AuthGuard>
              <AdminConsolePage />
            </AuthGuard>
          }
        />
      </Routes>
    </AssessmentProvider>
  );
}
