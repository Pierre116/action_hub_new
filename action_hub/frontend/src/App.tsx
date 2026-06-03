import { Routes, Route, Navigate } from 'react-router-dom'
import AppRoutes from './router'
import { useAuth } from './contexts/AuthContext'

function App() {
  return <AppRoutes />
}

export default App
