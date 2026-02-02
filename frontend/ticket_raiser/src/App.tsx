import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { AuthProvider } from './contexts/AuthContext';

// Auth pages
import { LoginPage } from './features/Auth/LoginPage/LoginPage';
import { SignupPage } from './features/Auth/SignupPage/SignupPage';

// import { Profile } from './features/Profile/Profile';
import { ProfilePage } from './features/Profile/Profile';
// Dashboard and Submission pages
import { Dashboard } from './features/Dashboard/Dashboard';
import { SubmissionDetailPage } from './features/SubmissionDetail/SubmissionDetail';

// Problem Management pages
// import { CreateProblem } from './features/CreateProblem/CreateProblem';
// import { EditProblem } from './features/EditProblem/EditProblem';
// import { ManageTestCases } from './features/ManageTestCases/ManageTestCases';
// import { UploadEditorial } from './features/UploadEditorial/UploadEditorial';
// import { ProblemDetail } from './features/ProblemDetail/ProblemDetail';

import { CreateProblemPage } from './features/CreateProblem/CreateProblem';
import { EditProblemPage } from './features/EditProblem/EditProblem';
import { ManageTestCasesPage } from './features/ManageTestCases/ManageTestCases';
import { UploadEditorialPage } from './features/UploadEditorial/UploadEditorial';
import { ProblemDetailPage } from './features/ProblemDetail/ProblemDetail';
import { ProblemList } from './features/ProblemList/ProblemList';
import RoadmapGeneration from './features/RoadmapGeneration/RoadmapGeneration';
import { IndividualRoadmap } from './features/IndividualRoadmap/IndividualRoadmap';
import { MyRoadmaps } from './features/MyRoadmaps/MyRoadmaps';
import { ProtectedRoute } from './components/ProtectedRoute';
import './App.css';

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        {/* Auth Routes */}
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
        />
        <Route
          path="/signup"
          element={isAuthenticated ? <Navigate to="/" replace /> : <SignupPage />}
        />

        <Route
          path="/profile"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <ProfilePage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        {/* Protected Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <Dashboard />
            </ProtectedRoute>
          }
        />



        <Route
          path="/submissions/:submissionId"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <SubmissionDetailPage />
            </ProtectedRoute>
          }
        />

        {/* Problem Management Routes */}
        <Route
          path="/admin/problems/create"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <CreateProblemPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/problems/:id/edit"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <EditProblemPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/problems/:id/test-cases"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <ManageTestCasesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/problems/:id/editorial"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <UploadEditorialPage />
            </ProtectedRoute>
          }
        />

        {/* Problem Detail Route */}
        <Route
          path="/problems/:id"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <ProblemDetailPage />
            </ProtectedRoute>
          }
        />

        {/* Problems List Route */}
        <Route
          path="/problems"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <ProblemList />
            </ProtectedRoute>
          }
        />

        {/* Roadmap Routes */}
        <Route
          path="/roadmap"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <RoadmapGeneration />
            </ProtectedRoute>
          }
        />
        <Route
          path="/generate-roadmap"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <RoadmapGeneration />
            </ProtectedRoute>
          }
        />
        <Route
          path="/my-roadmaps"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <MyRoadmaps />
            </ProtectedRoute>
          }
        />
        <Route
          path="/roadmaps/:roadmapId"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <IndividualRoadmap />
            </ProtectedRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
