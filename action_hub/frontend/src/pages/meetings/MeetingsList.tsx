import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Badge, Button } from 'react-bootstrap'
import { ColumnDef } from '@tanstack/react-table'
import api from '../../lib/api'
import CrudTable from '../../components/shared/CrudTable'
import { t } from '../../lib/i18n'
import { formatChinaDate } from '../../lib/dateTime'

interface Meeting {
  min_id: number
  min_date: string
  min_status: string
  topic_name: string | null
  creator_name: string | null
  action_count: number
  decision_count?: number
  latest_memo_date: string | null
  occurrence_access?: boolean
}

const STATUS_COLORS: Record<string, string> = {
  Scheduled: 'primary',
  InProgress: 'warning',
  Completed: 'success',
  Cancelled: 'secondary',
}

export default function MeetingsList() {
  const navigate = useNavigate()
  const [lockedMessage, setLockedMessage] = useState<string | null>(null)

  // Fetch meetings
  const { data: meetings = [], isLoading } = useQuery<Meeting[]>({
    queryKey: ['meetings'],
    queryFn: async () => {
      const response = await api.get('/api/meetings')
      return response.data.data as Meeting[]
    },
  })

  const columns: ColumnDef<Meeting>[] = [
    {
      accessorKey: 'min_id',
      header: t('common.id', 'ID'),
      cell: ({ getValue }) => `#${getValue() as number}`,
    },
    {
      accessorKey: 'min_date',
      header: t('meeting.date', 'Date'),
      cell: ({ row }) => {
        const date = row.original.min_date
        return formatChinaDate(date)
      },
    },
    {
      accessorKey: 'topic_name',
      header: t('meeting.topic', 'Category'),
      cell: ({ getValue }) => getValue() || '-',
    },
    {
      accessorKey: 'creator_name',
      header: t('meeting.createdBy', 'Created By'),
      cell: ({ getValue }) => getValue() || '-',
    },
    {
      accessorKey: 'action_count',
      header: t('meeting.actions', 'Actions'),
      cell: ({ getValue }) => {
        const count = getValue() as number
        return <Badge bg="info">{count}</Badge>
      },
    },
    {
      id: 'decision_count',
      header: t('decisions.title', 'Decisions'),
      cell: ({ row }) => {
        const meeting = row.original
        return (
          <Button
            variant="link"
            className="p-0"
            onClick={(e) => {
              e.stopPropagation()
              if (meeting.occurrence_access === false) return
              navigate(`/meetings/${meeting.min_id}?tab=decisions`)
            }}
          >
            <Badge bg="secondary">{meeting.decision_count || 0}</Badge>
          </Button>
        )
      },
    },
    {
      accessorKey: 'min_status',
      header: t('common.status', 'Status'),
      cell: ({ getValue }) => {
        const status = getValue() as string
        return <Badge bg={STATUS_COLORS[status] || 'secondary'}>{status}</Badge>
      },
    },
    {
      id: 'access',
      header: '',
      cell: ({ row }) => {
        if (row.original.occurrence_access === false) {
          return (
            <span
              title={t('meetings.occurrence_locked', 'Access restricted — you are not a participant of this meeting')}
              style={{ cursor: 'default', fontSize: '1.1em' }}
            >🔒</span>
          )
        }
        return null
      },
    },
  ]

  const handleRowClick = (meeting: Meeting) => {
    if (meeting.occurrence_access === false) {
      const owner = meeting.creator_name || t('meeting.createdBy', 'Created By')
      setLockedMessage(t('meetings.series_locked_message', 'This series is locked. Please contact {{owner}} to be added as a participant.', { owner }))
      return
    }
    navigate(`/meetings/${meeting.min_id}`)
  }

  const handleAdd = () => {
    console.log('Create meeting')
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>{t('nav.meetings', 'Meetings')}</h2>
        <Button variant="primary" onClick={handleAdd}>
          {t('meeting.new', 'New Meeting')}
        </Button>
      </div>
      {lockedMessage && (
        <Alert variant="warning" dismissible onClose={() => setLockedMessage(null)}>
          {lockedMessage}
        </Alert>
      )}
      <CrudTable
        data={meetings}
        columns={columns}
        isLoading={isLoading}
        onRowClick={handleRowClick}
        searchPlaceholder={t('common.search', 'Search meetings...')}
        pageSize={15}
      />
    </div>
  )
}
