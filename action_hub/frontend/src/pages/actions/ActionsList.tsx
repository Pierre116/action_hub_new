import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Row, Col, Form, Button, Badge, Card } from 'react-bootstrap'
import { ColumnDef } from '@tanstack/react-table'
import api from '../../lib/api'
import CrudTable from '../../components/shared/CrudTable'
import StatusBadge from '../../components/shared/StatusBadge'
import { t } from '../../lib/i18n'
import { formatChinaDate } from '../../lib/dateTime'
import { useAuth } from '../../contexts/AuthContext'

interface ActionItem {
  act_id: number
  act_ref: string
  act_title: string
  act_tags?: string | null
  act_priority: string
  act_status: string
  act_deadline: string | null
  act_team_id: number | null
  act_topic_code: string | null
  act_owner_id: number | null
  team_name: string | null
  topic_name: string | null
  owner_name: string | null
  creator_name: string | null
  act_created_at: string
  act_meeting_inst_id?: number | null
  meeting_title?: string | null
  meeting_date?: string | null
  series_name?: string | null
  series_id?: number | null
  is_masked_private?: boolean
  is_private_series?: boolean
}

interface TopicOption {
  top_id: number
  top_name: string
  top_code?: string
}

interface SeriesOption {
  mtg_id: number
  mtg_title: string
}

interface UserOption {
  usr_id: number
  usr_display_name: string
  usr_team_id?: number | null
  team_ids?: number[]
}

const STATUSES = ['Not started', 'On-track', 'Late', 'Done', 'Cancelled']

function inferYear(value?: string | null): number {
  const parsed = value ? new Date(value) : null
  if (parsed && !Number.isNaN(parsed.getTime())) {
    return parsed.getFullYear()
  }
  return new Date().getFullYear()
}

function formatSeriesRef(seriesId?: number | null, createdAt?: string | null): string {
  if (!seriesId) return ''
  const year = inferYear(createdAt)
  return `SER-${year}-${String(seriesId).padStart(6, '0')}`
}

function formatTags(tags?: string | null): string {
  return String(tags || '')
    .split(',')
    .map((tag) => tag.trim().replace(/^#+/, ''))
    .filter(Boolean)
    .map((tag) => `#${tag.toUpperCase()}`)
    .join(', ') || '-'
}

export default function ActionsList() {
  const navigate = useNavigate()
  const { user } = useAuth()

  // Filter state
  const [filters, setFilters] = useState({
    status: '',
    series_id: '',
    topic_id: '',
    search: '',
    hide_closed: true,
    lead_id: '',
  })

  // Fetch actions with filters
  const { data: actionsData, isLoading } = useQuery({
    queryKey: ['actions', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.status) params.append('status_family', filters.status)
      if (filters.series_id) params.append('series_id', filters.series_id)
      if (filters.topic_id) params.append('topic_id', filters.topic_id)
      if (filters.search) params.append('search', filters.search)
      if (filters.hide_closed && !filters.status) params.append('status_family_not', 'Done,Cancelled')
      if (filters.lead_id) params.append('lead_id', filters.lead_id)
      params.append('per_page', '500')
      params.append('sort_by', 'deadline')
      params.append('sort_order', 'asc')
      
      const response = await api.get(`/api/actions?${params.toString()}`)
      return response.data.data
    },
  })

  const actions: ActionItem[] = actionsData?.items || []
  const pagination = actionsData?.pagination || { page: 1, per_page: 500, total: 0, total_pages: 1 }

  // Group actions by lead (owner_name)
  const groupedByLead = useMemo(() => {
    const groups: { lead: string; actions: ActionItem[] }[] = []
    const map = new Map<string, ActionItem[]>()
    for (const action of actions) {
      const key = action.owner_name || t('actions.unassigned', 'Unassigned')
      if (!map.has(key)) {
        map.set(key, [])
      }
      map.get(key)!.push(action)
    }
    for (const [lead, items] of map) {
      groups.push({ lead, actions: items })
    }
    groups.sort((a, b) => a.lead.localeCompare(b.lead))
    return groups
  }, [actions])

  // Fetch meeting series for filter
  const { data: seriesList = [] } = useQuery<SeriesOption[]>({
    queryKey: ['meetings', 'series'],
    queryFn: async () => {
      const response = await api.get('/api/meetings/series')
      return response.data.data || []
    },
  })

  // Fetch topics for filter
  const { data: topics = [] } = useQuery({
    queryKey: ['topics'],
    queryFn: async () => {
      const response = await api.get('/api/topics')
      return response.data.data
    },
  })

  // Fetch users for lead filter
  const { data: allUsers = [] } = useQuery<UserOption[]>({
    queryKey: ['users', 'light'],
    queryFn: async () => {
      const response = await api.get('/api/users')
      return response.data.data || []
    },
  })

  // Compute team leads: users belonging to the same team(s) as the current user
  const teamLeadOptions = useMemo(() => {
    if (!user || !allUsers.length) return allUsers
    const currentUser = allUsers.find(u => u.usr_id === user.id)
    const myTeamIds = currentUser?.team_ids?.length ? currentUser.team_ids : (currentUser?.usr_team_id ? [currentUser.usr_team_id] : [])
    if (!myTeamIds.length) return allUsers
    return allUsers.filter(u => {
      const uTeamIds = u.team_ids?.length ? u.team_ids : (u.usr_team_id ? [u.usr_team_id] : [])
      return uTeamIds.some(tid => myTeamIds.includes(tid))
    })
  }, [user, allUsers])

  const columns: ColumnDef<ActionItem>[] = [
    {
      accessorKey: 'act_title',
      header: t('action.title', 'Title'),
      cell: ({ row }) => {
        const isLocked = row.original.is_private_series || row.original.is_masked_private
        return (
          <div style={{ minWidth: '280px' }}>
            <div className="small fw-semibold text-muted">{row.original.act_ref || `ACT-${inferYear(row.original.act_created_at)}-${String(row.original.act_id).padStart(5, '0')}`}</div>
            {isLocked ? (
              <div className="d-flex align-items-center gap-1">
                <span style={{ filter: 'blur(4px)', userSelect: 'none' }}>{row.original.act_title}</span>
                <span title={t('actions.privateSeries', 'This action belongs to a restricted meeting series')} style={{ cursor: 'default' }}>🔒</span>
              </div>
            ) : (
              <div>{row.original.act_title}</div>
            )}
          </div>
        )
      },
    },
    {
      accessorKey: 'owner_name',
      header: t('action.lead', 'Lead'),
      cell: ({ getValue }) => getValue() || '-',
    },
    {
      accessorKey: 'act_status',
      header: t('common.status', 'Status'),
      cell: ({ getValue }) => <StatusBadge status={getValue() as string} />,
    },
    {
      accessorKey: 'topic_name',
      header: t('common.category', 'Category'),
      cell: ({ getValue }) => getValue() || '-',
    },
    {
      accessorKey: 'act_tags',
      header: t('common.tags', 'Tags'),
      cell: ({ row }) => formatTags(row.original.act_tags),
    },
    {
      accessorKey: 'series_name',
      header: t('meetings.series', 'Meeting Series'),
      cell: ({ row }) => {
        if (!row.original.series_id) return '-'
        const ref = formatSeriesRef(row.original.series_id, row.original.act_created_at)
        return (
          <div>
            <div className="small fw-semibold text-muted">{ref}</div>
            <div className="small">{row.original.series_name || '-'}</div>
          </div>
        )
      },
      enableSorting: true,
    },
    {
      accessorKey: 'act_deadline',
      header: t('common.deadline', 'Deadline'),
      cell: ({ row }) => {
        const deadline = row.original.act_deadline
        if (!deadline) return '-'
        
        const deadlineDate = new Date(deadline)
        const today = new Date()
        today.setHours(0, 0, 0, 0)
        
        let variant = ''
        if (deadlineDate < today) {
          variant = 'danger'
        } else if (deadlineDate.getTime() - today.getTime() < 7 * 24 * 60 * 60 * 1000) {
          variant = 'warning'
        }
        
        return (
          <span className={variant ? `text-${variant}` : ''}>
            {formatChinaDate(deadlineDate)}
          </span>
        )
      },
    },
  ]

  const handleRowClick = (action: ActionItem) => {
    navigate(`/actions/${action.act_id}`)
  }

  const handleAdd = () => {
    navigate('/actions/new')
  }

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>{t('nav.actions', 'Actions')}</h2>
        <Button variant="primary" onClick={handleAdd}>
          {t('nav.newAction', 'New Action')}
        </Button>
      </div>

      {/* Filters */}
      <div className="card mb-4">
        <div className="card-body py-2">
          <Row className="g-2 align-items-end">
            <Col md={2}>
              <Form.Select size="sm"
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
              >
                <option value="">{t('common.allStatuses', 'All Statuses')}</option>
                {STATUSES.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </Form.Select>
            </Col>
            <Col md={2}>
              <Form.Select size="sm"
                value={filters.series_id}
                onChange={(e) => handleFilterChange('series_id', e.target.value)}
              >
                <option value="">{t('meetings.allSeries', 'All Series')}</option>
                {seriesList.map((s: SeriesOption) => (
                  <option key={s.mtg_id} value={s.mtg_id}>
                    {s.mtg_title ? s.mtg_title : `#${s.mtg_id}`}
                  </option>
                ))}
              </Form.Select>
            </Col>
            <Col md={2}>
              <Form.Select size="sm"
                value={filters.topic_id}
                onChange={(e) => handleFilterChange('topic_id', e.target.value)}
              >
                <option value="">{t('common.allCategories', 'All Categories')}</option>
                {topics.map((topic: TopicOption) => (
                  <option key={topic.top_id} value={topic.top_id}>
                    {topic.top_name}
                  </option>
                ))}
              </Form.Select>
            </Col>
            <Col md={2}>
              <Form.Select size="sm"
                value={filters.lead_id}
                onChange={(e) => handleFilterChange('lead_id', e.target.value)}
              >
                <option value="">{t('actions.allLeads', 'All Leads (My Team)')}</option>
                {teamLeadOptions.map((u) => (
                  <option key={u.usr_id} value={u.usr_id}>{u.usr_display_name}</option>
                ))}
              </Form.Select>
            </Col>
            <Col md={2}>
              <Form.Control size="sm"
                type="text"
                placeholder={t('action.searchPlaceholder', 'Search...')}
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
              />
            </Col>
            <Col md={2} className="d-flex align-items-center gap-3">
              <Form.Check
                type="switch"
                label={t('actions.hideClosed', 'Hide closed')}
                checked={filters.hide_closed}
                onChange={(e) => setFilters(prev => ({ ...prev, hide_closed: e.target.checked }))}
              />
            </Col>
          </Row>
        </div>
      </div>
      <div className="d-flex flex-column gap-3">
        {isLoading ? (
          <Card><Card.Body className="text-center py-4"><span className="text-muted">{t('common.loading', 'Loading...')}</span></Card.Body></Card>
        ) : groupedByLead.length === 0 ? (
          <Card><Card.Body className="text-center py-4"><span className="text-muted">{t('dashboard.noActions', 'No actions found.')}</span></Card.Body></Card>
        ) : groupedByLead.map((group) => (
          <Card key={group.lead}>
            <Card.Header className="d-flex justify-content-between align-items-center py-2">
              <strong className="small">{group.lead}</strong>
              <Badge bg="secondary">{group.actions.length}</Badge>
            </Card.Header>
            <Card.Body className="p-0">
              <CrudTable
                data={group.actions}
                columns={columns}
                isLoading={false}
                onRowClick={handleRowClick}
                pageSize={50}
              />
            </Card.Body>
          </Card>
        ))}
      </div>
    </div>
  )
}
