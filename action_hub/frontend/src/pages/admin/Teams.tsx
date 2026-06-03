import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Row, Col, Button, Modal, Form, Alert, Badge } from 'react-bootstrap'
import { ColumnDef } from '@tanstack/react-table'
import api from '../../lib/api'
import CrudTable from '../../components/shared/CrudTable'
import ConfirmModal from '../../components/shared/ConfirmModal'
import { t } from '../../lib/i18n'

interface Team {
  tea_id: number
  tea_code: string
  tea_name_en: string
  tea_name_cn: string
  tea_leader_user_id?: number | null
  tea_leader_name?: string | null
  tea_active: number
  member_count?: number
  can_delete?: boolean
}

interface TeamMember {
  usr_id: number
  usr_display_name: string
  usr_role: string
  usr_active: number
}

export default function Teams() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [showMembersModal, setShowMembersModal] = useState(false)
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null)
  const [editingTeam, setEditingTeam] = useState<Team | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Team | null>(null)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // Form state
  const [formData, setFormData] = useState({
    tea_code: '',
    tea_name_en: '',
    tea_name_cn: '',
    leader_id: '',
  })

  // Fetch teams
  const { data: teams = [], isLoading } = useQuery({
    queryKey: ['teams'],
    queryFn: async () => {
      const response = await api.get('/api/admin/teams?counts=true')
      return response.data.data as Team[]
    },
  })

  // Fetch all users for adding as members
  const { data: allUsers = [] } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: async () => {
      const response = await api.get('/api/admin/users')
      return response.data.data as { usr_id: number; usr_display_name: string; usr_role: string }[]
    },
  })

  // Fetch team members
  const { data: teamMembers = [], refetch: refetchMembers } = useQuery<TeamMember[]>({
    queryKey: ['admin', 'team-members', selectedTeam?.tea_id],
    queryFn: async () => {
      const response = await api.get(`/api/admin/teams/${selectedTeam!.tea_id}/members`)
      return response.data.data as TeamMember[]
    },
    enabled: !!selectedTeam,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/admin/teams', {
      code: data.tea_code,
      name_en: data.tea_name_en,
      name_cn: data.tea_name_cn,
      leader_id: data.leader_id ? Number(data.leader_id) : null,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams'] })
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
    mutationFn: ({ id, data }: { id: number; data: typeof formData }) => 
      api.patch(`/api/admin/teams/${id}`, {
        name_en: data.tea_name_en,
        name_cn: data.tea_name_cn,
        leader_id: data.leader_id ? Number(data.leader_id) : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      setShowModal(false)
      setEditingTeam(null)
      resetForm()
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/api/admin/teams/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      setDeleteTarget(null)
      setSuccessMsg(t('team.deleted', 'Team deleted successfully'))
      setTimeout(() => setSuccessMsg(''), 3000)
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  // Toggle active mutation
  const toggleActiveMutation = useMutation({
    mutationFn: (team: Team) => 
      api.patch(`/api/admin/teams/${team.tea_id}`, { active: team.tea_active ? 0 : 1 }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      setSuccessMsg(t('team.toggled', 'Team status updated successfully'))
      setTimeout(() => setSuccessMsg(''), 3000)
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  // Add member mutation
  const addMemberMutation = useMutation({
    mutationFn: ({ teamId, userId }: { teamId: number; userId: number }) =>
      api.post(`/api/admin/teams/${teamId}/members`, { user_id: userId }),
    onSuccess: () => {
      refetchMembers()
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      setSuccessMsg(t('team.memberAdded', 'Member added successfully'))
      setTimeout(() => setSuccessMsg(''), 3000)
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  // Remove member mutation
  const removeMemberMutation = useMutation({
    mutationFn: ({ teamId, userId }: { teamId: number; userId: number }) =>
      api.delete(`/api/admin/teams/${teamId}/members/${userId}`),
    onSuccess: () => {
      refetchMembers()
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      setSuccessMsg(t('team.memberRemoved', 'Member removed successfully'))
      setTimeout(() => setSuccessMsg(''), 3000)
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  const resetForm = () => {
    setFormData({ tea_code: '', tea_name_en: '', tea_name_cn: '', leader_id: '' })
    setError('')
  }

  const handleAdd = () => {
    resetForm()
    setEditingTeam(null)
    setShowModal(true)
  }

  const handleEdit = (team: Team) => {
    setEditingTeam(team)
    setFormData({
      tea_code: team.tea_code,
      tea_name_en: team.tea_name_en,
      tea_name_cn: team.tea_name_cn,
      leader_id: team.tea_leader_user_id ? String(team.tea_leader_user_id) : '',
    })
    setError('')
    setShowModal(true)
  }

  const handleManageMembers = (team: Team) => {
    setSelectedTeam(team)
    setError('')
    setShowMembersModal(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (editingTeam) {
      updateMutation.mutate({ id: editingTeam.tea_id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleAddMember = (userId: number) => {
    if (selectedTeam) {
      addMemberMutation.mutate({ teamId: selectedTeam.tea_id, userId })
    }
  }

  const handleRemoveMember = (userId: number) => {
    if (selectedTeam) {
      removeMemberMutation.mutate({ teamId: selectedTeam.tea_id, userId })
    }
  }

  const columns: ColumnDef<Team>[] = [
    {
      accessorKey: 'tea_code',
      header: t('team.code', 'Code'),
    },
    {
      accessorKey: 'tea_name_en',
      header: t('team.nameEn', 'Name (EN)'),
    },
    {
      accessorKey: 'tea_name_cn',
      header: t('team.nameCn', 'Name (CN)'),
    },
    {
      accessorKey: 'tea_leader_name',
      header: t('team.leader', 'Leader'),
      cell: ({ row }) => row.original.tea_leader_name || t('common.none', 'None'),
    },
    {
      accessorKey: 'tea_active',
      header: t('common.status', 'Status'),
      cell: ({ row }) => (
        <Badge bg={row.original.tea_active ? 'success' : 'secondary'}>
          {row.original.tea_active ? t('common.active', 'Active') : t('common.inactive', 'Inactive')}
        </Badge>
      ),
    },
    {
      accessorKey: 'member_count',
      header: t('team.members', 'Members'),
    },
    {
      id: 'actions',
      header: t('common.actions', 'Actions'),
      cell: ({ row }) => {
        const team = row.original
        return (
          <div className="d-flex gap-1">
            <Button variant="outline-primary" size="sm" onClick={() => handleEdit(team)}>
              {t('common.edit', 'Edit')}
            </Button>
            <Button variant="outline-info" size="sm" onClick={() => handleManageMembers(team)}>
              {t('team.members', 'Members')}
            </Button>
            <Button 
              variant={team.tea_active ? 'outline-warning' : 'outline-success'} 
              size="sm"
              onClick={() => toggleActiveMutation.mutate(team)}
            >
              {team.tea_active ? t('team.deactivate', 'Deactivate') : t('team.activate', 'Activate')}
            </Button>
            <Button
              variant="outline-danger"
              size="sm"
              onClick={() => {
                if (team.can_delete) {
                  setDeleteTarget(team)
                  setError('')
                  return
                }
                setError(t('team.cannotDelete', 'Cannot delete: referenced'))
              }}
              title={team.can_delete ? t('team.delete', 'Delete') : t('team.cannotDelete', 'Cannot delete: referenced')}
            >
              {t('common.delete', 'Delete')}
            </Button>
          </div>
        )
      },
    },
  ]

  return (
    <div>
      {successMsg && <Alert variant="success">{successMsg}</Alert>}
      {error && <Alert variant="danger">{error}</Alert>}

      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>{t('nav.teams', 'Teams')}</h2>
      </div>

      <CrudTable
        data={teams}
        columns={columns}
        isLoading={isLoading}
        onAdd={handleAdd}
        searchPlaceholder={t('common.search', 'Search...')}
        addButtonLabel={t('team.addTeam', 'Add Team')}
      />

      {/* Add/Edit Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>
            {editingTeam ? t('team.editTeam', 'Edit Team') : t('team.addTeam', 'Add Team')}
          </Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            {error && <Alert variant="danger">{error}</Alert>}
            
            <Form.Group className="mb-3">
              <Form.Label>{t('team.code', 'Code')} *</Form.Label>
              <Form.Control
                type="text"
                value={formData.tea_code}
                onChange={(e) => setFormData({ ...formData, tea_code: e.target.value })}
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>{t('team.nameEn', 'Name (EN)')} *</Form.Label>
              <Form.Control
                type="text"
                value={formData.tea_name_en}
                onChange={(e) => setFormData({ ...formData, tea_name_en: e.target.value })}
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>{t('team.nameCn', 'Name (CN)')} *</Form.Label>
              <Form.Control
                type="text"
                value={formData.tea_name_cn}
                onChange={(e) => setFormData({ ...formData, tea_name_cn: e.target.value })}
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>{t('team.leader', 'Leader')}</Form.Label>
              <Form.Select
                value={formData.leader_id}
                onChange={(e) => setFormData({ ...formData, leader_id: e.target.value })}
              >
                <option value="">{t('common.none', 'None')}</option>
                {allUsers.map((user) => (
                  <option key={user.usr_id} value={user.usr_id}>
                    {user.usr_display_name} ({user.usr_role})
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
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

      {/* Manage Members Modal */}
      <Modal show={showMembersModal} onHide={() => setShowMembersModal(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>{t('team.manageMembers', 'Manage Members')} — {selectedTeam ? `${selectedTeam.tea_name_en} (${selectedTeam.tea_code})` : ''}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {/* Current members */}
          {teamMembers.length === 0 ? (
            <p className="text-muted">{t('team.noMembers', 'No members in this team.')}</p>
          ) : (
            <div className="mb-3">
              {teamMembers.map((member) => (
                <Badge 
                  key={member.usr_id} 
                  bg={member.usr_active ? 'primary' : 'secondary'} 
                  className="me-2 mb-2 p-2" 
                  style={{ fontSize: '0.85em' }}
                >
                  {member.usr_display_name} ({member.usr_role})
                  <Button
                    variant="link"
                    size="sm"
                    className="text-white ms-1 p-0"
                    style={{ lineHeight: 1 }}
                    onClick={() => handleRemoveMember(member.usr_id)}
                  >
                    ×
                  </Button>
                </Badge>
              ))}
            </div>
          )}
          
          {/* Add member */}
          <Row className="g-2 align-items-center">
            <Col>
              <Form.Select
                value=""
                onChange={(e) => {
                  const userId = parseInt(e.target.value)
                  if (userId) handleAddMember(userId)
                }}
              >
                <option value="">{t('team.selectUser', 'Select a user to add...')}</option>
                {allUsers
                  .filter((u) => !teamMembers.some((m) => m.usr_id === u.usr_id))
                  .map((user) => (
                    <option key={user.usr_id} value={user.usr_id}>
                      {user.usr_display_name} ({user.usr_role})
                    </option>
                  ))}
              </Form.Select>
            </Col>
          </Row>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowMembersModal(false)}>
            {t('common.close', 'Close')}
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        show={!!deleteTarget}
        title={t('common.delete', 'Delete')}
        message={t('team.confirmDelete', 'Are you sure you want to delete this team?')}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.tea_id)}
        onCancel={() => setDeleteTarget(null)}
        isDeleting={deleteMutation.isPending}
      />
    </div>
  )
}