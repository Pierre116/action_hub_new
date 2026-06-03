import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, ButtonGroup, Card, Spinner, Table } from 'react-bootstrap'
import api from '../lib/api'
import { t } from '../lib/i18n'
import { formatChinaDateTimeNoSeconds } from '../lib/dateTime'

interface NotificationItem {
  ntf_id: number
  ntf_event_type: string
  ntf_title: string
  ntf_body: string | null
  ntf_action_id: number | null
  ntf_is_read: number
  ntf_created_at: string
}

async function fetchNotifications(unreadOnly: boolean) {
  const response = await api.get('/api/notifications', { params: unreadOnly ? { unread: true } : undefined })
  return response.data.data as { items: NotificationItem[]; unread_count: number }
}

export default function NotificationsPage() {
  const queryClient = useQueryClient()
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['notifications', 'history', showUnreadOnly],
    queryFn: () => fetchNotifications(showUnreadOnly),
  })

  const markOneRead = useMutation({
    mutationFn: (notificationId: number) => api.post(`/api/notifications/${notificationId}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'history'] })
    },
  })

  const markAllRead = useMutation({
    mutationFn: () => api.post('/api/notifications/read-all'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'history'] })
    },
  })

  const deleteOne = useMutation({
    mutationFn: (notificationId: number) => api.delete(`/api/notifications/${notificationId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'history'] })
    },
  })

  const deleteAll = useMutation({
    mutationFn: () => api.post('/api/notifications/delete-all'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'history'] })
    },
  })

  const notifications = data?.items || []
  const unreadCount = data?.unread_count || 0
  const totalCount = useMemo(() => notifications.length, [notifications])

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">
        <div>
          <h2 className="mb-1">{t('notifications.history', 'Notification History')}</h2>
          <div className="text-muted small">{t('notifications.historyHelp', 'Review, mark read, and clear in-app notifications.')}</div>
        </div>
        <div className="d-flex align-items-center gap-2 flex-wrap">
          <Badge bg="danger">{t('notifications.unreadCount', 'Unread: {{count}}', { count: unreadCount })}</Badge>
          <Badge bg="secondary">{t('notifications.totalCount', 'Shown: {{count}}', { count: totalCount })}</Badge>
        </div>
      </div>

      <Card className="mb-3">
        <Card.Body className="d-flex justify-content-between align-items-center flex-wrap gap-3">
          <ButtonGroup size="sm">
            <Button variant={showUnreadOnly ? 'outline-primary' : 'primary'} onClick={() => setShowUnreadOnly(false)}>
              {t('notifications.filterAll', 'All')}
            </Button>
            <Button variant={showUnreadOnly ? 'primary' : 'outline-primary'} onClick={() => setShowUnreadOnly(true)}>
              {t('notifications.filterUnread', 'Unread Only')}
            </Button>
          </ButtonGroup>

          <div className="d-flex gap-2 flex-wrap">
            <Button size="sm" variant="outline-secondary" onClick={() => markAllRead.mutate()} disabled={markAllRead.isPending || unreadCount === 0}>
              {t('notifications.markAllRead', 'Mark all read')}
            </Button>
            <Button size="sm" variant="outline-danger" onClick={() => deleteAll.mutate()} disabled={deleteAll.isPending || totalCount === 0}>
              {t('notifications.deleteAll', 'Delete all')}
            </Button>
          </div>
        </Card.Body>
      </Card>

      <Card>
        <Card.Body className="p-0">
          {isLoading ? (
            <div className="text-center py-5"><Spinner animation="border" /></div>
          ) : isError ? (
            <Alert variant="danger" className="m-3 mb-0">{t('notifications.error', 'Failed to load notifications')}</Alert>
          ) : notifications.length === 0 ? (
            <p className="text-muted small py-3 px-3 mb-0">{t('notifications.emptyHistory', 'No notifications found.')}</p>
          ) : (
            <Table responsive hover className="mb-0 align-middle">
              <thead>
                <tr>
                  <th>{t('common.title', 'Title')}</th>
                  <th>{t('common.description', 'Description')}</th>
                  <th>{t('common.status', 'Status')}</th>
                  <th>{t('common.date', 'Date')}</th>
                  <th style={{ width: 180 }}>{t('common.actions', 'Actions')}</th>
                </tr>
              </thead>
              <tbody>
                {notifications.map((item) => (
                  <tr key={item.ntf_id} className={item.ntf_is_read ? '' : 'table-primary'}>
                    <td>
                      <div className="fw-semibold small">{item.ntf_title}</div>
                      <div className="text-muted" style={{ fontSize: '0.75rem' }}>{item.ntf_event_type}</div>
                    </td>
                    <td className="small">{item.ntf_body || '—'}</td>
                    <td>
                      <Badge bg={item.ntf_is_read ? 'secondary' : 'primary'}>
                        {item.ntf_is_read ? t('notifications.read', 'Read') : t('notifications.unread', 'Unread')}
                      </Badge>
                    </td>
                    <td className="small">{formatChinaDateTimeNoSeconds(item.ntf_created_at)}</td>
                    <td>
                      <div className="d-flex gap-2 flex-wrap">
                        {!item.ntf_is_read ? (
                          <Button size="sm" variant="outline-primary" onClick={() => markOneRead.mutate(item.ntf_id)} disabled={markOneRead.isPending}>
                            {t('notifications.markRead', 'Mark read')}
                          </Button>
                        ) : null}
                        {item.ntf_action_id ? (
                          <Button size="sm" variant="outline-secondary" href={`/actions/${item.ntf_action_id}`}>
                            {t('common.open', 'Open')}
                          </Button>
                        ) : null}
                        <Button size="sm" variant="outline-danger" onClick={() => deleteOne.mutate(item.ntf_id)} disabled={deleteOne.isPending}>
                          {t('common.delete', 'Delete')}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </div>
  )
}