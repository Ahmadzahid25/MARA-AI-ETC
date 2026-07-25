import { Route, Routes } from 'react-router';
import { AuthGuard } from './components/AuthGuard';
import { LoginPage } from './pages/LoginPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { ReviewConsolePage } from './pages/ReviewConsolePage';

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <AuthGuard>
            <WorkspacePage />
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
    </Routes>
  );
}
