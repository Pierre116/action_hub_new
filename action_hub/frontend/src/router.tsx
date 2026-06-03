import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { Spinner } from 'react-bootstrap'
import AppLayout from './components/AppLayout'

// Lazy load all pages
const Login = lazy(() => import('./pages/Login'))
const ChangePassword = lazy(() => import('./pages/ChangePassword'))
const DashboardPersonal = lazy(() => import('./pages/dashboard/Personal'))
const DashboardGlobal = lazy(() => import('./pages/dashboard/GlobalDashboard'))
const DashboardCategory = lazy(() => import('./pages/dashboard/BusinessTheme'))
const TeamDashboard = lazy(() => import('./pages/dashboard/TeamDashboard'))
const ActionsList = lazy(() => import('./pages/actions/ActionsList'))
const ActionsDetail = lazy(() => import('./pages/actions/ActionDetail'))
const MeetingsList = lazy(() => import('./pages/meetings/SeriesList'))
const MeetingsDetail = lazy(() => import('./pages/meetings/OccurrenceWorkspace'))
const MeetingSeriesDetail = lazy(() => import('./pages/meetings/SeriesDetail'))
const Feedback = lazy(() => import('./pages/Feedback'))
const Gantt = lazy(() => import('./pages/Gantt'))
const NotificationsPage = lazy(() => import('./pages/Notifications'))
const AdminTeams = lazy(() => import('./pages/admin/Teams'))
const AdminUsers = lazy(() => import('./pages/admin/Users'))
// const AdminActionTypes = lazy(() => import('./pages/admin/ActionTypes'))
const AdminCategories = lazy(() => import('./pages/admin/BusinessThemes'))
const WorkflowDashboard = lazy(() => import('./pages/workflow/Dashboard'))
const WorkflowBuilder = lazy(() => import('./pages/workflow/WorkflowBuilder'))
const WorkflowWorkbench = lazy(() => import('./pages/workflow/Workbench'))
const Instructions = lazy(() => import('./pages/Instructions'))

const DecisionsList = lazy(() => import('./pages/decisions/DecisionsList'))
const DecisionDetail = lazy(() => import('./pages/decisions/DecisionDetail'))

function Loading() {
  return (
    <div className="d-flex justify-content-center align-items-center" style={{ height: '100vh' }}>
      <Spinner animation="border" role="status">
        <span className="visually-hidden">Loading...</span>
      </Spinner>
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <Suspense fallback={<Loading />}>{children}</Suspense>
}

function AuthenticatedLayout() {
  return <AppLayout />
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      
      <Route element={<AuthenticatedLayout />}>
        <Route path="/change-password" element={
          <ProtectedRoute>
            <ChangePassword />
          </ProtectedRoute>
        } />
        
        <Route path="/" element={
          <ProtectedRoute>
            <Navigate to="/dashboard/personal" replace />
          </ProtectedRoute>
        } />
        
        <Route path="/dashboard/personal" element={
          <ProtectedRoute>
            <DashboardPersonal />
          </ProtectedRoute>
        } />
        
        <Route path="/dashboard/global" element={
          <ProtectedRoute>
            <DashboardGlobal />
          </ProtectedRoute>
        } />

        <Route path="/dashboard/business-theme" element={
          <ProtectedRoute>
            <DashboardCategory />
          </ProtectedRoute>
        } />

        <Route path="/dashboard/team" element={
          <ProtectedRoute>
            <TeamDashboard />
          </ProtectedRoute>
        } />
        
        <Route path="/actions" element={
          <ProtectedRoute>
            <ActionsList />
          </ProtectedRoute>
        } />
        
        <Route path="/actions/new" element={
          <ProtectedRoute>
            <ActionsDetail />
          </ProtectedRoute>
        } />
        
        <Route path="/actions/:id" element={
          <ProtectedRoute>
            <ActionsDetail />
          </ProtectedRoute>
        } />
        
        <Route path="/meetings" element={
          <ProtectedRoute>
            <Navigate to="/meetings/series" replace />
          </ProtectedRoute>
        } />

        <Route path="/meetings/series" element={
          <ProtectedRoute>
            <MeetingsList />
          </ProtectedRoute>
        } />

        <Route path="/meetings/series/:id" element={
          <ProtectedRoute>
            <MeetingSeriesDetail />
          </ProtectedRoute>
        } />
        
        <Route path="/meetings/:id" element={
          <ProtectedRoute>
            <MeetingsDetail />
          </ProtectedRoute>
        } />
        
        <Route path="/feedback" element={
          <ProtectedRoute>
            <Feedback />
          </ProtectedRoute>
        } />

        <Route path="/notifications" element={
          <ProtectedRoute>
            <NotificationsPage />
          </ProtectedRoute>
        } />

        <Route path="/gantt" element={
          <ProtectedRoute>
            <Gantt />
          </ProtectedRoute>
        } />
        
        
        <Route path="/admin/teams" element={
          <ProtectedRoute>
            <AdminTeams />
          </ProtectedRoute>
        } />
        
        <Route path="/admin/users" element={
          <ProtectedRoute>
            <AdminUsers />
          </ProtectedRoute>
        } />
        
        {/* Legacy category-type route hidden as requested */}
        
        <Route path="/admin/categories" element={
          <ProtectedRoute>
            <AdminCategories />
          </ProtectedRoute>
        } />

        <Route path="/admin/business-themes" element={
          <ProtectedRoute>
            <AdminCategories />
          </ProtectedRoute>
        } />
        
        <Route path="/workflow" element={
          <ProtectedRoute>
            <WorkflowDashboard />
          </ProtectedRoute>
        } />



        <Route path="/workflow/builder" element={
          <ProtectedRoute>
            <WorkflowBuilder />
          </ProtectedRoute>
        } />

        <Route path="/workflow/workbench/:instanceId" element={
          <ProtectedRoute>
            <WorkflowWorkbench />
          </ProtectedRoute>
        } />
        
        <Route path="/decisions" element={
          <ProtectedRoute>
            <DecisionsList />
          </ProtectedRoute>
        } />

        <Route path="/decisions/:id" element={
          <ProtectedRoute>
            <DecisionDetail />
          </ProtectedRoute>
        } />

        <Route path="/instructions" element={
          <ProtectedRoute>
            <Instructions />
          </ProtectedRoute>
        } />
      </Route>
    </Routes>
  )
}
