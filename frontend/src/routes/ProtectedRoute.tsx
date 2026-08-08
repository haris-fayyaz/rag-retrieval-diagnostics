import { Navigate, Outlet } from 'react-router-dom'

interface ProtectedRouteProps {
  username: string | null
}

/**
 * Gate for every authenticated route. An unsigned-in visitor is sent
 * to /login instead of seeing a broken/empty page - the same guard
 * App.tsx used to apply by returning <LoginPage/> early.
 */
export default function ProtectedRoute({ username }: ProtectedRouteProps) {
  if (!username) return <Navigate to="/login" replace />
  return <Outlet />
}