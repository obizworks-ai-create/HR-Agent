import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Layout from './components/Layout';
import JobDescriptionPage from './pages/JobDescriptionPage';
import CandidateDashboard from './pages/CandidateDashboard';
import HRQuestionsPage from './pages/HRQuestionsPage';
import InterviewScheduler from './pages/InterviewScheduler';
import AnalysisPage from './pages/AnalysisPage';
import StatsDashboard from './pages/StatsDashboard';
import InterviewPage from './pages/InterviewPage';
import Login from './pages/Login';

// Auth Guard
const ProtectedRoute = () => {
  const token = localStorage.getItem('admin_password');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Login Route */}
        <Route path="/login" element={<Login />} />

        {/* Protected HR Routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Layout />}>
            <Route index element={<JobDescriptionPage />} />
            <Route path="analysis" element={<AnalysisPage />} />
            <Route path="candidates" element={<CandidateDashboard />} />
            <Route path="dashboard" element={<StatsDashboard />} />
            <Route path="questions" element={<HRQuestionsPage />} />
            <Route path="interviews" element={<InterviewScheduler />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Route>

        {/* Helper Route for standalone Interview Page (No Sidebar, MUST BE PUBLIC) */}
        <Route path="/interview" element={<InterviewPage />} />
      </Routes>
    </BrowserRouter>
  );
}


export default App;
