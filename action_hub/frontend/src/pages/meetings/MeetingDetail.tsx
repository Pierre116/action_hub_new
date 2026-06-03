import { useState, useMemo, useRef, Fragment } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Button, Badge, Table, Form, Modal, Row, Col, Spinner, Alert, Collapse, ProgressBar } from 'react-bootstrap'
import { t, getCurrentLanguage } from '../../lib/i18n'
import api from '../../lib/api'
import { useAuth } from '../../contexts/AuthContext'
import { addChinaDaysISO, currentChinaDateISO, formatChinaDateTimeNoSeconds } from '../../lib/dateTime'

/* ───── Interfaces ───── */

interface Meeting {
  min_id: number
  min_meeting_id?: number | null
  meeting_display_id?: string | null
  meeting_serial?: number | null
  min_title: string
  min_date: string
  min_created_at?: string
  min_topic_id: number
  min_secondary_category_id?: number | null
  min_target?: string | null
  min_planned_duration_min?: number | null
  topic_name: string
  min_notes: string
  min_created_by: number
  creator_name: string
  owners: number[]
  is_owner: boolean
  meeting_status?: string
  min_periodicity?: string | null
  secondary_category_name?: string | null
  participants?: Participant[]
  compulsory_participants?: Participant[]
  optional_participants?: Participant[]
}

interface Participant {
  mpa_id: number
  mpa_user_id: number
  usr_display_name: string
  usr_email?: string
  mpa_added_at: string
  mpa_kind?: string
}

interface Decision {
  mdc_id: number
  mdc_title: string
  mdc_body: string
  mdc_context?: string | null
  mdc_reason?: string | null
  mdc_status: string
  mdc_created_by?: number
  mdc_category_id?: number
  mdc_instance_id?: number
  category_name?: string
  category_color?: string
  mdc_created_at: string
  creator_name?: string
  mdc_meeting_id?: number | null
  meeting_title?: string
  occurrence_title?: string
  occurrence_date?: string
}

interface MeetingAction {
  act_id: number
  act_ref?: string
  act_ref_code?: string
  act_title: string
  act_desc?: string | null
  act_status: string
  act_priority: string
  act_deadline?: string | null
  act_meeting_inst_id?: number
  act_created_at?: string
  occurrence_title?: string
  occurrence_date?: string
  creator_name?: string | null
  lead_name?: string | null
  assignee_names?: string | null
  asg_total?: number
}

interface SeriesInstance {
  min_id: number
  min_date: string
  min_created_at?: string | null
}

interface OccurrenceFollowUp {
  action_id: number
  action_title?: string
  afb_completion_pct: number | null
  afb_status: string | null
  afb_comment: string | null
  afb_blockers: string | null
  usr_display_name?: string
  afb_created_at?: string
}

const FEEDBACK_COLORS: Record<string, string> = {
  not_started: 'primary', on_track: 'success', late: 'warning', done: 'success', cancelled: 'danger',
}
const FEEDBACK_LABELS: Record<string, string> = {
  not_started: 'Not started', on_track: 'On-track', late: 'Late', done: 'Done', cancelled: 'Cancelled',
}

interface OccurrenceComment {
  comment_id: number
  action_id: number
  action_title?: string
  body: string
  author?: string
  created_at?: string
  cmt_created_by?: number
}

interface TopicOption {
  top_id: number
  top_name: string
}

interface UserOption {
  usr_id: number
  usr_display_name: string
  usr_role?: string
}

interface SeriesDefaultParticipant {
  msp_user_id: number
}

const statusColors: Record<string, string> = {
  Published: 'primary',
  Expired: 'secondary',
}

function formatTimestampNoSeconds(value?: string | null): string {
  return formatChinaDateTimeNoSeconds(value)
}

interface TextMemo {
  mmm_id: number
  mmm_title: string
  mmm_body: string
  mmm_date?: string | null
  mmm_created_by: number
  creator_name: string
  mmm_created_at: string
}

export default function MeetingDetail() {
  const { id } = useParams<{ id: string }>()
  const meetingId = parseInt(id || '0', 10)
  const queryClient = useQueryClient()
  const { user } = useAuth()

  /* — section collapse state — */
  const [openMemos, setOpenMemos] = useState(true)
  const [openDecisions, setOpenDecisions] = useState(true)
  const [openActions, setOpenActions] = useState(true)

  /* — PDF export — */
  const [pdfError, setPdfError] = useState<string | null>(null)

  /* — inline forms visibility — */
  const [showAddDecision, setShowAddDecision] = useState(false)
  const [showAddAction, setShowAddAction] = useState(false)
  const [showAddMemo, setShowAddMemo] = useState(false)
  const [editingMemo, setEditingMemo] = useState<TextMemo | null>(null)
  const [memoForm, setMemoForm] = useState({ title: '', body: '', date: '' })

  /* — inline decision edit — */
  const [editingDecisionId, setEditingDecisionId] = useState<number | null>(null)
  const [decisionEditForm, setDecisionEditForm] = useState({ title: '', body: '', context: '', reason: '' })
  const [decisionEditError, setDecisionEditError] = useState<string | null>(null)

  /* — action history navigation (shared across all actions, 0 = most recent previous) — */
  const [histNavOffset, setHistNavOffset] = useState(0)

  /* — auto-save state and timers — */
  const saveTimers = useRef<Record<number, ReturnType<typeof setTimeout>>>({})
  const [saveStatusById, setSaveStatusById] = useState<Record<number, 'saving' | 'saved'>>({})

  /* — inline comment drafts per action (action_id -> draft text) — */
  const [commentDrafts, setCommentDrafts] = useState<Record<number, string>>({})

  /* — new action inline form — */
  const [actionForm, setActionForm] = useState({ title: '', description: '', owner_id: '', deadline: '' })

  /* — action edit modal — */
  const [editingAction, setEditingAction] = useState<MeetingAction | null>(null)
  const [actionEditForm, setActionEditForm] = useState({ title: '', description: '', status: '', deadline: '', hold_reason: '', cancel_reason: '' })
  const [actionEditError, setActionEditError] = useState<string | null>(null)

  /* — decision edit modal — */
  const [editingDecision, setEditingDecision] = useState<Decision | null>(null)
  const [decisionModalForm, setDecisionModalForm] = useState({ title: '', body: '', context: '', reason: '', status: '' })

  /* — edit meeting modal — */
  const [showEditMeeting, setShowEditMeeting] = useState(false)
  const [meetingForm, setMeetingForm] = useState({
    title: '',
    category_id: '',
    secondary_category_id: '',
    status: 'Active',
    periodicity: '',
    target: '',
    compulsory_participant_ids: [] as number[],
    optional_participant_ids: [] as number[],
  })

  /* ───── Queries ───── */

  const { data: decisionTopics = [] } = useQuery<TopicOption[]>({
    queryKey: ['topics'],
    queryFn: async () => {
      const response = await api.get('/api/topics')
      return response.data.data || []
    },
  })

  const { data: users = [] } = useQuery<UserOption[]>({
    queryKey: ['users', 'light'],
    queryFn: async () => {
      const response = await api.get('/api/users')
      return response.data.data || []
    },
  })

  const { data: meeting, isLoading: loadingMeeting, error: meetingError } = useQuery<Meeting>({
    queryKey: ['meeting', meetingId],
    queryFn: async () => {
      const response = await api.get(`/api/meetings/${meetingId}`)
      return response.data.data
    },
    enabled: !!meetingId,
  })

  const { data: seriesDefaultParticipants = [] } = useQuery<SeriesDefaultParticipant[]>({
    queryKey: ['meeting-series-default-participants', meeting?.min_meeting_id],
    queryFn: async () => {
      const response = await api.get(`/api/meetings/series/${meeting?.min_meeting_id}`)
      return response.data.data?.default_participants || []
    },
    enabled: Boolean(meeting?.min_meeting_id),
  })
  const detailErrorCode = (meetingError as any)?.response?.data?.error?.code

  const seriesId = meeting?.min_meeting_id || null
  const meetingDecisionQueryKey = ['meeting-workspace-decisions', meetingId, seriesId] as const
  const meetingActionsQueryKey = ['meeting-workspace-actions', meetingId, seriesId] as const

  const { data: actions = [] } = useQuery<MeetingAction[]>({
    queryKey: meetingActionsQueryKey,
    queryFn: async () => {
      const response = seriesId
        ? await api.get(`/api/meetings/series/${seriesId}/actions`)
        : await api.get(`/api/meetings/${meetingId}/actions`)
      return response.data.data || []
    },
    enabled: !!meetingId && !!meeting,
  })

  const { data: decisions = [], isLoading: loadingDecisions } = useQuery<Decision[]>({
    queryKey: meetingDecisionQueryKey,
    queryFn: async () => {
      const response = seriesId
        ? await api.get(`/api/meetings/series/${seriesId}/decisions`)
        : await api.get(`/api/meetings/${meetingId}/decisions`)
      return response.data.data || []
    },
    enabled: !!meetingId && !!meeting,
  })

  const { data: occurrenceComments } = useQuery<{
    current: OccurrenceComment[]
    previous: OccurrenceComment[]
    follow_up_current?: OccurrenceFollowUp[]
    follow_up_previous?: OccurrenceFollowUp[]
    previous_occurrence_id?: number | null
  }>({
    queryKey: ['meeting', meetingId, 'occurrence-comments'],
    queryFn: async () => {
      const response = await api.get(`/api/meetings/${meetingId}/occurrence-comments`)
      return response.data.data || { current: [], previous: [], follow_up_current: [], follow_up_previous: [], previous_occurrence_id: null }
    },
    enabled: !!meetingId && !!meeting,
  })

  const { data: textMemos = [] } = useQuery<TextMemo[]>({
    queryKey: ['meeting', meetingId, 'text-memos'],
    queryFn: async () => {
      const response = await api.get(`/api/meetings/${meetingId}/text-memos`)
      return response.data.data || []
    },
    enabled: !!meetingId && !!meeting,
  })

  /* — Series instances (for history navigation) — */
  const { data: seriesInstances } = useQuery<SeriesInstance[]>({
    queryKey: ['meeting-series-all-instances', seriesId],
    queryFn: async () => {
      const response = await api.get(`/api/meetings/series/${seriesId}/instances`)
      return response.data.data || []
    },
    enabled: !!seriesId,
  })

  /* Previous occurrences before current meeting, most recent first */
  const prevOccurrences = useMemo(() => {
    if (!seriesInstances || !meeting) return []
    const currDate = meeting.min_date
    return seriesInstances
      .filter((occ) => occ.min_date < currDate || (occ.min_date === currDate && occ.min_id < meetingId))
      .sort((a, b) => b.min_id - a.min_id)
  }, [seriesInstances, meeting, meetingId])

  /* When histNavOffset > 0 fetch that specific occurrence's comments */
  const histQueryOccurrenceId = histNavOffset > 0 ? (prevOccurrences[histNavOffset]?.min_id ?? null) : null

  const { data: histOccData } = useQuery<{
    current: OccurrenceComment[]
    follow_up_current?: OccurrenceFollowUp[]
  }>({
    queryKey: ['meeting', histQueryOccurrenceId, 'occurrence-comments'],
    queryFn: async () => {
      const response = await api.get(`/api/meetings/${histQueryOccurrenceId}/occurrence-comments`)
      return response.data.data || {}
    },
    enabled: !!histQueryOccurrenceId,
  })

  const currentFollowUpByActionId = new Map<number, OccurrenceFollowUp>()
  for (const row of (occurrenceComments?.follow_up_current || [])) {
    currentFollowUpByActionId.set(row.action_id, row)
  }

  const previousFollowUpByActionId = new Map<number, OccurrenceFollowUp>()
  for (const row of (occurrenceComments?.follow_up_previous || [])) {
    previousFollowUpByActionId.set(row.action_id, row)
  }

  /* ───── Mutations ───── */

  const createDecisionMutation = useMutation({
    mutationFn: (data: { title: string; body: string; context?: string; reason?: string; category_id?: number | null }) =>
      api.post('/api/decisions/', { ...data, meeting_id: meetingId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: meetingDecisionQueryKey })
      setShowAddDecision(false)
    },
  })

  const updateDecisionMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { title: string; body: string; context?: string; reason?: string; status?: string } }) =>
      api.patch(`/api/decisions/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: meetingDecisionQueryKey })
      setEditingDecisionId(null)
      setEditingDecision(null)
      setDecisionEditError(null)
    },
    onError: (error: any) => {
      setDecisionEditError(error?.response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  const createActionMutation = useMutation({
    mutationFn: (data: typeof actionForm) =>
      api.post('/api/actions', {
        title: data.title,
        description: data.description,
        status: 'Open',
        deadline: data.deadline || null,
        topic_id: meeting?.min_topic_id || null,
        owner_id: data.owner_id ? parseInt(data.owner_id, 10) : null,
        lead_user_id: data.owner_id ? parseInt(data.owner_id, 10) : null,
        assignee_user_ids: data.owner_id ? [parseInt(data.owner_id, 10)] : undefined,
        meeting_id: meetingId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: meetingActionsQueryKey })
      setShowAddAction(false)
      setActionForm({ title: '', description: '', owner_id: '', deadline: addChinaDaysISO(7) })
    },
  })

  const updateActionMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.patch(`/api/actions/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: meetingActionsQueryKey })
      setEditingAction(null)
      setActionEditError(null)
    },
    onError: (error: any) => {
      setActionEditError(error?.response?.data?.error?.message || t('common.error', 'Error'))
    },
  })

  const createCommentMutation = useMutation({
    mutationFn: ({ actionId, body }: { actionId: number; body: string }) =>
      api.post(`/api/actions/${actionId}/comments`, { body, type: 'Comment', meeting_inst_id: meetingId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId, 'occurrence-comments'] })
    },
  })

  const editCommentMutation = useMutation({
    mutationFn: ({ commentId, body }: { commentId: number; body: string }) =>
      api.patch(`/api/actions/comments/${commentId}`, { body }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId, 'occurrence-comments'] })
    },
  })

  const createMemoMutation = useMutation({
    mutationFn: (data: { title: string; body: string; date: string }) =>
      api.post(`/api/meetings/${meetingId}/text-memos`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId, 'text-memos'] })
      setShowAddMemo(false)
      setMemoForm({ title: '', body: '', date: '' })
    },
  })

  const updateMemoMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { title: string; body: string; date: string } }) =>
      api.patch(`/api/meetings/text-memos/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId, 'text-memos'] })
      setEditingMemo(null)
      setShowAddMemo(false)
      setMemoForm({ title: '', body: '', date: '' })
    },
  })

  const deleteMemoMutation = useMutation({
    mutationFn: (mmmId: number) => api.delete(`/api/meetings/text-memos/${mmmId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId, 'text-memos'] })
    },
  })

  const meetingEditMutation = useMutation({
    mutationFn: (payload: {
      title?: string; category_id?: number | null; secondary_category_id?: number | null
      status?: string; periodicity?: string | null; target?: string | null
      compulsory_participant_ids?: number[]; optional_participant_ids?: number[]
    }) => api.patch(`/api/meetings/${meetingId}`, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meeting', meetingId] })
      setShowEditMeeting(false)
    },
  })

  /* ───── Handlers ───── */

  const handleGenerateMinutes = async () => {
    setPdfError(null)
    try {
      const lang = getCurrentLanguage()
      const response = await api.get(`/api/meetings/${meetingId}/minutes/pdf?lang=${lang}`, { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      const disposition = response.headers['content-disposition'] as string | undefined
      const filenameMatch = disposition?.match(/filename="?([^"]+)"?/)
      link.href = url
      link.download = filenameMatch?.[1] || `MoM_${meetingId}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err: any) {
      setPdfError(err?.response?.data?.error?.message || t('common.error', 'Failed to generate PDF'))
    }
  }

  const handleMemoSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingMemo) {
      updateMemoMutation.mutate({ id: editingMemo.mmm_id, data: memoForm })
    } else {
      createMemoMutation.mutate(memoForm)
    }
  }

  const openMemoModal = () => {
    const nextIndex = textMemos.length + 1
    const today = currentChinaDateISO()
    setEditingMemo(null)
    setMemoForm({ title: `${nextIndex} - ${meeting!.min_title} - ${today}`, body: '', date: today })
    setShowAddMemo(true)
  }

  const handleEditMemo = (memo: TextMemo) => {
    setEditingMemo(memo)
    setMemoForm({
      title: memo.mmm_title,
      body: memo.mmm_body,
      date: memo.mmm_date ? memo.mmm_date.slice(0, 10) : memo.mmm_created_at.slice(0, 10),
    })
    setShowAddMemo(true)
  }

  const handleDeleteMemo = (mmmId: number) => {
    if (window.confirm(t('common.confirm_delete', 'Are you sure you want to delete?'))) {
      deleteMemoMutation.mutate(mmmId)
    }
  }

  const openMeetingEdit = () => {
    if (!meeting) return
    const creatorId = Number(meeting.min_created_by || 0)
    const compulsoryIds = (meeting.compulsory_participants || meeting.participants || [])
      .filter((p) => p.mpa_kind === 'Compulsory')
      .map((p) => p.mpa_user_id)
    const optionalIds = (meeting.optional_participants || meeting.participants || [])
      .filter((p) => p.mpa_kind !== 'Compulsory')
      .map((p) => p.mpa_user_id)
      .filter((userId) => userId !== creatorId)
    if (creatorId > 0 && !compulsoryIds.includes(creatorId)) {
      compulsoryIds.push(creatorId)
    }
    setMeetingForm({
      title: meeting.min_title || '', category_id: String(meeting.min_topic_id || ''),
      secondary_category_id: String(meeting.min_secondary_category_id || ''),
      status: meeting.meeting_status || 'Active', periodicity: meeting.min_periodicity || '',
      target: meeting.min_target || '',
      compulsory_participant_ids: compulsoryIds, optional_participant_ids: optionalIds,
    })
    setShowEditMeeting(true)
  }

  const allowedParticipantOptions = useMemo(() => {
    const selectedIds = new Set<number>([
      ...meetingForm.compulsory_participant_ids,
      ...meetingForm.optional_participant_ids,
    ])
    if (!meeting?.min_meeting_id) {
      return users
    }
    const allowedSeriesIds = new Set<number>(seriesDefaultParticipants.map((participant) => participant.msp_user_id))
    for (const id of selectedIds) {
      allowedSeriesIds.add(id)
    }
    return users.filter((option) => allowedSeriesIds.has(option.usr_id))
  }, [
    meeting?.min_meeting_id,
    meetingForm.compulsory_participant_ids,
    meetingForm.optional_participant_ids,
    seriesDefaultParticipants,
    users,
  ])

  const handleCreateDecision = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    createDecisionMutation.mutate({
      title: fd.get('title') as string,
      body: fd.get('body') as string,
      context: (fd.get('context') as string) || '',
      reason: (fd.get('reason') as string) || '',
      category_id: meeting?.min_topic_id || undefined,
    })
  }

  const handleInlineDecisionSave = (decisionId: number) => {
    updateDecisionMutation.mutate({
      id: decisionId,
      data: {
        title: decisionEditForm.title,
        body: decisionEditForm.body,
        context: decisionEditForm.context,
        reason: decisionEditForm.reason,
      },
    })
  }

  const startEditDecision = (d: Decision) => {
    setDecisionEditError(null)
    setEditingDecisionId(d.mdc_id)
    setEditingDecision(d)
    setDecisionModalForm({
      title: d.mdc_title,
      body: d.mdc_body || '',
      context: d.mdc_context || '',
      reason: d.mdc_reason || '',
      status: d.mdc_status || 'Published',
    })
    setDecisionEditForm({
      title: d.mdc_title,
      body: d.mdc_body || '',
      context: d.mdc_context || '',
      reason: d.mdc_reason || '',
    })
  }

  const startEditAction = (action: MeetingAction) => {
    setActionEditError(null)
    setEditingAction(action)
    setActionEditForm({
      title: action.act_title,
      description: action.act_desc || '',
      status: action.act_status,
      deadline: (action.act_deadline || '').slice(0, 10),
      hold_reason: '',
      cancel_reason: '',
    })
  }

  const handleActionEditSave = () => {
    if (!editingAction) return
    const data: Record<string, unknown> = {
      title: actionEditForm.title.trim(),
      description: actionEditForm.description.trim() || null,
      status: actionEditForm.status,
      deadline: actionEditForm.deadline || null,
    }
    if (actionEditForm.status === 'On Hold') data.hold_reason = actionEditForm.hold_reason.trim()
    if (actionEditForm.status === 'Cancelled') data.cancel_reason = actionEditForm.cancel_reason.trim()
    updateActionMutation.mutate({ id: editingAction.act_id, data })
  }

  const handleDecisionModalSave = () => {
    if (!editingDecision) return
    updateDecisionMutation.mutate({
      id: editingDecision.mdc_id,
      data: {
        title: decisionModalForm.title.trim(),
        body: decisionModalForm.body.trim(),
        context: decisionModalForm.context.trim() || undefined,
        reason: decisionModalForm.reason.trim() || undefined,
        status: decisionModalForm.status || undefined,
      },
    })
  }

  const handleCreateAction = (e: React.FormEvent) => {
    e.preventDefault()
    createActionMutation.mutate(actionForm)
  }

  const handleCommentChange = (actionId: number, value: string) => {
    setCommentDrafts((prev) => ({ ...prev, [actionId]: value }))
    if (saveTimers.current[actionId]) {
      clearTimeout(saveTimers.current[actionId])
      delete saveTimers.current[actionId]
    }
    if (!value.trim()) return
    saveTimers.current[actionId] = setTimeout(() => {
      const existingCmt = currentCommentByActionIdRef.current.get(actionId)
      const editableCmt =
        existingCmt && Number(existingCmt.cmt_created_by || 0) === Number(user?.id || 0)
          ? existingCmt
          : undefined
      if (editableCmt && editableCmt.body === value) return
      setSaveStatusById((prev) => ({ ...prev, [actionId]: 'saving' }))
      const onDone = () => {
        setSaveStatusById((prev) => ({ ...prev, [actionId]: 'saved' }))
        setTimeout(() => setSaveStatusById((prev) => { const n = { ...prev }; delete n[actionId]; return n }), 3000)
      }
      if (editableCmt) {
        editCommentMutation.mutate({ commentId: editableCmt.comment_id, body: value }, {
          onSuccess: onDone,
          onError: () => {
            setSaveStatusById((prev) => { const n = { ...prev }; delete n[actionId]; return n })
          },
        })
      } else {
        createCommentMutation.mutate({ actionId, body: value }, {
          onSuccess: onDone,
          onError: () => {
            setSaveStatusById((prev) => { const n = { ...prev }; delete n[actionId]; return n })
          },
        })
      }
    }, 1200)
  }

  /* ───── Derived data ───── */

  const allParticipants = meeting
    ? [
      ...(meeting.compulsory_participants || (meeting.participants || []).filter((p) => p.mpa_kind === 'Compulsory')),
      ...(meeting.optional_participants || (meeting.participants || []).filter((p) => p.mpa_kind !== 'Compulsory')),
    ]
    : []

  const currentCommentByActionId = new Map<number, OccurrenceComment>()
  for (const c of occurrenceComments?.current || []) {
    currentCommentByActionId.set(c.action_id, c)
  }

  /* Keep a ref so auto-save timers can read the freshest comment map */
  const currentCommentByActionIdRef = useRef(currentCommentByActionId)
  currentCommentByActionIdRef.current = currentCommentByActionId

  /* Historical comments: offset 0 = previous from main query, offset >0 = fetched data */
  const historicalComments: OccurrenceComment[] =
    histNavOffset === 0
      ? (occurrenceComments?.previous ?? [])
      : (histOccData?.current ?? [])
  const historicalFollowUps: OccurrenceFollowUp[] =
    histNavOffset === 0
      ? (occurrenceComments?.follow_up_previous ?? [])
      : (histOccData?.follow_up_current ?? [])

  const historicalCommentByActionId = new Map<number, OccurrenceComment>()
  for (const c of historicalComments) {
    historicalCommentByActionId.set(c.action_id, c)
  }
  const historicalFollowUpByActionId = new Map<number, OccurrenceFollowUp>()
  for (const f of historicalFollowUps) {
    historicalFollowUpByActionId.set(f.action_id, f)
  }

  const statusRank: Record<string, number> = {
    Open: 1, 'In Progress': 2, 'Under Review': 3, 'On Hold': 4, Postponed: 5, Done: 6, Completed: 6, Cancelled: 7,
    Published: 1, Expired: 2,
  }
  const sortedActions = [...actions].sort((a, b) => {
    const r = (statusRank[a.act_status] || 99) - (statusRank[b.act_status] || 99)
    return r !== 0 ? r : String(a.occurrence_date || '').localeCompare(String(b.occurrence_date || ''))
  })
  const sortedDecisions = [...decisions].sort((a, b) => {
    const r = (statusRank[a.mdc_status] || 99) - (statusRank[b.mdc_status] || 99)
    return r !== 0 ? r : String(b.occurrence_date || b.mdc_created_at || '').localeCompare(String(a.occurrence_date || a.mdc_created_at || ''))
  })

  /* ───── Loading / Error ───── */

  if (loadingMeeting) {
    return <div className="d-flex justify-content-center p-5"><Spinner animation="border" /></div>
  }
  if (detailErrorCode === 'FORBIDDEN') {
    return (
      <Alert variant="warning">
        <Alert.Heading>{t('meetings.no_access_title', 'No access to this meeting')}</Alert.Heading>
        <div>{t('meetings.no_access_message', 'You are not a meeting lead or participant for this occurrence.')}</div>
      </Alert>
    )
  }
  if (!meeting) {
    return <Alert variant="danger">{t('common.error')}</Alert>
  }

  const meetingDisplayDate = meeting?.min_created_at || meeting?.min_date
  const canEdit = Boolean(meeting?.is_creator || user?.role === 'Admin')
  const canEditDecision = (_d: Decision) => canEdit
  const creatorUserId = Number(meeting?.min_created_by || 0)

  const formatDecisionRef = (decision: Decision) => {
    const sourceDate = decision.occurrence_date || decision.mdc_created_at || currentChinaDateISO()
    const parsedYear = Number.parseInt(String(sourceDate).slice(0, 4), 10)
    const year = Number.isFinite(parsedYear) ? parsedYear : new Date().getFullYear()
    return `DEC-${year}-${String(decision.mdc_id).padStart(5, '0')}`
  }

  const formatActionRef = (action: MeetingAction) => {
    const rawRef = String(action.act_ref_code || action.act_ref || '').trim()
    if (rawRef) {
      return rawRef.startsWith('ACT-') ? rawRef : `ACT-${rawRef}`
    }
    const sourceDate = action.occurrence_date || action.act_created_at || currentChinaDateISO()
    const parsedYear = Number.parseInt(String(sourceDate).slice(0, 4), 10)
    const year = Number.isFinite(parsedYear) ? parsedYear : new Date().getFullYear()
    return `ACT-${year}-${String(action.act_id).padStart(5, '0')}`
  }

  const renderParticipantName = (participant: Participant) => {
    const isCreator = Number(participant.mpa_user_id) === creatorUserId
    if (!isCreator) {
      return participant.usr_display_name
    }
    return (
      <span style={{ color: '#0d6efd', textDecoration: 'underline', fontWeight: 600 }}>
        {participant.usr_display_name} ({t('meetings.creatorLabel', 'Meeting creator')})
      </span>
    )
  }

  const participantSummary = allParticipants.length <= 4 ? allParticipants : allParticipants.slice(0, 3)

  /* ── Section header helper ── */
  const SectionHeader = ({ title, count, open, onToggle, onAdd, addLabel }: {
    title: string; count: number; open: boolean; onToggle: () => void; onAdd?: () => void; addLabel?: string
  }) => (
    <div className="d-flex justify-content-between align-items-center py-2 px-3 bg-light border rounded mb-0"
      style={{ cursor: 'pointer', userSelect: 'none' }}>
      <div onClick={onToggle} className="d-flex align-items-center gap-2 flex-grow-1">
        <span style={{ fontSize: '0.8rem' }}>{open ? '\u25BC' : '\u25B6'}</span>
        <strong>{title}</strong>
        <Badge bg="secondary" pill>{count}</Badge>
      </div>
      {onAdd && canEdit && (
        <Button variant="primary" size="sm" onClick={(e) => { e.stopPropagation(); onAdd() }}>
          {addLabel || t('common.add', '+ Add')}
        </Button>
      )}
    </div>
  )

  /* ───── Render ───── */
  return (
    <div>
      {/* ── Compact Header ── */}
      <div className="d-flex justify-content-between align-items-start mb-3">
        <div>
          <h4 className="mb-1">{meeting.meeting_display_id || `#${meeting.min_id}`}</h4>
          <div className="text-muted small d-flex flex-wrap align-items-center gap-2">
            {meetingDisplayDate && <span>{formatTimestampNoSeconds(meetingDisplayDate)}</span>}
            {meeting.topic_name && <><span>&bull;</span><span>{meeting.topic_name}</span></>}
            <span>&bull;</span>
            <Badge bg={meeting.meeting_status === 'Closed' ? 'secondary' : 'success'} className="fw-normal">
              {meeting.meeting_status || 'Active'}
            </Badge>
            {allParticipants.length > 0 && (
              <>
                <span>&bull;</span>
                <span title={allParticipants.map((p) => p.usr_display_name).join(', ')}>
                  {participantSummary.map((participant, index) => (
                    <Fragment key={`participant-summary-${participant.mpa_user_id}`}>
                      {index > 0 ? ', ' : null}
                      {renderParticipantName(participant)}
                    </Fragment>
                  ))}
                  {allParticipants.length > participantSummary.length
                    ? ` (+${allParticipants.length - participantSummary.length})`
                    : null}
                </span>
              </>
            )}
            {canEdit && (
              <>
                <span>&bull;</span>
                <Button variant="outline-primary" size="sm" className="py-0 px-2" onClick={openMeetingEdit}>
                  {t('common.edit', 'Edit')}
                </Button>
              </>
            )}
          </div>
        </div>
        <div className="d-flex gap-2 flex-shrink-0">
          {pdfError && (
            <Alert variant="danger" dismissible className="mb-0 py-1 px-2 small" onClose={() => setPdfError(null)}>
              {pdfError}
            </Alert>
          )}
          <Button variant="outline-secondary" size="sm" onClick={handleGenerateMinutes}>
            {t('meetings.generateMinutes', 'PDF')}
          </Button>
        </div>
      </div>

      {/* ── Memos Section ── */}
      <div className="mb-3">
        <SectionHeader title={t('meetings.memos', 'Memos')} count={textMemos.length}
          open={openMemos} onToggle={() => setOpenMemos(!openMemos)}
          onAdd={openMemoModal} addLabel={t('meetings.add_memo', '+ Memo')} />
        <Collapse in={openMemos}>
          <div>
            {textMemos.length === 0 ? (
              <p className="text-muted small px-3 pt-2 mb-0">{t('meetings.no_memos', 'No memos yet.')}</p>
            ) : (
              <div className="border border-top-0 rounded-bottom">
                {textMemos.map((memo, idx) => (
                  <div key={memo.mmm_id} className="border-bottom px-3 py-2">
                    <div className="d-flex justify-content-between align-items-start">
                      <div className="flex-grow-1">
                        <div className="d-flex align-items-center gap-2">
                          <Badge bg="secondary" pill style={{ fontSize: '0.7rem' }}>#{idx + 1}</Badge>
                        </div>
                        {memo.mmm_body && <div className="text-muted small mt-1" style={{ whiteSpace: 'pre-wrap' }}>{memo.mmm_body}</div>}
                      </div>
                      {meeting.is_owner && (
                        <div className="d-flex gap-1 flex-shrink-0">
                          <Button variant="link" size="sm" className="text-primary p-0" onClick={() => handleEditMemo(memo)}>{t('common.edit', 'Edit')}</Button>
                          <Button variant="link" size="sm" className="text-danger p-0" onClick={() => handleDeleteMemo(memo.mmm_id)}>{t('common.delete', 'Del')}</Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Collapse>
      </div>

      {/* ── Decisions Section ── */}
      <div className="mb-3">
        <SectionHeader title={t('decisions.meeting', 'Decisions')} count={decisions.filter((d) => d.mdc_instance_id === meetingId).length}
          open={openDecisions} onToggle={() => setOpenDecisions(!openDecisions)}
          onAdd={() => setShowAddDecision(!showAddDecision)} addLabel={t('decisions.add', '+ Decision')} />
        <Collapse in={openDecisions}>
          <div>
            {/* Inline create form */}
            <Collapse in={showAddDecision}>
              <div>
                <Card className="border-top-0 rounded-0 rounded-bottom">
                  <Card.Body className="py-2">
                    <Form onSubmit={handleCreateDecision}>
                      {createDecisionMutation.isError && (
                        <Alert variant="danger" className="py-1 small">
                          {((createDecisionMutation.error as any)?.response?.data?.error?.message) || t('common.error', 'Error')}
                        </Alert>
                      )}
                      <Row className="g-2 align-items-end">
                        <Col sm={3}>
                          <Form.Control name="title" placeholder={t('common.title', 'Decision title')} required size="sm" />
                        </Col>
                        <Col sm={3}>
                          <Form.Control name="body" placeholder={t('decisions.body', 'Content')} size="sm" />
                        </Col>
                        <Col sm={2}>
                          <Form.Control name="context" placeholder={t('decisions.contextPlaceholder', 'Background, trigger, or scope')} size="sm" />
                        </Col>
                        <Col sm={2}>
                          <Form.Control name="reason" placeholder={t('decisions.reasonPlaceholder', 'Rationale or trade-off')} size="sm" />
                        </Col>
                        <Col sm={2} className="d-flex gap-1">
                          <Button type="submit" size="sm" variant="primary" disabled={createDecisionMutation.isPending} className="flex-grow-1">
                            {t('common.create', 'Add')}
                          </Button>
                          <Button size="sm" variant="outline-secondary" onClick={() => setShowAddDecision(false)}>&times;</Button>
                        </Col>
                      </Row>
                    </Form>
                  </Card.Body>
                </Card>
              </div>
            </Collapse>

            {loadingDecisions ? (
              <div className="text-center p-3"><Spinner animation="border" size="sm" /></div>
            ) : decisions.length === 0 && !showAddDecision ? (
              <p className="text-muted small px-3 pt-2 mb-0">{t('decisions.no_decisions', 'No decisions yet.')}</p>
            ) : decisions.length > 0 && (
              <div className="border border-top-0 rounded-bottom">
                {decisionEditError && (
                  <Alert variant="danger" className="m-2 py-1 px-2 small mb-0">
                    {decisionEditError}
                  </Alert>
                )}
                <Table responsive size="sm" className="mb-0">
                  <thead>
                    <tr>
                      <th style={{ width: '140px' }}>{t('common.id', 'ID')}</th>
                      <th>{t('common.title', 'Title')}</th>
                      <th style={{ width: '120px' }}>{t('common.createdBy', 'Created by')}</th>
                      <th style={{ width: '180px' }}>{t('meetings.meeting', 'Meeting')}</th>
                      <th style={{ width: '100px' }}>{t('meetings.occurrence', 'Occurrence')}</th>
                      <th style={{ width: '80px' }}>{t('decisions.status', 'Status')}</th>
                      <th style={{ width: '160px' }}>{t('common.date', 'Date')}</th>
                      {canEdit && <th style={{ width: '50px' }}></th>}
                    </tr>
                  </thead>
                  <tbody>
                    {sortedDecisions.map((d) => (
                        <tr key={d.mdc_id}>
                          <td className="small fw-semibold">{formatDecisionRef(d)}</td>
                          <td>
                            <strong className="small">{d.mdc_title}</strong>
                            {d.mdc_body && <div className="text-muted" style={{ fontSize: '0.75rem' }}>{d.mdc_body.substring(0, 80)}{d.mdc_body.length > 80 ? '...' : ''}</div>}
                            {d.mdc_context && <div className="text-muted" style={{ fontSize: '0.75rem' }}><strong>{t('decisions.context', 'Context')}:</strong> {d.mdc_context.substring(0, 80)}{d.mdc_context.length > 80 ? '...' : ''}</div>}
                            {d.mdc_reason && <div className="text-muted" style={{ fontSize: '0.75rem' }}><strong>{t('decisions.reason', 'Why')}:</strong> {d.mdc_reason.substring(0, 80)}{d.mdc_reason.length > 80 ? '...' : ''}</div>}
                          </td>
                          <td className="small">{d.creator_name || '-'}</td>
                          <td className="small">{`#${d.mdc_meeting_id || d.mdc_instance_id || meeting.min_id}`}</td>
                          <td className="small">{d.occurrence_date || '-'}</td>
                          <td><Badge bg={statusColors[d.mdc_status] || 'secondary'} style={{ fontSize: '0.7rem' }}>{d.mdc_status}</Badge></td>
                          <td className="small">{formatTimestampNoSeconds(d.mdc_created_at)}</td>
                          {canEdit && (
                            <td>
                              {canEditDecision(d) && (
                                <Button variant="link" size="sm" className="p-0" onClick={() => startEditDecision(d)}>{t('common.edit', 'Edit')}</Button>
                              )}
                            </td>
                          )}
                        </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}
          </div>
        </Collapse>
      </div>

      {/* ── Actions Section ── */}
      <div className="mb-3">
        <SectionHeader title={t('meetings.actions', 'Actions')} count={actions.filter((a) => a.act_meeting_inst_id === meetingId).length}
          open={openActions} onToggle={() => setOpenActions(!openActions)}
          onAdd={() => {
            const preferredOwnerId = allParticipants.some((p) => p.mpa_user_id === Number(user?.id))
              ? String(user?.id || '')
              : String(allParticipants[0]?.mpa_user_id || user?.id || '')
            setShowAddAction(!showAddAction)
            setActionForm({
              title: '',
              description: '',
              owner_id: preferredOwnerId,
              deadline: addChinaDaysISO(7),
            })
          }}
          addLabel={t('actions.new', '+ Action')} />
        <Collapse in={openActions}>
          <div>
            {/* Inline create form */}
            <Collapse in={showAddAction}>
              <div>
                <Card className="border-top-0 rounded-0 rounded-bottom">
                  <Card.Body className="py-2">
                    <Form onSubmit={handleCreateAction}>
                      {createActionMutation.isError && (
                        <Alert variant="danger" className="py-1 small">
                          {((createActionMutation.error as any)?.response?.data?.error?.message) || t('common.error', 'Error')}
                        </Alert>
                      )}
                      <Row className="g-2 align-items-end">
                        <Col sm={3}>
                          <Form.Control size="sm" placeholder={t('action.title', 'Action title')}
                            value={actionForm.title} onChange={(e) => setActionForm({ ...actionForm, title: e.target.value })} required />
                        </Col>
                        <Col sm={3}>
                          <Form.Control size="sm" placeholder={t('common.description', 'Description')}
                            value={actionForm.description} onChange={(e) => setActionForm({ ...actionForm, description: e.target.value })} />
                        </Col>
                        <Col sm={2}>
                          <Form.Select size="sm" value={actionForm.owner_id}
                            onChange={(e) => setActionForm({ ...actionForm, owner_id: e.target.value })}>
                            <option value="">{t('meetings.actionOwner', 'Lead (primary assignee)')}</option>
                            {allParticipants.length > 0
                              ? allParticipants.map((p) => <option key={p.mpa_user_id} value={p.mpa_user_id}>{p.usr_display_name}</option>)
                              : users.map((u) => <option key={u.usr_id} value={u.usr_id}>{u.usr_display_name}</option>)
                            }
                          </Form.Select>
                        </Col>
                        <Col sm={2}>
                          <Form.Control type="date" size="sm" value={actionForm.deadline}
                            onChange={(e) => setActionForm({ ...actionForm, deadline: e.target.value })} />
                        </Col>
                        <Col sm={2} className="d-flex gap-1">
                          <Button type="submit" size="sm" variant="primary" disabled={createActionMutation.isPending} className="flex-grow-1">
                            {t('common.create', 'Add')}
                          </Button>
                          <Button size="sm" variant="outline-secondary" onClick={() => setShowAddAction(false)}>&times;</Button>
                        </Col>
                      </Row>
                    </Form>
                  </Card.Body>
                </Card>
              </div>
            </Collapse>

            {actions.length === 0 && !showAddAction ? (
              <p className="text-muted small px-3 pt-2 mb-0">{t('common.no_actions', 'No actions yet.')}</p>
            ) : actions.length > 0 && (
              <div className="border border-top-0 rounded-bottom">
                <Table responsive size="sm" className="mb-0" style={{ tableLayout: 'fixed' }}>
                  <colgroup>
                    <col style={{ width: '130px' }} />
                    <col />
                    <col style={{ width: '110px' }} />
                    <col style={{ width: '130px' }} />
                    <col style={{ width: '100px' }} />
                    <col style={{ width: '90px' }} />
                    {canEdit && <col style={{ width: '50px' }} />}
                  </colgroup>
                  <thead>
                    <tr>
                      <th>{t('common.id', 'ID')}</th>
                      <th>{t('action.title', 'Title')}</th>
                      <th>{t('meetings.ownerShort', 'Lead')}</th>
                      <th>{t('action.progress', 'Progress')}</th>
                      <th>{t('common.deadline', 'Deadline')}</th>
                      <th>{t('common.status', 'Status')}</th>
                      {canEdit && <th></th>}
                    </tr>
                  </thead>
                  <tbody>
                    {sortedActions.map((action) => {
                      const fb = currentFollowUpByActionId.get(action.act_id) || previousFollowUpByActionId.get(action.act_id)
                      const currentCmt = currentCommentByActionId.get(action.act_id)
                      const editableCmt =
                        currentCmt && Number(currentCmt.cmt_created_by || 0) === Number(user?.id || 0) ? currentCmt : undefined
                      const histCmt = historicalCommentByActionId.get(action.act_id)
                      const histFb = historicalFollowUpByActionId.get(action.act_id)
                      const draftValue = commentDrafts[action.act_id] ?? editableCmt?.body ?? ''
                      const saveStatus = saveStatusById[action.act_id]
                      const isOverdue =
                        action.act_deadline &&
                        action.act_deadline < currentChinaDateISO() &&
                        !['Done', 'Cancelled'].includes(action.act_status)
                      const histOccurrence = prevOccurrences[histNavOffset]
                      return (
                        <Fragment key={action.act_id}>
                          {/* ── Main action row ── */}
                          <tr style={{ borderTop: '2px solid #dee2e6' }}>
                            <td className="small fw-semibold align-middle">{formatActionRef(action)}</td>
                            <td className="align-middle">
                              <Link to={`/actions/${action.act_id}`} className="small fw-semibold">{action.act_title}</Link>
                              {action.act_desc && (
                                <div className="text-muted" style={{ fontSize: '0.72rem', whiteSpace: 'normal' }}>
                                  {action.act_desc.length > 120 ? `${action.act_desc.slice(0, 120)}…` : action.act_desc}
                                </div>
                              )}
                            </td>
                            <td className="small align-middle">{action.lead_name || '-'}</td>
                            <td className="align-middle">
                              {fb ? (
                                <div className="d-flex align-items-center gap-1">
                                  <ProgressBar
                                    now={fb.afb_completion_pct ?? 0}
                                    variant={FEEDBACK_COLORS[fb.afb_status || ''] || 'info'}
                                    style={{ height: 12, minWidth: 40 }}
                                    className="flex-grow-1"
                                  />
                                  <span style={{ fontSize: '0.65rem' }}>{fb.afb_completion_pct ?? 0}%</span>
                                </div>
                              ) : (
                                <span className="text-muted" style={{ fontSize: '0.7rem' }}>—</span>
                              )}
                            </td>
                            <td className="small align-middle">
                              <span className={isOverdue ? 'text-danger fw-semibold' : ''}>
                                {action.act_deadline ? action.act_deadline.slice(0, 10) : '—'}
                              </span>
                            </td>
                            <td className="align-middle">
                              <Badge bg="secondary" style={{ fontSize: '0.7rem' }}>{action.act_status}</Badge>
                            </td>
                            {canEdit && (
                              <td className="align-middle">
                                <Button variant="link" size="sm" className="p-0" onClick={() => startEditAction(action)}>{t('common.edit', 'Edit')}</Button>
                              </td>
                            )}
                          </tr>

                          {/* ── Feedback from lead row ── */}
                          <tr style={{ backgroundColor: '#f8f9fa' }}>
                            <td colSpan={canEdit ? 7 : 6} className="py-1 px-3" style={{ borderTop: 'none' }}>
                              <div className="d-flex align-items-center gap-2" style={{ fontSize: '0.75rem', flexWrap: 'wrap' }}>
                                <span className="text-muted fw-semibold">{t('meetings.feedbackLead', 'Lead feedback')}:</span>
                                {fb ? (
                                  <>
                                    <Badge bg={FEEDBACK_COLORS[fb.afb_status || ''] || 'secondary'} style={{ fontSize: '0.65rem' }}>
                                      {FEEDBACK_LABELS[fb.afb_status || ''] || fb.afb_status}
                                    </Badge>
                                    <span>{fb.afb_completion_pct ?? 0}%</span>
                                    {fb.afb_comment && <span className="text-muted">{fb.afb_comment}</span>}
                                    {fb.afb_blockers && <span className="text-danger">⚠ {fb.afb_blockers}</span>}
                                    <span className="text-muted ms-auto" style={{ fontSize: '0.7rem' }}>
                                      {fb.usr_display_name}
                                      {fb.afb_created_at ? ` · ${formatTimestampNoSeconds(fb.afb_created_at)}` : ''}
                                    </span>
                                  </>
                                ) : (
                                  <span className="text-muted">{t('meetings.noFeedback', 'No lead feedback yet.')}</span>
                                )}
                              </div>
                            </td>
                          </tr>

                          {/* ── Comment row ── */}
                          <tr style={{ backgroundColor: '#eef2f7' }}>
                            <td colSpan={canEdit ? 7 : 6} className="py-2 px-3" style={{ borderTop: 'none' }}>
                              <Row className="g-2">
                                {/* Left: current meeting update (auto-save) */}
                                <Col xs={6}>
                                  <div className="d-flex justify-content-between align-items-center mb-1">
                                    <span className="fw-semibold text-primary" style={{ fontSize: '0.75rem' }}>
                                      {t('meetings.currentMeetingUpdate', 'Current meeting')}
                                    </span>
                                    {saveStatus === 'saving' && (
                                      <span className="text-muted" style={{ fontSize: '0.68rem' }}>saving…</span>
                                    )}
                                    {saveStatus === 'saved' && (
                                      <span className="text-success" style={{ fontSize: '0.68rem' }}>✓ {t('meetings.autoSaved', 'saved')}</span>
                                    )}
                                    {(createCommentMutation.isError || editCommentMutation.isError) && !saveStatus && (
                                      <span className="text-danger" style={{ fontSize: '0.68rem' }}>
                                        {((editCommentMutation.error as any)?.response?.data?.error?.message)
                                          || ((createCommentMutation.error as any)?.response?.data?.error?.message)
                                          || t('common.error', 'Error')}
                                      </span>
                                    )}
                                  </div>
                                  <Form.Control
                                    as="textarea"
                                    rows={2}
                                    size="sm"
                                    style={{ fontSize: '0.8rem', resize: 'vertical' }}
                                    placeholder={t('meetings.addComment', 'Add a comment for this meeting...')}
                                    value={draftValue}
                                    onChange={(e) => handleCommentChange(action.act_id, e.target.value)}
                                  />
                                  {editableCmt && (
                                    <div className="text-muted mt-1" style={{ fontSize: '0.68rem' }}>
                                      {editableCmt.author}{editableCmt.cmt_created_at ? ` · ${formatTimestampNoSeconds(editableCmt.cmt_created_at)}` : ''}
                                    </div>
                                  )}
                                </Col>

                                {/* Right: previous meeting history with navigation */}
                                <Col xs={6}>
                                  <div className="d-flex justify-content-between align-items-center mb-1">
                                    <span className="fw-semibold text-muted" style={{ fontSize: '0.75rem' }}>
                                      {histNavOffset === 0
                                        ? t('meetings.previousMeetingUpdate', 'Previous meeting')
                                        : `${histNavOffset + 1} ${t('meetings.meetingsAgo', 'meetings ago')}`}
                                      {histOccurrence && (
                                        <span className="fw-normal ms-1" style={{ fontSize: '0.68rem' }}>
                                          ({formatTimestampNoSeconds(histOccurrence.min_created_at || histOccurrence.min_date)})
                                        </span>
                                      )}
                                    </span>
                                    <div className="d-flex gap-1">
                                      {histNavOffset > 0 && (
                                        <Button
                                          size="sm"
                                          variant="link"
                                          className="p-0 text-primary"
                                          style={{ fontSize: '0.7rem' }}
                                          onClick={() => setHistNavOffset((prev) => prev - 1)}
                                        >
                                          {t('meetings.newerBtn', '← Newer')}
                                        </Button>
                                      )}
                                      {histNavOffset < prevOccurrences.length - 1 && (
                                        <Button
                                          size="sm"
                                          variant="link"
                                          className="p-0 text-secondary"
                                          style={{ fontSize: '0.7rem' }}
                                          onClick={() => setHistNavOffset((prev) => prev + 1)}
                                        >
                                          {t('meetings.olderBtn', 'Older →')}
                                        </Button>
                                      )}
                                    </div>
                                  </div>
                                  {histFb && (
                                    <div className="d-flex align-items-center gap-2 mb-1 small border rounded px-2 py-1 bg-white">
                                      <Badge bg={FEEDBACK_COLORS[histFb.afb_status || ''] || 'secondary'} style={{ fontSize: '0.65rem' }}>
                                        {FEEDBACK_LABELS[histFb.afb_status || ''] || histFb.afb_status}
                                      </Badge>
                                      <span>{histFb.afb_completion_pct ?? 0}%</span>
                                      {histFb.afb_comment && <span className="text-muted">{histFb.afb_comment}</span>}
                                      {histFb.afb_blockers && <span className="text-danger">⚠ {histFb.afb_blockers}</span>}
                                    </div>
                                  )}
                                  {histCmt ? (
                                    <div className="border rounded px-2 py-1 bg-white" style={{ fontSize: '0.8rem', minHeight: '2.5rem' }}>
                                      <div style={{ whiteSpace: 'pre-wrap' }}>{histCmt.body}</div>
                                      <div className="text-muted mt-1" style={{ fontSize: '0.68rem' }}>
                                        {histCmt.author || '-'}
                                        {histCmt.cmt_created_at ? ` · ${formatTimestampNoSeconds(histCmt.cmt_created_at)}` : ''}
                                      </div>
                                    </div>
                                  ) : (
                                    <div className="border rounded px-2 py-1" style={{ fontSize: '0.75rem', minHeight: '2.5rem' }}>
                                      <span className="text-muted">{t('meetings.noPrevUpdate', 'No update from this meeting.')}</span>
                                    </div>
                                  )}
                                </Col>
                              </Row>
                            </td>
                          </tr>
                        </Fragment>
                      )
                    })}
                  </tbody>
                </Table>
              </div>
            )}
          </div>
        </Collapse>
      </div>

      {/* ── Memo Modal ── */}
      <Modal show={showAddMemo} onHide={() => { setShowAddMemo(false); setEditingMemo(null) }}>
        <Modal.Header closeButton>
          <Modal.Title>{editingMemo ? t('common.edit', 'Edit Memo') : t('meetings.add_memo', 'Add Memo')}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleMemoSubmit}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>{t('meetings.memo_content', 'Content')}</Form.Label>
              <Form.Control value={memoForm.body} onChange={(e) => setMemoForm({ ...memoForm, body: e.target.value })} as="textarea" rows={5} />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => { setShowAddMemo(false); setEditingMemo(null) }}>{t('common.cancel', 'Cancel')}</Button>
            <Button variant="primary" type="submit">{editingMemo ? t('common.save', 'Save') : t('common.create', 'Create')}</Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* ── Edit Meeting Modal ── */}
      <Modal show={showEditMeeting} onHide={() => setShowEditMeeting(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{t('common.edit', 'Edit Meeting')}</Modal.Title>
        </Modal.Header>
        <Form onSubmit={(e) => {
          e.preventDefault()
          meetingEditMutation.mutate({
            title: meetingForm.title.trim() || undefined,
            category_id: meetingForm.category_id ? Number(meetingForm.category_id) : undefined,
            secondary_category_id: meetingForm.secondary_category_id ? Number(meetingForm.secondary_category_id) : undefined,
            status: meetingForm.status, periodicity: meetingForm.periodicity || null,
            target: meetingForm.target || null,
            compulsory_participant_ids: meetingForm.compulsory_participant_ids,
            optional_participant_ids: meetingForm.optional_participant_ids,
          })
        }}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>{t('meeting.title', 'Title')}</Form.Label>
              <Form.Control value={meetingForm.title} onChange={(e) => setMeetingForm({ ...meetingForm, title: e.target.value })} />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>{t('common.category', 'Category')}</Form.Label>
              <Form.Select value={meetingForm.category_id} onChange={(e) => setMeetingForm({ ...meetingForm, category_id: e.target.value })}>
                <option value="">{t('common.none', 'None')}</option>
                {decisionTopics.map((topic) => <option key={topic.top_id} value={topic.top_id}>{topic.top_name}</option>)}
              </Form.Select>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>{t('common.status', 'Status')}</Form.Label>
              <Form.Select value={meetingForm.status} onChange={(e) => setMeetingForm({ ...meetingForm, status: e.target.value })}>
                <option value="Active">Active</option>
                <option value="Closed">Closed</option>
              </Form.Select>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>{t('meetings.compulsoryParticipants', 'Compulsory participants')}</Form.Label>
              <div className="border rounded p-2" style={{ maxHeight: 180, overflowY: 'auto' }}>
                {allowedParticipantOptions.map((option) => {
                  const isCreatorOption = option.usr_id === creatorUserId
                  const checked = isCreatorOption || meetingForm.compulsory_participant_ids.includes(option.usr_id)
                  const displayLabel = isCreatorOption
                    ? (<span style={{ color: '#0d6efd', textDecoration: 'underline', fontWeight: 600 }}>{option.usr_display_name} ({t('meetings.creatorLabel', 'Meeting creator')})</span>)
                    : option.usr_display_name
                  return (
                    <Form.Check
                      key={`compulsory-${option.usr_id}`}
                      id={`compulsory-${option.usr_id}`}
                      type="checkbox"
                      label={displayLabel}
                      checked={checked}
                      disabled={isCreatorOption}
                      onChange={(event) => {
                        setMeetingForm((current) => {
                          if (event.target.checked) {
                            return {
                              ...current,
                              compulsory_participant_ids: [...current.compulsory_participant_ids, option.usr_id],
                              optional_participant_ids: current.optional_participant_ids.filter((id) => id !== option.usr_id),
                            }
                          }
                          return {
                            ...current,
                            compulsory_participant_ids: current.compulsory_participant_ids.filter((id) => id !== option.usr_id),
                          }
                        })
                      }}
                      className="mb-1"
                    />
                  )
                })}
              </div>
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>{t('meetings.optionalParticipants', 'Optional participants')}</Form.Label>
              <div className="border rounded p-2" style={{ maxHeight: 180, overflowY: 'auto' }}>
                {allowedParticipantOptions.map((option) => {
                  const isCreatorOption = option.usr_id === creatorUserId
                  const checked = !isCreatorOption && meetingForm.optional_participant_ids.includes(option.usr_id)
                  const displayLabel = isCreatorOption
                    ? (<span style={{ color: '#0d6efd', textDecoration: 'underline', fontWeight: 600 }}>{option.usr_display_name} ({t('meetings.creatorLabel', 'Meeting creator')})</span>)
                    : option.usr_display_name
                  return (
                    <Form.Check
                      key={`optional-${option.usr_id}`}
                      id={`optional-${option.usr_id}`}
                      type="checkbox"
                      label={displayLabel}
                      checked={checked}
                      disabled={isCreatorOption}
                      onChange={(event) => {
                        setMeetingForm((current) => {
                          if (event.target.checked) {
                            return {
                              ...current,
                              optional_participant_ids: [
                                ...current.optional_participant_ids.filter((id) => id !== option.usr_id),
                                option.usr_id,
                              ],
                              compulsory_participant_ids: current.compulsory_participant_ids.filter((id) => id !== option.usr_id),
                            }
                          }
                          return {
                            ...current,
                            optional_participant_ids: current.optional_participant_ids.filter((id) => id !== option.usr_id),
                          }
                        })
                      }}
                      className="mb-1"
                    />
                  )
                })}
              </div>
              {meeting?.min_meeting_id ? (
                <Form.Text className="text-muted">
                  {t('meetings.seriesOccurrenceParticipantHint', 'This meeting inherits participants from the series. Remove users here to mark no attendance for this occurrence, or re-add inherited users as needed.')}
                </Form.Text>
              ) : (
                <Form.Text className="text-muted">
                  {t('meetings.standaloneParticipantHint', 'Select participants for this standalone meeting.')}
                </Form.Text>
              )}
            </Form.Group>
            {meetingEditMutation.isError && (
              <Alert variant="danger" className="mb-0">
                {((meetingEditMutation.error as any)?.response?.data?.error?.message) || t('common.error', 'Error')}
              </Alert>
            )}
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowEditMeeting(false)}>{t('common.cancel', 'Cancel')}</Button>
            <Button variant="primary" type="submit">{t('common.save', 'Save')}</Button>
          </Modal.Footer>
        </Form>
      </Modal>

      {/* ── Action Edit Modal ── */}
      <Modal show={!!editingAction} onHide={() => { setEditingAction(null); setActionEditError(null) }}>
        <Modal.Header closeButton>
          <Modal.Title>{t('action.edit', 'Edit Action')}{editingAction ? ` — ${formatActionRef(editingAction)}` : ''}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {actionEditError && <Alert variant="danger" className="py-1 small">{actionEditError}</Alert>}
          <Form.Group className="mb-3">
            <Form.Label>{t('action.title', 'Title')}</Form.Label>
            <Form.Control value={actionEditForm.title} onChange={(e) => setActionEditForm({ ...actionEditForm, title: e.target.value })} />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>{t('common.description', 'Description')}</Form.Label>
            <Form.Control as="textarea" rows={3} value={actionEditForm.description}
              onChange={(e) => setActionEditForm({ ...actionEditForm, description: e.target.value })} />
          </Form.Group>
          <Row className="g-2">
            <Col sm={6}>
              <Form.Group className="mb-3">
                <Form.Label>{t('common.status', 'Status')}</Form.Label>
                <Form.Select value={actionEditForm.status} onChange={(e) => setActionEditForm({ ...actionEditForm, status: e.target.value })}>
                  <option value="Open">Open</option>
                  <option value="In Progress">In Progress</option>
                  <option value="On Hold">On Hold</option>
                  <option value="Done">Done</option>
                  <option value="Cancelled">Cancelled</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col sm={6}>
              <Form.Group className="mb-3">
                <Form.Label>{t('common.deadline', 'Deadline')}</Form.Label>
                <Form.Control type="date" value={actionEditForm.deadline}
                  onChange={(e) => setActionEditForm({ ...actionEditForm, deadline: e.target.value })} />
              </Form.Group>
            </Col>
          </Row>
          {actionEditForm.status === 'On Hold' && (
            <Form.Group className="mb-3">
              <Form.Label>{t('action.holdReason', 'Hold reason')}</Form.Label>
              <Form.Control value={actionEditForm.hold_reason}
                onChange={(e) => setActionEditForm({ ...actionEditForm, hold_reason: e.target.value })}
                placeholder={t('action.holdReasonPlaceholder', 'Why is this action on hold?')} required />
            </Form.Group>
          )}
          {actionEditForm.status === 'Cancelled' && (
            <Form.Group className="mb-3">
              <Form.Label>{t('action.cancelReason', 'Cancel reason')}</Form.Label>
              <Form.Control value={actionEditForm.cancel_reason}
                onChange={(e) => setActionEditForm({ ...actionEditForm, cancel_reason: e.target.value })}
                placeholder={t('action.cancelReasonPlaceholder', 'Why is this action cancelled?')} required />
            </Form.Group>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => { setEditingAction(null); setActionEditError(null) }}>{t('common.cancel', 'Cancel')}</Button>
          <Button variant="primary" onClick={handleActionEditSave} disabled={updateActionMutation.isPending}>{t('common.save', 'Save')}</Button>
        </Modal.Footer>
      </Modal>

      {/* ── Decision Edit Modal ── */}
      <Modal show={!!editingDecision} onHide={() => { setEditingDecision(null); setEditingDecisionId(null); setDecisionEditError(null) }}>
        <Modal.Header closeButton>
          <Modal.Title>{t('decisions.edit', 'Edit Decision')}{editingDecision ? ` — ${formatDecisionRef(editingDecision)}` : ''}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {decisionEditError && <Alert variant="danger" className="py-1 small">{decisionEditError}</Alert>}
          <Form.Group className="mb-3">
            <Form.Label>{t('common.title', 'Title')}</Form.Label>
            <Form.Control value={decisionModalForm.title} onChange={(e) => setDecisionModalForm({ ...decisionModalForm, title: e.target.value })} />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>{t('decisions.body', 'Content')}</Form.Label>
            <Form.Control as="textarea" rows={3} value={decisionModalForm.body}
              onChange={(e) => setDecisionModalForm({ ...decisionModalForm, body: e.target.value })} />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>{t('decisions.context', 'Context')}</Form.Label>
            <Form.Control as="textarea" rows={2} value={decisionModalForm.context}
              onChange={(e) => setDecisionModalForm({ ...decisionModalForm, context: e.target.value })}
              placeholder={t('decisions.contextPlaceholder', 'Background, trigger, or scope')} />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>{t('decisions.reason', 'Reason')}</Form.Label>
            <Form.Control as="textarea" rows={2} value={decisionModalForm.reason}
              onChange={(e) => setDecisionModalForm({ ...decisionModalForm, reason: e.target.value })}
              placeholder={t('decisions.reasonPlaceholder', 'Rationale or trade-off')} />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>{t('decisions.status', 'Status')}</Form.Label>
            <Form.Select value={decisionModalForm.status} onChange={(e) => setDecisionModalForm({ ...decisionModalForm, status: e.target.value })}>
              <option value="Published">Published</option>
              <option value="Expired">Expired</option>
            </Form.Select>
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => { setEditingDecision(null); setEditingDecisionId(null); setDecisionEditError(null) }}>{t('common.cancel', 'Cancel')}</Button>
          <Button variant="primary" onClick={handleDecisionModalSave} disabled={updateDecisionMutation.isPending}>{t('common.save', 'Save')}</Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
