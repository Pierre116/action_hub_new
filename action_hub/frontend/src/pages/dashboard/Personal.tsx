import { useEffect, useMemo, useState } from 'react'
import { Badge, Table, Tabs, Tab, Alert } from 'react-bootstrap'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../../lib/api'
import StatusBadge from '../../components/shared/StatusBadge'
import { t } from '../../lib/i18n'
import { formatChinaDate, formatChinaDateTimeNoSeconds } from '../../lib/dateTime'

interface DashboardAction {
  act_id: number
  act_ref: string
  act_title: string
  act_desc?: string | null
  act_status: string
  act_priority?: string
  act_deadline: string | null
  act_start_date?: string | null
  act_created_at?: string
  act_updated_at?: string
  act_actual_date?: string | null
  act_meeting_inst_id?: number | null
  topic_name?: string | null
  meeting_title?: string | null
  creator_name?: string | null
}

interface TopicGroup {
  topic_name: string
  topic_id: number | null
  open: number
  overdue: number
  actions: DashboardAction[]
}

interface PendingStep {
  step_id: number
  step_key: string
  status: string
  entered_at: string | null
  sla_deadline: string | null
  instance_id: number
  action_id: number | null
  action_title: string | null
  action_status: string | null
  action_priority: string | null
  workflow_name: string
  team_name: string | null
}

function inferYear(value?: string | null): number {
  const parsed = value ? new Date(value) : null
  if (parsed && !Number.isNaN(parsed.getTime())) {
    return parsed.getFullYear()
  }
  return new Date().getFullYear()
}

function formatDecisionRef(decision: { mdc_id?: number | null; mdc_created_at?: string | null }): string {
  if (!decision.mdc_id) return '-'
  return `DEC-${inferYear(decision.mdc_created_at)}-${String(decision.mdc_id).padStart(5, '0')}`
}

function formatMeetingLabel(_meetingId?: number | null, meetingTitle?: string | null): string {
  return meetingTitle || '-'
}

function formatTimestampNoSeconds(value?: string | null): string {
  return formatChinaDateTimeNoSeconds(value)
}

function formatDateOnly(value?: string | null): string {
  return formatChinaDate(value)
}

function decisionStatusBadgeVariant(statusFamily?: string | null): string {
  if (statusFamily === 'Active') return 'success'
  if (statusFamily === 'Closed') return 'secondary'
  return 'secondary'
}

const personalDashboardTableStyle = {
  fontSize: '0.875rem',
}

const personalDashboardFixedTableStyle = {
  ...personalDashboardTableStyle,
  tableLayout: 'fixed' as const,
}

export default function DashboardPersonal() {
  const [activeTab, setActiveTab] = useState(() => (window.location.hash || '#overview').replace('#', ''))

  useEffect(() => {
    const syncFromHash = () => {
      const nextTab = (window.location.hash || '#overview').replace('#', '')
      setActiveTab(nextTab || 'overview')
    }
    syncFromHash()
    window.addEventListener('hashchange', syncFromHash)
    return () => window.removeEventListener('hashchange', syncFromHash)
  }, [])

  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['dashboard', 'personal'],
    queryFn: async () => {
      const response = await api.get('/api/dashboard/personal')
      return response.data.data
    },
  })

  const { data: pendingSteps = [] } = useQuery<PendingStep[]>({
    queryKey: ['workflow', 'my-steps'],
    queryFn: async () => {
      const response = await api.get('/api/workflow/my-steps')
      return response.data
    },
  })

  const { data: decisionDashboard } = useQuery({
    queryKey: ['dashboard', 'decisions', 'all'],
    queryFn: async () => {
      const response = await api.get('/api/dashboard/decisions', { params: { scope: 'all', limit: 5 } })
      return response.data.data
    },
  })

  const recentDecisions = decisionDashboard?.recent || []
  const overdueActions: DashboardAction[] = dashboardData?.overdue_actions || []
  const dueSoonActions: DashboardAction[] = dashboardData?.due_this_week || dashboardData?.due_soon_actions || []
  const recentCompleted: DashboardAction[] = dashboardData?.recent_completed || []
  const allActions: DashboardAction[] = dashboardData?.all_actions || []
  const byTopic: TopicGroup[] = dashboardData?.by_topic || []
  const workloadForecast = dashboardData?.workload_forecast || []

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

  const sortedAllActions = useMemo(() => {
    return [...allActions]
      .filter((a) => a.act_status !== 'Cancelled')
      .sort((left, right) => {
        if (!left.act_deadline && !right.act_deadline) return 0
        if (!left.act_deadline) return 1
        if (!right.act_deadline) return -1
        return String(left.act_deadline).localeCompare(String(right.act_deadline))
      })
  }, [allActions])

  const ganttRows = useMemo(() => {
    return sortedAllActions
      .filter((action) => action.act_deadline || action.act_start_date || action.act_created_at)
      .map((action) => {
        const start = new Date(action.act_start_date || action.act_created_at || new Date().toISOString())
        const end = new Date(action.act_deadline || action.act_start_date || action.act_created_at || new Date().toISOString())
        return {
          ...action,
          ganttStart: start,
          ganttEnd: end < start ? start : end,
          displayStatus: normalizeActionStatus(action.act_status, action.act_deadline),
        }
      })
  }, [sortedAllActions])

  const ganttBounds = useMemo(() => {
    if (ganttRows.length === 0) return null
    const starts = ganttRows.map((row) => row.ganttStart.getTime())
    const ends = ganttRows.map((row) => row.ganttEnd.getTime())
    const min = Math.min(...starts)
    const max = Math.max(...ends)
    return { min, max: Math.max(max, min + 86400000) }
  }, [ganttRows])

  const DeadlineCell = ({ deadline }: { deadline: string | null }) => {
    if (!deadline) return <span className="text-muted">—</span>
    const d = new Date(deadline)
    const now = new Date(); now.setHours(0, 0, 0, 0)
    const diff = Math.ceil((d.getTime() - now.getTime()) / 86400000)
    const cls = diff < 0 ? 'text-danger fw-bold' : diff <= 7 ? 'text-warning' : ''
    const label = diff < 0 ? `${Math.abs(diff)}d overdue` : diff === 0 ? 'Today' : diff <= 7 ? `${diff}d left` : formatChinaDate(d)
    return <span className={cls}>{label}</span>
  }

  const ActionTable = ({
    actions,
    emptyMsg,
    showCategory = false,
    showMeeting = false,
    showDeadline = true,
  }: {
    actions: DashboardAction[]
    emptyMsg: string
    showCategory?: boolean
    showMeeting?: boolean
    showDeadline?: boolean
  }) => (
    actions.length === 0 ? (
      <p className="text-muted small py-2 px-3 mb-0">{emptyMsg}</p>
    ) : (
      <Table responsive hover size="sm" className="mb-0" style={personalDashboardFixedTableStyle}>
        {(() => {
          const otherColumnCount = 6 + (showCategory ? 1 : 0) + (showMeeting ? 1 : 0) + (showDeadline ? 0 : -1)
          const totalUnits = otherColumnCount + 4
          const otherWidth = `${100 / totalUnits}%`
          const contentWidth = `${(4 * 100) / totalUnits}%`
          return (
            <colgroup>
              <col style={{ width: otherWidth }} />
              <col style={{ width: otherWidth }} />
              <col style={{ width: contentWidth }} />
              {showCategory ? <col style={{ width: otherWidth }} /> : null}
              {showMeeting ? <col style={{ width: otherWidth }} /> : null}
              <col style={{ width: otherWidth }} />
              <col style={{ width: otherWidth }} />
              {showDeadline ? <col style={{ width: otherWidth }} /> : null}
              <col style={{ width: otherWidth }} />
            </colgroup>
          )
        })()}
        <thead>
          <tr>
            <th>{t('common.id', 'ID')}</th>
            <th>{t('common.title', 'Title')}</th>
            <th>{t('decisions.content', 'Content')}</th>
            {showCategory ? <th>{t('common.category', 'Category')}</th> : null}
            {showMeeting ? <th>{t('meetings.meeting', 'Meeting')}</th> : null}
            <th>{t('common.createdBy', 'Created by')}</th>
            <th>{t('common.updatedAt', 'Updated')}</th>
            {showDeadline ? <th>{t('common.deadline', 'Deadline')}</th> : null}
            <th>{t('common.status', 'Status')}</th>
          </tr>
        </thead>
        <tbody>
          {actions.map((a) => (
            <tr key={a.act_id}>
              <td className="small fw-semibold text-muted text-truncate" title={a.act_ref || `#${a.act_id}`}>
                <Link to={`/actions/${a.act_id}`} className="text-decoration-none">
                  {a.act_ref || `#${a.act_id}`}
                </Link>
              </td>
              <td className="small text-truncate" title={a.act_title}>
                <Link to={`/actions/${a.act_id}`} className="text-decoration-underline">{a.act_title}</Link>
              </td>
              <td className="small text-truncate" title={a.act_desc || '-'}>{a.act_desc || '-'}</td>
              {showCategory ? <td className="small text-truncate" title={a.topic_name || '—'}>{a.topic_name || '—'}</td> : null}
              {showMeeting ? <td className="small text-truncate" title={formatMeetingLabel(a.act_meeting_inst_id, a.meeting_title)}>{formatMeetingLabel(a.act_meeting_inst_id, a.meeting_title)}</td> : null}
              <td className="small text-truncate" title={a.creator_name || '-'}>{a.creator_name || '-'}</td>
              <td className="small text-truncate" title={formatDateOnly(a.act_updated_at || a.act_created_at)}>{formatDateOnly(a.act_updated_at || a.act_created_at)}</td>
              {showDeadline ? <td><DeadlineCell deadline={a.act_deadline} /></td> : null}
              <td><StatusBadge status={normalizeActionStatus(a.act_status, a.act_deadline)} /></td>
            </tr>
          ))}
        </tbody>
      </Table>
    )
  )

  const handleTabSelect = (key: string | null) => {
    const nextTab = key || 'overview'
    setActiveTab(nextTab)
    window.location.hash = nextTab
  }

  if (isLoading) {
    return <div>{t('common.loading', 'Loading')}</div>
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">
        <div>
          <h2 className="mb-1">{t('dashboard.personal', 'My Dashboard')}</h2>
        </div>
      </div>

      <Tabs activeKey={activeTab} onSelect={handleTabSelect} className="mb-4">
        <Tab eventKey="overview" title={t('dashboard.overview', 'Overview')}>
          <div className="pt-3">
            {overdueActions.length > 0 && (
              <div className="card border-danger mb-3">
                <div className="card-header bg-danger bg-opacity-10 d-flex justify-content-between align-items-center py-2">
                  <strong className="text-danger small">{t('dashboard.overdueActions', 'Overdue Actions')}</strong>
                  <Badge bg="danger">{overdueActions.length}</Badge>
                </div>
                <div className="card-body p-0">
                  <ActionTable actions={overdueActions} emptyMsg="" showCategory showMeeting />
                </div>
              </div>
            )}

            <div className="card mb-3">
              <div className="card-header d-flex justify-content-between align-items-center py-2">
                <strong className="small">{t('dashboard.dueSoon', 'Due This Week')}</strong>
                <Badge bg="warning" text="dark">{dueSoonActions.length}</Badge>
              </div>
              <div className="card-body p-0">
                <ActionTable actions={dueSoonActions} emptyMsg={t('dashboard.noDueSoon', 'Nothing due this week. You\'re on track!')} showCategory showMeeting />
              </div>
            </div>

            <div className="card mb-3">
              <div className="card-header d-flex justify-content-between align-items-center py-2">
                <strong className="small">{t('dashboard.recentCompleted', 'Recently Completed')}</strong>
                <Badge bg="success">{recentCompleted.length}</Badge>
              </div>
              <div className="card-body p-0">
                <ActionTable actions={recentCompleted} emptyMsg={t('dashboard.noRecentCompleted', 'No recently completed actions.')} showCategory showMeeting showDeadline={false} />
              </div>
            </div>

            <div className="card mb-3">
              <div className="card-header d-flex justify-content-between align-items-center py-2">
                <strong className="small">{t('dashboard.recentDecisions', 'Recent Decisions')}</strong>
                <Badge bg="info">{recentDecisions.length}</Badge>
              </div>
              <div className="card-body p-0">
                {recentDecisions.length === 0 ? (
                  <p className="text-muted small py-2 px-3 mb-0">{t('decisions.no_decisions', 'No decisions found.')}</p>
                ) : (
                  <Table responsive hover size="sm" className="mb-0" style={personalDashboardFixedTableStyle}>
                    <colgroup>
                      <col style={{ width: '8.3333%' }} />
                      <col style={{ width: '8.3333%' }} />
                      <col style={{ width: '33.3333%' }} />
                      <col style={{ width: '8.3333%' }} />
                      <col style={{ width: '8.3333%' }} />
                      <col style={{ width: '8.3333%' }} />
                      <col style={{ width: '8.3333%' }} />
                      <col style={{ width: '8.3333%' }} />
                      <col style={{ width: '8.3333%' }} />
                    </colgroup>
                    <thead>
                      <tr>
                        <th>{t('common.id', 'ID')}</th>
                        <th>{t('common.title', 'Title')}</th>
                        <th>{t('decisions.content', 'Content')}</th>
                        <th>{t('common.category', 'Category')}</th>
                        <th>{t('meetings.meeting', 'Meeting')}</th>
                        <th>{t('common.createdBy', 'Created by')}</th>
                        <th>{t('common.updatedAt', 'Updated')}</th>
                        <th>{t('decisions.expiredAt', 'Expired At')}</th>
                        <th>{t('decisions.status', 'Status')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentDecisions.map((d: any) => (
                        <tr key={d.mdc_id}>
                          <td className="small fw-semibold text-muted text-truncate" title={d.mdc_id ? formatDecisionRef(d) : '-'}>
                            {d.mdc_id ? <Link to={`/decisions/${d.mdc_id}`} className="text-decoration-none">{formatDecisionRef(d)}</Link> : '-'}
                          </td>
                          <td className="small text-truncate" title={d.mdc_title || '-'}>
                            {d.mdc_id ? <Link to={`/decisions/${d.mdc_id}`} className="text-decoration-underline">{d.mdc_title}</Link> : d.mdc_title}
                          </td>
                          <td className="small text-truncate" title={d.mdc_body || '-'}>{d.mdc_body || '-'}</td>
                          <td className="small text-truncate" title={d.category_name || '-'}>{d.category_name || '-'}</td>
                          <td className="small text-truncate" title={formatMeetingLabel((d as any).mdc_meeting_id || d.mdc_instance_id, (d as any).series_title || d.meeting_title)}>{formatMeetingLabel((d as any).mdc_meeting_id || d.mdc_instance_id, (d as any).series_title || d.meeting_title)}</td>
                          <td className="small text-truncate" title={d.creator_name || '-'}>{d.creator_name || '-'}</td>
                          <td className="small text-truncate" title={formatDateOnly(d.mdc_updated_at)}>{formatDateOnly(d.mdc_updated_at)}</td>
                          <td className="small text-truncate" title={formatTimestampNoSeconds(d.mdc_status_changed_at || d.mdc_expires_at)}>{formatTimestampNoSeconds(d.mdc_status_changed_at || d.mdc_expires_at)}</td>
                          <td className="small text-truncate" title={(d as any).mdc_status_family || d.mdc_status || '-'}>
                            <Badge bg={decisionStatusBadgeVariant((d as any).mdc_status_family)}>{(d as any).mdc_status_family || d.mdc_status || '-'}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </div>
            </div>

            {pendingSteps.length > 0 && (
              <div className="card mb-3">
                <div className="card-header d-flex justify-content-between align-items-center py-2">
                  <strong className="small">{t('workflow.myPendingSteps', 'My Pending Steps')}</strong>
                  <div className="d-flex align-items-center gap-2">
                    <Badge bg="info">{pendingSteps.length}</Badge>
                    <Link to="/workflow" className="btn btn-sm btn-outline-primary py-0">{t('workflow.openDashboard', 'Workflow')}</Link>
                  </div>
                </div>
                <div className="card-body p-0">
                  <Table hover responsive size="sm" className="mb-0" style={personalDashboardTableStyle}>
                    <thead><tr><th>{t('workflow.stepName', 'Step')}</th><th>{t('action.title', 'Action')}</th><th>{t('workflow.slaDeadline', 'SLA')}</th></tr></thead>
                    <tbody>
                      {pendingSteps.slice(0, 5).map((step) => {
                        const isOverdue = step.sla_deadline && new Date(step.sla_deadline) < new Date()
                        return (
                          <tr key={step.step_id}>
                            <td><Link to={`/workflow/workbench/${step.instance_id}`} className="small">{step.step_key}</Link></td>
                            <td className="small">
                              {step.action_id ? (
                                <>
                                  <div className="fw-semibold text-muted">#{step.action_id}</div>
                                  <Link to={`/actions/${step.action_id}`}>{step.action_title || '-'}</Link>
                                </>
                              ) : <span className="text-muted">Process</span>}
                            </td>
                            <td className={isOverdue ? 'text-danger fw-bold small' : 'small'}>
                              {formatChinaDate(step.sla_deadline)}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        </Tab>

        <Tab eventKey="deadline" title={t('dashboard.byDeadline', 'By Deadline')}>
          <div className="pt-3">
            <div className="card">
              <div className="card-header py-2">
                <strong className="small">{t('dashboard.allActionsByDeadline', 'All Actions by Deadline')}</strong>
              </div>
              <div className="card-body p-0">
                <ActionTable actions={sortedAllActions} emptyMsg={t('dashboard.noActions', 'No actions found.')} showCategory showMeeting />
              </div>
            </div>
          </div>
        </Tab>

        <Tab eventKey="category" title={t('dashboard.byCategory', 'By Category')}>
          <div className="pt-3 d-flex flex-column gap-3">
            {byTopic.length === 0 ? (
              <Alert variant="light" className="mb-0 small">{t('dashboard.noCategoryGroups', 'No category groups found.')}</Alert>
            ) : byTopic.map((group) => (
              <div className="card" key={`${group.topic_id || 'none'}-${group.topic_name}`}>
                <div className="card-header d-flex justify-content-between align-items-center">
                  <strong className="small">{group.topic_name}</strong>
                  <div className="d-flex gap-2">
                    <Badge bg="primary" className="small">{t('dashboard.openShort', 'Open')}: {group.open}</Badge>
                    <Badge bg={group.overdue ? 'danger' : 'secondary'} className="small">{t('dashboard.overdue', 'Overdue')}: {group.overdue}</Badge>
                  </div>
                </div>
                <div className="card-body p-0">
                  <ActionTable actions={(group.actions || []).filter((a) => a.act_status !== 'Cancelled')} emptyMsg={t('dashboard.noActions', 'No actions found.')} showMeeting />
                </div>
              </div>
            ))}
          </div>
        </Tab>

        {/* Gantt tab hidden temporarily */}
        {false && <Tab eventKey="gantt" title={t('nav.gantt', 'Gantt')}>
          <div className="pt-3 d-flex flex-column gap-3">
            {ganttRows.length === 0 || !ganttBounds ? (
              <Alert variant="light" className="mb-0">{t('dashboard.noTimelineActions', 'No actions with timeline data available.')}</Alert>
            ) : (
              <div className="card">
                <div className="card-header">{t('dashboard.personalTimeline', 'Personal Timeline')}</div>
                <div className="card-body">
                  <div className="d-flex flex-column gap-3">
                    {ganttRows.map((row) => {
                      const totalSpan = ganttBounds.max - ganttBounds.min
                      const left = ((row.ganttStart.getTime() - ganttBounds.min) / totalSpan) * 100
                      const width = Math.max(((row.ganttEnd.getTime() - row.ganttStart.getTime()) / totalSpan) * 100, 1.5)
                      return (
                        <div key={row.act_id}>
                          <div className="d-flex justify-content-between align-items-center mb-1 small">
                            <Link to={`/actions/${row.act_id}`}>{`${row.act_ref || `#${row.act_id}`} - ${row.act_title}`}</Link>
                            <span className="text-muted">{row.topic_name || '—'}</span>
                          </div>
                          <div className="position-relative rounded bg-light" style={{ height: 18 }}>
                            <div
                              className={`position-absolute top-0 bottom-0 rounded ${row.displayStatus === 'Completed' ? 'bg-success' : row.displayStatus === 'Late' ? 'bg-danger' : row.displayStatus === 'Cancelled' ? 'bg-secondary' : row.displayStatus === 'Not started' ? 'bg-primary' : 'bg-info'}`}
                              style={{ left: `${left}%`, width: `${width}%`, minWidth: 10, opacity: row.displayStatus === 'Cancelled' ? 0.65 : 1 }}
                              title={`${formatChinaDate(row.ganttStart)} - ${formatChinaDate(row.ganttEnd)}`}
                            />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            )}

            <div className="card">
              <div className="card-header">{t('dashboard.workloadForecast', 'Workload Forecast')}</div>
              <div className="card-body p-0">
                {workloadForecast.length === 0 ? (
                  <p className="text-muted small py-2 px-3 mb-0">{t('dashboard.noForecast', 'No forecast data available.')}</p>
                ) : (
                  <Table responsive hover size="sm" className="mb-0" style={personalDashboardTableStyle}>
                    <thead>
                      <tr>
                        <th>{t('dashboard.week', 'Week')}</th>
                        <th>{t('dashboard.hours', 'Hours')}</th>
                        <th>{t('dashboard.count', 'Count')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {workloadForecast.map((bucket: any) => (
                        <tr key={bucket.week_start}>
                          <td>{bucket.label_full || bucket.label}</td>
                          <td>{bucket.total_hours || 0}</td>
                          <td>{bucket.count || 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </div>
            </div>
          </div>
        </Tab>}
      </Tabs>

      <div className="text-center mt-3">
        <Link to="/actions" className="btn btn-outline-primary btn-sm">{t('nav.actions', 'View All Actions')} →</Link>
      </div>
    </div>
  )
}
