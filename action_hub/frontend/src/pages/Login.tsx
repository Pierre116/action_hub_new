import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Form, Button, Alert } from 'react-bootstrap'
import { useAuth } from '../contexts/AuthContext'
import { t } from '../lib/i18n'

export default function Login() {
  const { login, isLoading } = useAuth()
  const navigate = useNavigate()
  
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    
    try {
      await login(username, password)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const response = (err as { response?: { data?: { error?: { message?: string } } } }).response
        setError(response?.data?.error?.message || t('auth.loginFailed', 'Login failed'))
      } else {
        setError(t('auth.loginFailed', 'Login failed'))
      }
    }
  }

  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh', backgroundColor: 'var(--brand-light)' }}>
      <Card style={{ width: '400px' }}>
        <Card.Body className="p-4">
          <div className="text-center mb-4">
            <h2 style={{ color: 'var(--brand-blue)' }}>ActionHub</h2>
            <p className="text-muted">{t('auth.signIn', 'Sign in to continue')}</p>
          </div>
          
          {error && <Alert variant="danger">{error}</Alert>}
          
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3" controlId="username">
              <Form.Label>{t('auth.username', 'Username')}</Form.Label>
              <Form.Control
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
                placeholder={t('auth.usernamePlaceholder', 'Enter username')}
              />
            </Form.Group>
            
            <Form.Group className="mb-3" controlId="password">
              <Form.Label>{t('auth.password', 'Password')}</Form.Label>
              <Form.Control
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder={t('auth.passwordPlaceholder', 'Enter password')}
              />
            </Form.Group>
            
            <Button
              variant="primary"
              type="submit"
              className="w-100"
              disabled={isLoading}
            >
              {isLoading ? t('auth.loggingIn', 'Signing in...') : t('auth.signIn', 'Sign in')}
            </Button>
          </Form>
        </Card.Body>
      </Card>
    </div>
  )
}