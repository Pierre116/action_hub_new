import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button, Modal, Form, Alert, Badge } from 'react-bootstrap'
import { ColumnDef } from '@tanstack/react-table'
import api from '../../lib/api'
import CrudTable from '../../components/shared/CrudTable'
import ConfirmModal from '../../components/shared/ConfirmModal'
import { t } from '../../lib/i18n'

interface CategoryRecord {
  top_id?: number
  top_code: string
  top_name: string
  top_name_en?: string
  top_name_cn?: string
  top_active: number
}

function getCategoryIdentifier(category: CategoryRecord): string {
  return category.top_code || String(category.top_id || '')
}

export default function AdminCategories() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingCategory, setEditingCategory] = useState<CategoryRecord | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<CategoryRecord | null>(null)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // Form state
  const [formData, setFormData] = useState({
    code: '',
    name_en: '',
    name_cn: '',
  })

  // Show success message and auto-hide
  const showSuccess = (msg: string) => {
    setSuccessMsg(msg)
    setTimeout(() => setSuccessMsg(''), 3000)
  }

  const { data: businessThemes = [], isLoading } = useQuery({
    queryKey: ['admin', 'topics'],
    queryFn: async () => {
      const response = await api.get('/api/admin/topics?include_inactive=true')
      return response.data.data as CategoryRecord[]
    },
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => api.post('/api/admin/topics', {
      code: data.code,
      name_en: data.name_en,
      name_cn: data.name_cn,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] })
      setShowModal(false)
      resetForm()
      showSuccess(t('businessTheme.created', 'Category created'))
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ code, data }: { code: string; data: typeof formData }) => 
      api.patch(`/api/admin/topics/${code}`, {
        code: data.code,
        name_en: data.name_en,
        name_cn: data.name_cn,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] })
      setShowModal(false)
      setEditingCategory(null)
      resetForm()
      showSuccess(t('businessTheme.updated', 'Category updated'))
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  // Toggle active status mutation
  const toggleActiveMutation = useMutation({
    mutationFn: async (category: CategoryRecord) => {
      const newActive = category.top_active ? 0 : 1
      const response = await api.patch(`/api/admin/topics/${getCategoryIdentifier(category)}`, { active: newActive })
      return response.data
    },
    onSuccess: (_, category) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] })
      showSuccess(category.top_active 
        ? t('admin.topics.deactivated', 'Category deactivated')
        : t('admin.topics.activated', 'Category activated'))
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (code: string) => api.delete(`/api/admin/topics/${code}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'topics'] })
      setDeleteTarget(null)
      showSuccess(t('businessTheme.deleted', 'Category deleted'))
    },
    onError: (err: unknown) => {
      const response = (err as { response?: { data?: { error?: { message?: string } } } })?.response
      setError(response?.data?.error?.message || t('common.error', 'Error'))
      setDeleteTarget(null)
    },
  })

  const resetForm = () => {
    setFormData({
      code: '',
      name_en: '',
      name_cn: '',
    })
    setError('')
  }

  const handleAdd = () => {
    resetForm()
    setEditingCategory(null)
    setDeleteTarget(null)
    setShowModal(true)
  }

  const handleEdit = (category: CategoryRecord) => {
    setEditingCategory(category)
    setFormData({
      code: category.top_code,
      name_en: category.top_name_en || '',
      name_cn: category.top_name_cn || '',
    })
    setError('')
    setShowModal(true)
  }

  const handleToggleActive = (category: CategoryRecord) => {
    toggleActiveMutation.mutate(category)
  }

  const handleDelete = (category: CategoryRecord) => {
    setError('')
    setDeleteTarget(category)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (editingCategory) {
      updateMutation.mutate({ code: getCategoryIdentifier(editingCategory), data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const columns: ColumnDef<CategoryRecord>[] = [
    {
      accessorKey: 'top_code',
      header: t('businessTheme.id', 'Code'),
      cell: ({ row }) => getCategoryIdentifier(row.original),
    },
    {
      accessorKey: 'top_name_en',
      header: t('businessTheme.nameEn', 'Name (EN)'),
    },
    {
      accessorKey: 'top_name_cn',
      header: t('businessTheme.nameCn', 'Name (CN)'),
    },
    {
      accessorKey: 'top_active',
      header: t('businessTheme.status', 'Status'),
      cell: ({ row }) => (
        <Badge bg={row.original.top_active ? 'success' : 'secondary'}>
          {row.original.top_active ? t('common.active', 'Active') : t('common.inactive', 'Inactive')}
        </Badge>
      ),
    },
    {
      id: 'actions',
      header: t('common.actions', 'Actions'),
      cell: ({ row }) => {
        const category = row.original
        return (
          <div className="d-flex gap-1">
            <Button variant="outline-primary" size="sm" onClick={() => handleEdit(category)}>
              {t('common.edit', 'Edit')}
            </Button>
            <Button 
              variant={category.top_active ? 'outline-warning' : 'outline-success'} 
              size="sm"
              onClick={() => handleToggleActive(category)}
              disabled={toggleActiveMutation.isPending}
            >
              {category.top_active ? t('businessTheme.deactivate', 'Deactivate') : t('businessTheme.activate', 'Activate')}
            </Button>
            <Button variant="outline-danger" size="sm" onClick={() => handleDelete(category)}>
              {t('common.delete', 'Delete')}
            </Button>
          </div>
        )
      },
    },
  ]

  return (
    <div>
      {successMsg && <Alert variant="success" dismissible onClose={() => setSuccessMsg('')}>{successMsg}</Alert>}
      {error && <Alert variant="danger" dismissible onClose={() => setError('')}>{error}</Alert>}
      
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>{t('nav.businessThemes', 'Categories')}</h2>
      </div>

      <CrudTable
        data={businessThemes}
        columns={columns}
        isLoading={isLoading}
        onAdd={handleAdd}
        searchPlaceholder={t('common.search', 'Search...')}
        addButtonLabel={t('businessTheme.addTheme', 'Add Category')}
      />

      {/* Add/Edit Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>
            {editingCategory ? t('businessTheme.editTheme', 'Edit Category') : t('businessTheme.addTheme', 'Add Category')}
          </Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            {error && <Alert variant="danger">{error}</Alert>}
            
            <Form.Group className="mb-3">
              <Form.Label>{t('businessTheme.id', 'Code')} *</Form.Label>
              <Form.Control
                type="text"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>{t('businessTheme.nameEn', 'Name (EN)')}</Form.Label>
              <Form.Control
                type="text"
                value={formData.name_en}
                onChange={(e) => setFormData({ ...formData, name_en: e.target.value })}
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>{t('businessTheme.nameCn', 'Name (CN)')}</Form.Label>
              <Form.Control
                type="text"
                value={formData.name_cn}
                onChange={(e) => setFormData({ ...formData, name_cn: e.target.value })}
              />
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

      <ConfirmModal
        show={!!deleteTarget}
        title={t('common.delete', 'Delete')}
        message={t('businessTheme.confirmDelete', 'Are you sure you want to delete this category?')}
        onConfirm={() => deleteTarget && deleteMutation.mutate(getCategoryIdentifier(deleteTarget))}
        onCancel={() => setDeleteTarget(null)}
        isDeleting={deleteMutation.isPending}
        variant="danger"
      />
    </div>
  )
}
