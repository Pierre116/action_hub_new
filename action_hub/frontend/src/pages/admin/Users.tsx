import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button, Modal, Form, Alert, Badge, Row, Col } from 'react-bootstrap'
import { ColumnDef } from '@tanstack/react-table'
import api from '../../lib/api'
import CrudTable from '../../components/shared/CrudTable'
import { t } from '../../lib/i18n'

interface User {
  usr_id: number
  usr_username: string // Employee ID
  usr_display_name: string
  usr_email: string
  usr_role: string
  teams?: Team[]
  usr_active: number
}

interface Team {
  tea_id: number
  tea_name_en: string
  tea_code: string
}

interface FormData {
  username: string // Employee ID
  display_name: string
  email: string
  role: string
  password?: string // Marked as optional
}

export default function Users() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [showResetModal, setShowResetModal] = useState(false)
  const [showTeamsModal, setShowTeamsModal] = useState(false)
  const [teamsUser, setTeamsUser] = useState<User | null>(null)
  const [selectedTeamId, setSelectedTeamId] = useState('')
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [resetUser, setResetUser] = useState<User | null>(null)
  const [error, setError] = useState('')

  const [formData, setFormData] = useState<FormData>({
    username: '',
    display_name: '',
    email: '',
    role: 'Member',
    password: '',
  })

  const [resetPassword, setResetPassword] = useState('')

  // Fetch all teams (for dropdown)
  const { data: allTeams = [] } = useQuery<Team[]>({
    queryKey: ['admin', 'teams'],
    queryFn: async () => {
      const response = await api.get('/api/admin/teams')
      return response.data.data as Team[]
    },
  })

  // Fetch teams for the selected user
  const { data: userTeams = [], refetch: refetchUserTeams } = useQuery<Team[]>({
    queryKey: ['admin', 'user-teams', teamsUser?.usr_id],
    queryFn: async () => {
      const response = await api.get(`/api/admin/users/${teamsUser!.usr_id}/teams`)
      return response.data.data as Team[]
    },
    enabled: !!teamsUser,
  })

  // Add team mutation
  const addTeamMutation = useMutation({
    mutationFn: ({ userId, teamId }: { userId: number; teamId: number }) =>
      api.post(`/api/admin/users/${userId}/teams`, { team_id: teamId }),
    onSuccess: () => {
      refetchUserTeams()
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      setSelectedTeamId('')
    },
  })

  // Remove team mutation
  const removeTeamMutation = useMutation({
    mutationFn: ({ userId, teamId }: { userId: number; teamId: number }) =>
      api.delete(`/api/admin/users/${userId}/teams/${teamId}`),
    onSuccess: () => {
      refetchUserTeams()
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })

  const handleManageTeams = (user: User) => {
    setTeamsUser(user)
    setSelectedTeamId('')
    setShowTeamsModal(true)
  }

  // Fetch users
  const { data: users = [], isLoading } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: async () => {
      const response = await api.get('/api/admin/users')
      return response.data.data as User[]
    },
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/admin/users', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      setShowModal(false)
      resetForm()
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<typeof formData> }) => 
      api.patch(`/api/admin/users/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      setShowModal(false)
      setEditingUser(null)
      resetForm()
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  // Reset password mutation
  const resetPasswordMutation = useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) => 
      api.post(`/api/admin/users/${id}/reset-password`, { password }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
      setShowResetModal(false)
      setResetUser(null)
      setResetPassword('')
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  const resetForm = () => {
    setFormData({
      username: '',
      display_name: '',
      email: '',
      role: 'Member',
      password: '',
    })
    setError('')
  }

  const handleAdd = () => {
    resetForm()
    setEditingUser(null)
    setShowModal(true)
  }

  const handleEdit = (user: User) => {
    setEditingUser(user)
    setFormData({
      username: user.usr_username,
      display_name: user.usr_display_name,
      email: user.usr_email,
      role: user.usr_role,
      password: '',
    })
    setError('')
    setShowModal(true)
  }

  const handleResetPassword = (user: User) => {
    setResetUser(user)
    setResetPassword('')
    setError('')
    setShowResetModal(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    const payload = { ...formData }
    if (!payload.password && !editingUser) {
      setError(t('user.passwordRequired', 'Password is required for new users'))
      return
    }
    if (editingUser && !payload.password) {
      // Ensure the property exists before attempting to delete it
      if ('password' in payload) {
        delete payload.password;
      }
    }

    if (editingUser) {
      updateMutation.mutate({ id: editingUser.usr_id, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const handleResetSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!resetUser || !resetPassword) return
    if (resetPassword.length < 8) {
      setError(t('auth.passwordTooShort', 'Password must be at least 8 characters'))
      return
    }
    resetPasswordMutation.mutate({ id: resetUser.usr_id, password: resetPassword })
  }

  const columns: ColumnDef<User>[] = [
    {
      accessorKey: 'usr_username',
      header: t('user.employeeId', 'Employee ID'),
    },
    {
      accessorKey: 'usr_display_name',
      header: t('user.displayName', 'Display Name'),
    },
    {
      accessorKey: 'usr_email',
      header: t('user.email', 'Email'),
    },
    {
      accessorKey: 'usr_role',
      header: t('user.role', 'Role'),
      cell: ({ row }) => {
        const role = row.original.usr_role
        const badgeVariant = role === 'Admin' ? 'danger' : role === 'TeamLead' ? 'warning' : 'primary'
        return <Badge bg={badgeVariant}>{role}</Badge>
      },
    },
    {
      id: 'teams',
      header: t('user.team', 'Team'),
      cell: ({ row }) => (
        <span>
          {(row.original.teams ?? []).map((team) => (
            <Badge key={team.tea_id} bg="info" className="me-1">
              {team.tea_name_en}
            </Badge>
          ))}
        </span>
      ),
    },
    {
      accessorKey: 'usr_active',
      header: t('user.status', 'Status'),
      cell: ({ row }) => (
        <Badge bg={row.original.usr_active ? 'success' : 'secondary'}>
          {row.original.usr_active ? t('user.active', 'Active') : t('user.inactive', 'Inactive')}
        </Badge>
      ),
    },
    {
      id: 'actions',
      header: t('common.actions', 'Actions'),
      cell: ({ row }) => {
        const user = row.original
        const [deleting, setDeleting] = useState(false)
        const [deleteError, setDeleteError] = useState('')
        // referenced: user._referenced (backend should provide this flag, fallback to false)
        const referenced = user._referenced || false
        const handleDelete = async () => {
          setDeleteError('')
          setDeleting(true)
          try {
            await api.delete(`/api/admin/users/${user.usr_id}`)
            queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
          } catch (err: any) {
            setDeleteError(err?.response?.data?.error?.message || t('common.error', 'Error'))
          } finally {
            setDeleting(false)
          }
        }
        return (
          <div className="d-flex gap-1 align-items-center">
            <Button variant="outline-primary" size="sm" onClick={() => handleEdit(user)}>
              {t('common.edit', 'Edit')}
            </Button>
            <Button variant="outline-info" size="sm" onClick={() => handleManageTeams(user)}>
              {t('user.teams', 'Teams')}
            </Button>
            <Button 
              variant={user.usr_active ? 'outline-warning' : 'outline-success'} 
              size="sm"
              onClick={() => handleToggleActive(user)}
            >
              {user.usr_active ? t('admin.users.deactivate', 'Deactivate') : t('admin.users.activate', 'Activate')}
            </Button>
            <Button
              variant="outline-danger"
              size="sm"
              disabled={referenced || deleting}
              onClick={handleDelete}
              title={referenced ? t('user.cannotDeleteReferenced', 'User is referenced and cannot be deleted') : t('common.delete', 'Delete')}
              style={referenced ? { opacity: 0.5, pointerEvents: 'none' } : {}}
            >
              {deleting ? t('common.saving', 'Saving...') : t('common.delete', 'Delete')}
            </Button>
            {deleteError && <span className="text-danger small ms-2">{deleteError}</span>}
          </div>
        )
      },
    },
  ]

  // Toggle active status mutation
  const toggleActiveMutation = useMutation({
    mutationFn: async (user: User) => {
      console.log('Toggling user:', user.usr_id, 'to active:', user.usr_active ? 0 : 1)
      try {
        const response = await api.patch(`/api/admin/users/${user.usr_id}`, { usr_active: user.usr_active ? 0 : 1 })
        console.log('Response:', response.data)
        return response.data
      } catch (err) {
        console.error('API Error:', err)
        throw err
      }
    },
    onSuccess: () => {
      console.log('Toggle success - invalidating queries')
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
    onError: (err: unknown) => {
      console.error('Toggle error:', err)
      const axiosErr = err as { response?: { data?: { error?: { message?: string } } }, message?: string }
      const errorMsg = axiosErr?.response?.data?.error?.message || axiosErr?.message || t('common.error', 'Error')
      setError(errorMsg)
    },
  })

  // Success toast state
  const [successMsg, setSuccessMsg] = useState('')
  
  // Show success message and auto-hide
  const showSuccess = (msg: string) => {
    setSuccessMsg(msg)
    setTimeout(() => setSuccessMsg(''), 3000)
  }

  // Update toggle mutation to show success
  const handleToggleActive = (user: User) => {
    console.log('handleToggleActive called for user:', user.usr_id)
    toggleActiveMutation.mutate(user, {
      onSuccess: () => {
        console.log('Mutation success')
        showSuccess(user.usr_active 
          ? t('admin.users.deactivated', 'User deactivated successfully')
          : t('admin.users.activated', 'User activated successfully'))
      },
      onError: (err) => {
        console.log('Mutation error:', err)
      }
    })
  }

  return (
    <div>
      {successMsg && <Alert variant="success">{successMsg}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}
      
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>{t('nav.users', 'Users')}</h2>
      </div>

      <CrudTable
        data={users}
        columns={columns}
        isLoading={isLoading}
        onAdd={handleAdd}
        searchPlaceholder={t('common.search', 'Search...')}
        addButtonLabel={t('user.addUser', 'Add User')}
      />

      {/* Add/Edit Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            {editingUser ? t('user.editUser', 'Edit User') : t('user.addUser', 'Add User')}
          </Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            {error && <Alert variant="danger">{error}</Alert>}
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>{t('user.employeeId', 'Employee ID')} *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    required
                    disabled={!!editingUser}
                    minLength={3}
                    maxLength={100}
                  />
                  <Form.Text className="text-muted">
                    {t('user.employeeIdUnique', 'Must be unique for each user.')}
                  </Form.Text>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>{t('user.displayName', 'Display Name')} *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.display_name}
                    onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                    required
                  />
                </Form.Group>
              </Col>
            </Row>

            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>{t('user.email', 'Email')} *</Form.Label>
                  <Form.Control
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>{t('user.role', 'Role')} *</Form.Label>
                  <Form.Select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  >
                    <option value="Member">Member</option>
                    <option value="TeamLead">TeamLead</option>
                    <option value="Admin">Admin</option>
                  </Form.Select>
                </Form.Group>
              </Col>
            </Row>

            {!editingUser && (
              <Form.Group className="mb-3">
                <Form.Label>{t('user.password', 'Password')} *</Form.Label>
                <Form.Control
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required={!editingUser}
                  minLength={8}
                />
              </Form.Group>
            )}
          </Modal.Body>
          <Modal.Footer>
            {editingUser && (
              <Button 
                variant="warning" 
                onClick={() => handleResetPassword(editingUser)}
                className="me-auto"
              >
                {t('user.resetPassword', 'Reset Password')}
              </Button>
            )}
            <Button variant="secondary" onClick={() => setShowModal(false)}>
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button 
              variant="primary" 
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {createMutation.isPending || updateMutation.isPending 
                ? t('common.saving', 'Saving...') 
                : t('common.save', 'Save')}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* Manage Teams Modal */}
      <Modal show={showTeamsModal} onHide={() => setShowTeamsModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>{t('user.manageTeams', 'Manage Teams')} — {teamsUser?.usr_display_name}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {/* Current teams */}
          {userTeams.length === 0 ? (
            <p className="text-muted">{t('user.noTeams', 'No teams assigned.')}</p>
          ) : (
            <div className="mb-3">
              {userTeams.map((team) => (
                <Badge key={team.tea_id} bg="primary" className="me-2 mb-2 p-2" style={{ fontSize: '0.85em' }}>
                  {team.tea_name_en}
                  <Button
                    variant="link"
                    size="sm"
                    className="text-white ms-1 p-0"
                    style={{ lineHeight: 1 }}
                    onClick={() => teamsUser && removeTeamMutation.mutate({ userId: teamsUser.usr_id, teamId: team.tea_id })}
                  >
                    ×
                  </Button>
                </Badge>
              ))}
            </div>
          )}
          {/* Add team */}
          <Row className="g-2 align-items-center">
            <Col>
              <Form.Select
                value={selectedTeamId}
                onChange={(e) => setSelectedTeamId(e.target.value)}
              >
                <option value="">{t('user.selectTeam', 'Select a team...')}</option>
                {allTeams
                  .filter((t) => !userTeams.some((ut) => ut.tea_id === t.tea_id))
                  .map((team) => (
                    <option key={team.tea_id} value={team.tea_id}>
                      {team.tea_name_en} ({team.tea_code})
                    </option>
                  ))}
              </Form.Select>
            </Col>
            <Col xs="auto">
              <Button
                variant="primary"
                disabled={!selectedTeamId || addTeamMutation.isPending}
                onClick={() => teamsUser && selectedTeamId && addTeamMutation.mutate({ userId: teamsUser.usr_id, teamId: parseInt(selectedTeamId) })}
              >
                {t('common.add', 'Add')}
              </Button>
            </Col>
          </Row>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowTeamsModal(false)}>
            {t('common.close', 'Close')}
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Reset Password Modal */}
      <Modal show={showResetModal} onHide={() => setShowResetModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>{t('user.resetPassword', 'Reset Password')}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleResetSubmit}>
          <Modal.Body>
            {error && <Alert variant="danger">{error}</Alert>}
            <p>
              {t('user.resetFor', 'Reset password for')} <strong>{resetUser?.usr_display_name}</strong>
            </p>
            <Form.Group className="mb-3">
              <Form.Label>{t('user.newPassword', 'New Password')} *</Form.Label>
              <Form.Control
                type="password"
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
                required
                minLength={8}
              />
              <Form.Text className="text-muted">
                {t('auth.passwordRequirements', 'Minimum 8 characters')}
              </Form.Text>
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowResetModal(false)}>
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button 
              variant="primary" 
              type="submit"
              disabled={resetPasswordMutation.isPending}
            >
              {resetPasswordMutation.isPending 
                ? t('common.saving', 'Saving...') 
                : t('common.save', 'Save')}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  )
}
