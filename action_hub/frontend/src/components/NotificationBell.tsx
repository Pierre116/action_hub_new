import { useState, useEffect, useRef } from 'react'
import { Dropdown, Badge, Spinner } from 'react-bootstrap'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { t } from '../lib/i18n'
import { formatChinaDate } from '../lib/dateTime'

interface Notification {
  ntf_id: number
  ntf_event_type: string
  ntf_title: string
  ntf_body: string | null
  ntf_action_id: number | null
  ntf_is_read: number
  ntf_created_at: string
}

interface NotificationResponse {
  data: {
    items: Notification[]
    unread_count: number
  }
}

async function fetchNotifications(): Promise<NotificationResponse> {
  const res = await api.get('/api/notifications?unread=true')
  return res.data
}

async function markAsRead(ntfId: number): Promise<void> {
  await api.post(`/api/notifications/${ntfId}/read`)
}

async function markAllAsRead(): Promise<void> {
  await api.post('/api/notifications/read-all')
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return t('notifications.justNow', 'Just now')
  if (diffMins < 60) return t('notifications.minutesAgo', '{{count}}m ago', { count: diffMins })
  if (diffHours < 24) return t('notifications.hoursAgo', '{{count}}h ago', { count: diffHours })
  if (diffDays < 7) return t('notifications.daysAgo', '{{count}}d ago', { count: diffDays })
  return formatChinaDate(date)
}

function getEventIcon(eventType: string): string {
  if (eventType === 'assigned') return '📋'
  if (eventType === 'deadline_soon') return '⏰'
  if (eventType.startsWith('meeting_memo')) return '📝'
  return '🔔'
}

function getEventLabel(eventType: string): string {
  if (eventType === 'assigned') return t('notifications.eventAssigned', 'Assigned to you')
  if (eventType === 'deadline_soon') return t('notifications.eventDeadlineSoon', 'Deadline soon')
  if (eventType.startsWith('meeting_memo')) return t('notifications.eventMeetingMemo', 'Meeting memo updated')
  const normalized = eventType.replace(/[_:]+/g, ' ').trim()
  if (!normalized) {
    return t('notifications.eventGeneral', 'Notification')
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

export default function NotificationBell() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const dropRef = useRef<HTMLDivElement>(null)

  // Poll every 30 seconds
  const { data, isLoading, error } = useQuery({
    queryKey: ['notifications'],
    queryFn: fetchNotifications,
    refetchInterval: 30000,
    staleTime: 10000,
  })

  const markReadMutation = useMutation({
    mutationFn: markAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const markAllReadMutation = useMutation({
    mutationFn: markAllAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const notifications = data?.data.items || []
  const unreadCount = data?.data.unread_count || 0

  const handleNotificationClick = (n: Notification) => {
    markReadMutation.mutate(n.ntf_id)
    setIsOpen(false)
    if (n.ntf_action_id) {
      navigate(`/actions/${n.ntf_action_id}`)
    }
  }

  const handleMarkAllRead = () => {
    markAllReadMutation.mutate()
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={dropRef} className="position-relative">
      <Dropdown show={isOpen} onToggle={(isOpen) => setIsOpen(isOpen)}>
        <Dropdown.Toggle
          variant="link"
          id="notification-dropdown"
          onClick={() => setIsOpen(!isOpen)}
          className="p-0 border-0 text-decoration-none position-relative"
          style={{ color: 'var(--brand-dark)' }}
          title={t('notifications.title', 'Notifications')}
        >
          <span style={{ fontSize: '1.25rem' }}>🔔</span>
          {unreadCount > 0 && (
            <Badge
              bg="danger"
              pill
              className="position-absolute"
              style={{
                top: '-4px',
                right: '-8px',
                fontSize: '0.625rem',
                minWidth: '1.1em',
                padding: '2px 4px',
              }}
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
        </Dropdown.Toggle>

        <Dropdown.Menu
          align="end"
          style={{
            width: '320px',
            maxHeight: '400px',
            overflowY: 'auto',
          }}
        >
          <Dropdown.Header className="d-flex justify-content-between align-items-center">
            <span>{t('notifications.title', 'Notifications')}</span>
            {unreadCount > 0 && (
              <button
                className="btn btn-link btn-sm p-0 text-muted"
                onClick={handleMarkAllRead}
                style={{ fontSize: '0.75rem' }}
              >
                {t('notifications.markAllRead', 'Mark all read')}
              </button>
            )}
          </Dropdown.Header>

          {isLoading && (
            <div className="text-center py-3">
              <Spinner animation="border" size="sm" />
            </div>
          )}

          {error && (
            <div className="text-center py-3 text-muted">
              {t('notifications.error', 'Failed to load')}
            </div>
          )}

          {!isLoading && notifications.length === 0 && (
            <div className="text-center py-3 text-muted">
              {t('notifications.empty', 'No new notifications')}
            </div>
          )}

          {notifications.map((n) => {
            const itemBody = (
              <div className="d-flex align-items-start gap-2">
                <span style={{ fontSize: '1rem' }} title={getEventLabel(n.ntf_event_type)}>{getEventIcon(n.ntf_event_type)}</span>
                <div className="flex-grow-1" style={{ minWidth: 0 }}>
                  <div className="text-uppercase text-muted" style={{ fontSize: '0.625rem', letterSpacing: '0.04em' }}>
                    {getEventLabel(n.ntf_event_type)}
                  </div>
                  <div
                    className="text-truncate"
                    style={{
                      fontSize: '0.8125rem',
                      fontWeight: n.ntf_is_read ? 400 : 600,
                      color: 'var(--brand-dark)',
                    }}
                  >
                    {n.ntf_title}
                  </div>
                  {n.ntf_body && (
                    <div
                      className="text-truncate text-muted"
                      style={{ fontSize: '0.75rem' }}
                    >
                      {n.ntf_body}
                    </div>
                  )}
                  <div className="text-muted" style={{ fontSize: '0.6875rem' }}>
                    {formatTimeAgo(n.ntf_created_at)}
                  </div>
                </div>
              </div>
            )

            const itemProps = {
              className: 'py-2',
              style: {
                backgroundColor: n.ntf_is_read ? 'transparent' : 'rgba(0, 51, 130, 0.04)',
                cursor: 'pointer',
              },
            }

            return (
              <Dropdown.Item
                key={n.ntf_id}
                as="div"
                onClick={() => handleNotificationClick(n)}
                {...itemProps}
              >
                {itemBody}
              </Dropdown.Item>
            )
          })}

          {notifications.length > 0 && (
            <>
              <Dropdown.Divider />
              <Dropdown.Item
                as="button"
                onClick={() => {
                  setIsOpen(false)
                  navigate('/notifications')
                }}
                className="text-center text-primary"
              >
                {t('notifications.viewAll', 'View all notifications')}
              </Dropdown.Item>
            </>
          )}
        </Dropdown.Menu>
      </Dropdown>
    </div>
  )
}
