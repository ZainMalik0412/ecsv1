import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Toaster } from '@/components/ui/toaster'
import LoginPage from '@/pages/LoginPage'
import SignupPage from '@/pages/SignupPage'
import DashboardLayout from '@/components/layout/DashboardLayout'
import DashboardPage from '@/pages/DashboardPage'
import ModulesPage from '@/pages/ModulesPage'
import SessionsPage from '@/pages/SessionsPage'
import AttendancePage from '@/pages/AttendancePage'
import UsersPage from '@/pages/UsersPage'
import FaceRegistrationPage from '@/pages/FaceRegistrationPage'
import MarkAttendancePage from '@/pages/MarkAttendancePage'
import LiveSessionPage from '@/pages/LiveSessionPage'
import CalendarPage from '@/pages/CalendarPage'
import StudentStatsPage from '@/pages/StudentStatsPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <DashboardLayout />
            </PrivateRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="modules" element={<ModulesPage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="attendance" element={<AttendancePage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="face-registration" element={<FaceRegistrationPage />} />
          <Route path="mark-attendance" element={<MarkAttendancePage />} />
          <Route path="live-session/:sessionId" element={<LiveSessionPage />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="my-stats" element={<StudentStatsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster />
    </>
  )
}

export default App
