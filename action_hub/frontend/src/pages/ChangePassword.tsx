import { useState, FormEvent } from 'react'
import { Card, Form, Button, Alert } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { t } from '../lib/i18n'

export default function ChangePassword() {
  const navigate = useNavigate()
  
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess(false)
    
    if (newPassword !== confirmPassword) {
      setError(t('auth.passwordsDoNotMatch', 'Passwords do not match'))
      return
    }
    
    if (newPassword.length < 6) {
      setError(t('auth.passwordTooShort', 'Password must be at least 6 characters'))
      return
    }

    setIsLoading(true)
    
    try {
      await api.post('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setSuccess(true)
      setTimeout(() => {
        navigate('/dashboard/personal')
      }, 2000)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const response = (err as { response?: { data?: { error?: { message?: string } } } }).response
        setError(response?.data?.error?.message || t('auth.changePasswordFailed', 'Failed to change password'))
      } else {
        setError(t('auth.changePasswordFailed', 'Failed to change password'))
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
      <Card style={{ width: '400px' }}>
        <Card.Body className="p-4">
          <div className="text-center mb-4">
            <h4 style={{ color: '#1a365d' }}>{t('auth.changePassword', 'Change Password')}</h4>
          </div>
          
          {error && <Alert variant="danger">{error}</Alert>}
          {success && <Alert variant="success">{t('auth.passwordChanged', 'Password changed successfully! Redirecting...')}</Alert>}
          
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3" controlId="currentPassword">
              <Form.Label>{t('auth.currentPassword', 'Current Password')}</Form.Label>
              <Form.Control
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoFocus
              />
            </Form.Group>
            
            <Form.Group className="mb-3" controlId="newPassword">
              <Form.Label>{t('auth.newPassword', 'New Password')}</Form.Label>
              <Form.Control
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={6}
              />
              <Form.Text className="text-muted">
                {t('auth.passwordRequirements', 'Minimum 6 characters')}
              </Form.Text>
            </Form.Group>
            
            <Form.Group className="mb-3" controlId="confirmPassword">
              <Form.Label>{t('auth.confirmPassword', 'Confirm New Password')}</Form.Label>
              <Form.Control
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </Form.Group>
            
            <div className="d-grid gap-2">
              <Button
                variant="primary"
                type="submit"
                disabled={isLoading}
                style={{ backgroundColor: '#1a365d' }}
              >
                {isLoading ? t('common.saving', 'Saving...') : t('auth.changePassword', 'Change Password')}
              </Button>
              <Button
                variant="outline-secondary"
                type="button"
                onClick={() => navigate('/dashboard/personal')}
              >
                {t('common.cancel', 'Cancel')}
              </Button>
            </div>
          </Form>
        </Card.Body>
      </Card>
    </div>
  )
}