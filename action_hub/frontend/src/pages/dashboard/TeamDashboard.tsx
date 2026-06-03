import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { Alert, Badge, Card, Col, Form, Row, Spinner, Table, Tabs, Tab } from 'react-bootstrap'
import api from '../../lib/api'
import { useAuth } from '../../contexts/AuthContext'
import StatusBadge from '../../components/shared/StatusBadge'
import { t } from '../../lib/i18n'
import { formatChinaDate } from '../../lib/dateTime'

interface TeamAction {
  act_id: number
  act_ref: string
  act_title: string
  act_desc?: string
  act_status: string
  act_priority?: string
  act_deadline: string | null
  topic_name?: string | null
  owner_name?: string | null
  meeting_series_title?: string | null
  act_meeting_inst_id?: number | null
  is_masked_private?: boolean
  assignees?: string | null
}

interface TeamMember {
  usr_id: number
  usr_display_name: string
  total: number
  open: number
  overdue: number
  due_this_week: number
}

interface TeamDashboardData {
  team: { dep_id: number; dep_code: string; dep_name_en: string }
  kpis: { total: number; open: number; done: number; overdue: number }
  overdue_actions: TeamAction[]
  overdue_by_deadline?: TeamAction[]
  overdue_by_owner?: TeamAction[]
  overdue_by_category?: TeamAction[]
  members: TeamMember[]
  all_actions: TeamAction[]
  by_lead?: { lead_name: string; open: number; overdue: number; actions: TeamAction[] }[]
  by_category?: { topic_name: string; open: number; overdue: number; actions: TeamAction[] }[]
}

export default function TeamDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const leadsTeams = user?.leads_teams || []
  const fallbackTeamId = leadsTeams.length > 0 ? Number(leadsTeams[0].id) : null
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(fallbackTeamId)

  const leadTeamOptions = useMemo(
    () => leadsTeams.map((team) => ({ id: Number(team.id), name: String(team.name || team.id) })),
    [leadsTeams],
  )

  useEffect(() => {
    if (leadTeamOptions.length === 0) {
      setSelectedTeamId(null)
      return
    }
    if (!selectedTeamId || !leadTeamOptions.some((team) => team.id === selectedTeamId)) {
      setSelectedTeamId(leadTeamOptions[0].id)
    }
  }, [leadTeamOptions, selectedTeamId])

  const { data, isLoading, error } = useQuery<TeamDashboardData>({
    queryKey: ['dashboard', 'team', selectedTeamId],
    queryFn: async () => {
      const response = await api.get(`/api/dashboard/team-lead?team_id=${selectedTeamId}`)
      return response.data.data
    },
    enabled: !!selectedTeamId,
  })

  if (!selectedTeamId) {
    return <Alert variant="info">{t('dashboard.noTeam', 'You are not leading any team.')}</Alert>
  }

  if (isLoading) {
    return <div className="d-flex justify-content-center py-5"><Spinner animation="border" /></div>
  }

  if (error || !data) {
    return <Alert variant="danger">{t('common.error', 'Error loading team dashboard')}</Alert>
  }

  const { kpis, overdue_actions, overdue_by_deadline = [], overdue_by_owner = [], overdue_by_category = [], members, by_lead = [], by_category = [] } = data

  const normalizeActionStatus = (status: string, deadline: string | null | undefined) => {
    if (status === 'Cancelled') return 'Cancelled'
    if (status === 'Done' || status === 'Closed' || status === 'Completed') return 'Completed'
    if (status === 'Open' || status === 'Not started') return 'Not started'
    if (deadline) {
      const now = new Date()
      now.setHours(0, 0, 0, 0)
      const deadlineDate = new Date(deadline)
      deadlineDate.setHours(0, 0, 0, 0)
      if (deadlineDate < now) return 'Late'
    }
    return 'On-track'
  }

  const DeadlineCell = ({ deadline }: { deadline: string | null }) => {
    if (!deadline) return <span className="text-muted">-</span>
    const d = new Date(deadline)
    const now = new Date(); now.setHours(0, 0, 0, 0)
    const diff = Math.ceil((d.getTime() - now.getTime()) / 86400000)
    const cls = diff < 0 ? 'text-danger fw-bold' : diff <= 7 ? 'text-warning' : ''
    const label = diff < 0 ? `${Math.abs(diff)}d overdue` : diff === 0 ? 'Today' : diff <= 7 ? `${diff}d left` : formatChinaDate(d)
    return <span className={cls}>{label}</span>
  }

  const OverdueDetailsTable = ({ rows }: { rows: TeamAction[] }) => (
    rows.length === 0 ? (
      <p className="text-muted small py-3 px-3 mb-0">{t('dashboard.noOverdueActions', 'No overdue actions.')}</p>
    ) : (
      <Table responsive hover size="sm" className="mb-0">
        <colgroup>
          <col style={{ width: '50vw', maxWidth: '50vw' }} />
        </colgroup>
        <thead>
          <tr>
            <th>{t('action.title', 'Title')}</th>
            <th>{t('common.lead', 'Lead')}</th>
            <th>{t('common.category', 'Category')}</th>
            <th>{t('meetings.meeting', 'Meeting')}</th>
            <th>{t('common.deadline', 'Deadline')}</th>
            <th>{t('common.status', 'Status')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a) => (
            <tr
              key={a.act_id}
              onClick={() => {
                if (!a.is_masked_private) {
                  navigate(`/actions/${a.act_id}`)
                }
              }}
              style={{ cursor: a.is_masked_private ? 'default' : 'pointer' }}
            >
              <td style={{ maxWidth: '50vw', overflow: 'hidden' }}>
                {a.is_masked_private ? (
                  <div className="small text-muted" style={{ opacity: 0.7 }}>
                    <div className="fw-semibold">{a.act_ref || `#${a.act_id}`}</div>
                    <div>{a.act_title}</div>
                    <div>{a.act_desc || t('dashboard.privateActionMasked', 'Private action details are hidden')}</div>
                  </div>
                ) : (
                  <>
                    <div className="small fw-semibold text-muted">{a.act_ref || `#${a.act_id}`}</div>
                    <Link to={`/actions/${a.act_id}`} className="small">{a.act_title}</Link>
                    {a.act_desc ? <div className="small text-muted text-truncate">{a.act_desc}</div> : null}
                  </>
                )}
              </td>
              <td className="small">{a.owner_name || '-'}</td>
              <td className="small">{a.topic_name || '-'}</td>
              <td className="small">{a.meeting_series_title || '-'}</td>
              <td className="small"><DeadlineCell deadline={a.act_deadline} /></td>
              <td><StatusBadge status={normalizeActionStatus(a.act_status, a.act_deadline)} /></td>
            </tr>
          ))}
        </tbody>
      </Table>
    )
  )

  return (
    <div>
      <div className="d-flex justify-content-between align-items-start flex-wrap gap-3 mb-3">
        <h2 className="mb-0">{t('dashboard.myTeam', 'My Team')}</h2>
        {leadTeamOptions.length > 1 ? (
          <Form.Group className="mb-0" style={{ minWidth: 260 }}>
            <Form.Label className="small mb-1">{t('common.team', 'Team')}</Form.Label>
            <Form.Select
              size="sm"
              value={selectedTeamId}
              onChange={(event) => setSelectedTeamId(Number(event.target.value))}
            >
              {leadTeamOptions.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
        ) : null}
      </div>

      {/* KPIs */}
      <Row className="mb-3 g-3 flex-nowrap overflow-auto">
        {[
          { label: t('dashboard.open', 'Open'), value: kpis.open, bg: 'primary' },
          { label: t('dashboard.overdue', 'Overdue'), value: kpis.overdue, bg: kpis.overdue ? 'danger' : 'secondary' },
          { label: t('dashboard.done', 'Done'), value: kpis.done, bg: 'success' },
          { label: t('dashboard.total', 'Total'), value: kpis.total, bg: 'dark' },
        ].map(({ label, value, bg }) => (
          <Col key={label} style={{ minWidth: 220 }}>
            <div className="d-flex align-items-center gap-2 border rounded px-3 py-2">
              <Badge bg={bg} style={{ fontSize: '1.1rem', minWidth: 36 }}>{value}</Badge>
              <span className="small">{label}</span>
            </div>
          </Col>
        ))}
      </Row>

      <Tabs defaultActiveKey="overview" className="mb-3">
        <Tab eventKey="overview" title={t('dashboard.overview', 'Overview')}>
          <div className="pt-3">
            {/* Members breakdown */}
            <Card className="mb-3">
              <Card.Header className="py-2"><strong className="small">{t('dashboard.teamMembers', 'Team Members')}</strong></Card.Header>
              <Card.Body className="p-0">
                <Table responsive hover size="sm" className="mb-0">
                  <thead>
                    <tr>
                      <th>{t('common.name', 'Name')}</th>
                      <th className="text-center">{t('dashboard.open', 'Open')}</th>
                      <th className="text-center">{t('dashboard.overdue', 'Overdue')}</th>
                      <th className="text-center">{t('dashboard.dueThisWeek', 'Due This Week')}</th>
                      <th className="text-center">{t('dashboard.total', 'Total')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.map((m) => (
                      <tr key={m.usr_id}>
                        <td>{m.usr_display_name}</td>
                        <td className="text-center">{m.open}</td>
                        <td className="text-center">{m.overdue > 0 ? <Badge bg="danger">{m.overdue}</Badge> : 0}</td>
                        <td className="text-center">{m.due_this_week > 0 ? <Badge bg="warning" text="dark">{m.due_this_week}</Badge> : 0}</td>
                        <td className="text-center">{m.total}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>

            {/* Overdue actions */}
            {overdue_actions.length > 0 && (
              <Card className="border-danger mb-3">
                <Card.Header className="bg-danger bg-opacity-10 py-2 d-flex justify-content-between align-items-center">
                  <strong className="text-danger small">{t('dashboard.overdueActions', 'Overdue Actions')}</strong>
                  <Badge bg="danger">{overdue_actions.length}</Badge>
                </Card.Header>
                <Card.Body className="p-0">
                  <Tabs defaultActiveKey="deadline" className="px-3 pt-3">
                    <Tab eventKey="deadline" title={t('dashboard.byDeadline', 'By Deadline')}>
                      <div className="pt-2">
                        <OverdueDetailsTable rows={overdue_by_deadline} />
                      </div>
                    </Tab>
                    <Tab eventKey="owner" title={t('common.lead', 'Lead')}>
                      <div className="pt-2">
                        <OverdueDetailsTable rows={overdue_by_owner} />
                      </div>
                    </Tab>
                    <Tab eventKey="category" title={t('dashboard.byCategory', 'By Category')}>
                      <div className="pt-2">
                        <OverdueDetailsTable rows={overdue_by_category} />
                      </div>
                    </Tab>
                  </Tabs>
                </Card.Body>
              </Card>
            )}
          </div>
        </Tab>

        <Tab eventKey="by-lead" title={t('dashboard.byLead', 'By Lead')}>
          <div className="pt-3 d-flex flex-column gap-3">
            {by_lead.length === 0 ? (
              <Alert variant="light" className="mb-0 small">{t('dashboard.noActions', 'No actions found.')}</Alert>
            ) : by_lead.map((group) => (
              <Card key={group.lead_name}>
                <Card.Header className="d-flex justify-content-between align-items-center py-2">
                  <strong className="small">{group.lead_name}</strong>
                  <div className="d-flex gap-2">
                    <Badge bg="primary" className="small">{t('dashboard.openShort', 'Open')}: {group.open}</Badge>
                    <Badge bg={group.overdue ? 'danger' : 'secondary'} className="small">{t('dashboard.overdue', 'Overdue')}: {group.overdue}</Badge>
                  </div>
                </Card.Header>
                <Card.Body className="p-0">
                  <OverdueDetailsTable rows={(group.actions || []).filter((a) => a.act_status !== 'Cancelled')} />
                </Card.Body>
              </Card>
            ))}
          </div>
        </Tab>

        <Tab eventKey="by-category" title={t('dashboard.byCategory', 'By Category')}>
          <div className="pt-3 d-flex flex-column gap-3">
            {by_category.length === 0 ? (
              <Alert variant="light" className="mb-0 small">{t('dashboard.noCategoryGroups', 'No category groups found.')}</Alert>
            ) : by_category.map((group) => (
              <Card key={group.topic_name}>
                <Card.Header className="d-flex justify-content-between align-items-center py-2">
                  <strong className="small">{group.topic_name}</strong>
                  <div className="d-flex gap-2">
                    <Badge bg="primary" className="small">{t('dashboard.openShort', 'Open')}: {group.open}</Badge>
                    <Badge bg={group.overdue ? 'danger' : 'secondary'} className="small">{t('dashboard.overdue', 'Overdue')}: {group.overdue}</Badge>
                  </div>
                </Card.Header>
                <Card.Body className="p-0">
                  <OverdueDetailsTable rows={(group.actions || []).filter((a) => a.act_status !== 'Cancelled')} />
                </Card.Body>
              </Card>
            ))}
          </div>
        </Tab>
      </Tabs>
    </div>
  )
}
