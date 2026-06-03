import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Table, Form, Button, Card, Badge, Row, Col, Spinner, Modal, Alert } from 'react-bootstrap';
import { t } from '../../lib/i18n';
import api from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';
import { formatChinaDateTimeNoSeconds } from '../../lib/dateTime';
import StatusBadge from '../../components/shared/StatusBadge';

interface TopicOption {
  top_id: number;
  top_name: string;
}

interface SeriesOption {
  mtg_id: number;
  mtg_title: string;
}

interface UserOption {
  usr_id: number;
  usr_display_name: string;
}

interface Revision {
  mdr_id: number;
  mdr_decision_id: number;
  mdr_title: string;
  mdr_body: string;
  mdr_updated_by?: number | null;
  mdr_updated_at: string;
  updated_by_name: string;
}

interface Decision {
  mdc_id: number;
  mdc_title: string;
  mdc_body: string;
  mdc_context?: string | null;
  mdc_reason?: string | null;
  mdc_tags?: string | null;
  mdc_status: string;
  mdc_meeting_id?: number;
  meeting_title?: string;
  series_title?: string;
  creator_name?: string;
  mdc_created_by?: number;
  mdc_category_id?: number;
  category_name?: string;
  mdc_secondary_category_id?: number;
  secondary_category_name?: string;
  can_manage?: boolean;
  mdc_created_at: string;
  mdc_updated_at?: string | null;
  mdc_expires_at?: string | null;
  mdc_status_changed_at?: string | null;
  revision_count?: number;
  last_revised_at?: string | null;
}

const statusColors: Record<string, string> = {
  Published: 'primary',
  Expired: 'secondary',
};

function inferYear(value?: string | null): number {
  const parsed = value ? new Date(value) : null
  if (parsed && !Number.isNaN(parsed.getTime())) {
    return parsed.getFullYear()
  }
  return new Date().getFullYear()
}

function formatDecisionRef(decision: Decision): string {
  return `DEC-${inferYear(decision.mdc_created_at)}-${String(decision.mdc_id).padStart(5, '0')}`
}

function formatSeriesRef(seriesId?: number | null, createdAt?: string | null): string {
  if (!seriesId) return '-'
  return `SER-${inferYear(createdAt)}-${String(seriesId).padStart(6, '0')}`
}

function formatTags(tags?: string | null): string {
  return String(tags || '')
    .split(',')
    .map((tag) => tag.trim().replace(/^#+/, ''))
    .filter(Boolean)
    .map((tag) => `#${tag.toUpperCase()}`)
    .join(', ') || '-'
}

function formatTimestampNoSeconds(value?: string | null): string {
  return formatChinaDateTimeNoSeconds(value)
}

const fetchDecisions = async (params: { search?: string; status?: string; category_id?: number; series_id?: number; owner_id?: number; limit?: number; offset?: number }) => {
  const response = await api.get('/api/decisions/', { params });
  return response.data;
};

const fetchCounts = async () => {
  const response = await api.get('/api/decisions/counts');
  return response.data;
};

const DecisionsList: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === 'Admin';
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('Published');
  const [categoryFilter, setCategoryFilter] = useState<number | ''>('');
  const [seriesFilter, setSeriesFilter] = useState<number | ''>('');
  const [ownerFilter, setOwnerFilter] = useState<number | ''>('');
  const [page, setPage] = useState(0);
  const [editingDecision, setEditingDecision] = useState<Decision | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editTags, setEditTags] = useState('');
  const [revisionDecision, setRevisionDecision] = useState<Decision | null>(null);
  const limit = 20;

  const { data: categories = [] } = useQuery<TopicOption[]>({
    queryKey: ['topics'],
    queryFn: async () => {
      const response = await api.get('/api/topics');
      return response.data.data || [];
    },
  });

  const { data: seriesList = [] } = useQuery<SeriesOption[]>({
    queryKey: ['meetings', 'series'],
    queryFn: async () => {
      const response = await api.get('/api/meetings/series');
      return response.data.data || [];
    },
  });

  const { data: users = [] } = useQuery<UserOption[]>({
    queryKey: ['users', 'decision-owners'],
    queryFn: async () => {
      const response = await api.get('/api/users');
      return response.data.data || [];
    },
  });

  const { data: decisionsPayload, isLoading, refetch } = useQuery({
    queryKey: ['decisions', searchQuery, statusFilter, categoryFilter, seriesFilter, ownerFilter, page],
    queryFn: () => fetchDecisions({
      search: searchQuery,
      status: statusFilter || undefined,
      category_id: categoryFilter || undefined,
      series_id: seriesFilter || undefined,
      owner_id: ownerFilter || undefined,
      limit,
      offset: page * limit,
    }),
  });

  const decisions: Decision[] = decisionsPayload?.data || [];
  const pagination = decisionsPayload?.pagination;
  const { data: counts = {} } = useQuery({
    queryKey: ['decisions', 'counts'],
    queryFn: fetchCounts,
  });

  const { data: revisionsData, isLoading: revisionsLoading } = useQuery<Revision[]>({
    queryKey: ['decisions', 'revisions', revisionDecision?.mdc_id],
    queryFn: async () => {
      const res = await api.get(`/api/decisions/${revisionDecision!.mdc_id}/revisions`);
      return res.data.data || [];
    },
    enabled: !!revisionDecision,
  });

  const expireMutation = useMutation({
    mutationFn: (decisionId: number) => api.patch(`/api/decisions/${decisionId}/status`, { status: 'Expired' }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['decisions'] });
      await queryClient.invalidateQueries({ queryKey: ['decisions', 'counts'] });
    },
  });

  const editMutation = useMutation({
    mutationFn: async ({ decisionId, title, body, tags }: { decisionId: number; title: string; body: string; tags: string }) => {
      return api.patch(`/api/decisions/${decisionId}`, { title, body, tags })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['decisions'] });
      await queryClient.invalidateQueries({ queryKey: ['dashboard', 'decisions'] });
      setEditingDecision(null)
      setEditTitle('')
      setEditBody('')
      setEditTags('')
    },
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    refetch();
  };

  const handleMarkExpired = (decisionId: number) => {
    expireMutation.mutate(decisionId);
  };

  const openEditModal = (decision: Decision) => {
    setEditingDecision(decision)
    setEditTitle(decision.mdc_title || '')
    setEditBody(decision.mdc_body || '')
    setEditTags(decision.mdc_tags || '')
  }

  const saveDecisionEdit = () => {
    if (!editingDecision) return
    editMutation.mutate({
      decisionId: editingDecision.mdc_id,
      title: editTitle.trim(),
      body: editBody,
      tags: editTags.trim(),
    })
  }

  const totalCount = Object.values(counts).reduce((a: any, b: any) => a + b, 0) as number;

  return (
    <div>
      <h2 className="mb-4">{t('decisions.title', 'Decisions')}</h2>


      <Card className="mb-4">
        <Card.Body className="py-2">
          <Form onSubmit={handleSearch}>
            <Row className="g-2 align-items-end">
              <Col md={4}>
                <Form.Control
                  size="sm"
                  type="text"
                  placeholder={t('decisions.search', 'Search decisions...')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </Col>
              <Col md={2}>
                <Form.Select size="sm"
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
                >
                  <option value="">{t('common.allStatuses', 'All Statuses')}</option>
                  <option value="Published">{t('decisions.status_published', 'Published')}</option>
                  <option value="Expired">{t('decisions.status_expired', 'Expired')}</option>
                </Form.Select>
              </Col>
              <Col md={3}>
                <Form.Select size="sm"
                  value={seriesFilter}
                  onChange={(e) => { setSeriesFilter(e.target.value ? Number(e.target.value) : ''); setPage(0); }}
                >
                  <option value="">{t('meetings.allSeries', 'All Series')}</option>
                  {seriesList.map((s) => (
                    <option key={s.mtg_id} value={s.mtg_id}>{`${formatSeriesRef(s.mtg_id)} - ${s.mtg_title}`}</option>
                  ))}
                </Form.Select>
              </Col>
              <Col md={3}>
                <Form.Select size="sm"
                  value={categoryFilter}
                  onChange={(e) => { setCategoryFilter(e.target.value ? Number(e.target.value) : ''); setPage(0); }}
                >
                  <option value="">{t('common.allCategories', 'All Categories')}</option>
                  {categories.map((category) => (
                    <option key={category.top_id} value={category.top_id}>{category.top_name}</option>
                  ))}
                </Form.Select>
              </Col>
              <Col md={3}>
                <Form.Select size="sm"
                  value={ownerFilter}
                  onChange={(e) => { setOwnerFilter(e.target.value ? Number(e.target.value) : ''); setPage(0); }}
                >
                  <option value="">{t('common.allCreatedBy', 'All Created by')}</option>
                  {users.map((entry) => (
                    <option key={entry.usr_id} value={entry.usr_id}>{entry.usr_display_name}</option>
                  ))}
                </Form.Select>
              </Col>

            </Row>
          </Form>
        </Card.Body>
      </Card>

      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center py-2">
          <span className="small fw-bold text-uppercase text-muted">{t('decisions.title', 'Decisions')}</span>
          <Badge bg="secondary">{pagination?.total ?? decisions.length}</Badge>
        </Card.Header>
        <Card.Body className="p-0">
          {isLoading ? (
            <div className="text-center py-5">
              <Spinner animation="border" role="status">
                <span className="visually-hidden">{t('common.loading', 'Loading...')}</span>
              </Spinner>
            </div>
          ) : decisions.length === 0 ? (
            <div className="text-center py-5 text-muted">
              {t('decisions.no_decisions', 'No decisions found.')}
            </div>
          ) : (
            <Table responsive hover size="sm" className="mb-0" style={{ fontSize: '0.875rem' }}>
              <thead className="table-light">
                <tr>
                  <th style={{ width: 140 }}>{t('common.id', 'ID')}</th>
                  <th style={{ width: '40vw' }}>{t('common.title', 'Title')}</th>
                  <th>{t('common.createdBy', 'Created by')}</th>
                  <th>{t('common.tags', 'Tags')}</th>
                  <th>{t('common.category', 'Category')}</th>
                  <th>{t('meetings.meeting', 'Meeting')}</th>
                  <th style={{ width: 90 }}>{t('decisions.status', 'Status')}</th>
                  <th style={{ width: 120 }}>{t('common.createdAt', 'Created')}</th>
                  <th style={{ width: 120 }}>{t('common.updatedAt', 'Updated')}</th>
                  <th style={{ width: 150 }}>{t('decisions.revisions', 'Revisions')}</th>
                  <th style={{ width: 190 }}></th>
                </tr>
              </thead>
              <tbody>
                {decisions.map((decision: Decision) => (
                  <tr key={decision.mdc_id}>
                    <td className="small fw-semibold text-muted">
                      <Link to={`/decisions/${decision.mdc_id}`} className="text-decoration-none">
                        {formatDecisionRef(decision)}
                      </Link>
                    </td>
                    <td>
                      <strong>
                        <Link to={`/decisions/${decision.mdc_id}`} className="text-decoration-none">
                          {decision.mdc_title}
                        </Link>
                      </strong>
                      {decision.mdc_body && (
                        <div className="text-muted small text-truncate" style={{ maxWidth: '400px' }}>{decision.mdc_body}</div>
                      )}
                      {decision.mdc_context && (
                        <div className="text-muted small text-truncate" style={{ maxWidth: '400px' }}>
                          <strong>{t('decisions.context', 'Context')}:</strong> {decision.mdc_context}
                        </div>
                      )}
                      {decision.mdc_reason && (
                        <div className="text-muted small text-truncate" style={{ maxWidth: '400px' }}>
                          <strong>{t('decisions.reason', 'Why')}:</strong> {decision.mdc_reason}
                        </div>
                      )}
                    </td>
                    <td className="small">{decision.creator_name || '-'}</td>
                    <td className="small">{formatTags(decision.mdc_tags)}</td>
                    <td className="small">{decision.category_name || '-'}</td>
                    <td className="small">
                      {decision.series_title || decision.meeting_title || '-'}
                    </td>
                    <td>
                      <StatusBadge status={decision.mdc_status} />
                    </td>
                    <td className="small">{formatTimestampNoSeconds(decision.mdc_created_at)}</td>
                    <td className="small">{formatTimestampNoSeconds(decision.mdc_updated_at)}</td>
                    <td className="small">
                      {(decision.revision_count || 0) > 0 ? (
                        <>
                          <Button
                            variant="link"
                            size="sm"
                            className="p-0 mb-1"
                            onClick={() => setRevisionDecision(decision)}
                          >
                            <Badge bg="info">{t('decisions.revised', 'Revised')} × {decision.revision_count}</Badge>
                          </Button>
                          <div className="text-muted">{formatTimestampNoSeconds(decision.last_revised_at)}</div>
                        </>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td>
                      {decision.can_manage ? (
                        <Button
                          variant="outline-primary"
                          size="sm"
                          className="me-2"
                          onClick={() => openEditModal(decision)}
                        >
                          {t('common.edit', 'Edit')}
                        </Button>
                      ) : (
                        <Button variant="outline-secondary" size="sm" className="me-2" disabled>
                          {t('common.locked', 'Locked')}
                        </Button>
                      )}
                      {isAdmin && decision.mdc_status === 'Published' ? (
                        <Button
                          variant="outline-warning"
                          size="sm"
                          onClick={() => handleMarkExpired(decision.mdc_id)}
                          disabled={expireMutation.isPending}
                        >
                          {t('decisions.mark_expired', 'Expire')}
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>

      {decisions.length > 0 && (
        <div className="d-flex justify-content-between align-items-center mt-3">
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Previous
          </Button>
          <span className="text-muted">Page {page + 1}</span>
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={pagination ? page + 1 >= (pagination.total_pages || 1) : decisions.length < limit}
          >
            Next
          </Button>
        </div>
      )}

      <Modal show={!!revisionDecision} onHide={() => setRevisionDecision(null)} size="xl">
        <Modal.Header closeButton>
          <Modal.Title>
            {t('decisions.revisionHistory', 'Revision History')}:
            {' '}<span className="text-muted fw-normal">{revisionDecision?.mdc_title}</span>
          </Modal.Title>
        </Modal.Header>
        <Modal.Body className="p-0">
          {revisionsLoading ? (
            <div className="text-center py-4">
              <Spinner animation="border" size="sm" />
            </div>
          ) : !revisionsData || revisionsData.length === 0 ? (
            <p className="text-muted text-center py-4 mb-0">{t('decisions.noRevisions', 'No revision history available.')}</p>
          ) : (
            <>
              <div className="px-3 pt-3 pb-2">
                <small className="text-muted">
                  {t('decisions.revisionHint', 'Each row shows the content as it was before that edit was saved (oldest last).')}
                </small>
              </div>
              <Table responsive hover size="sm" className="mb-0">
                <thead className="table-light">
                  <tr>
                    <th style={{ width: 40 }}>#</th>
                    <th style={{ width: 200 }}>{t('common.title', 'Title')}</th>
                    <th>{t('decisions.content', 'Content')}</th>
                    <th style={{ width: 140 }}>{t('decisions.revisedBy', 'Revised By')}</th>
                    <th style={{ width: 120 }}>{t('decisions.revisedAt', 'Revised At')}</th>
                  </tr>
                </thead>
                <tbody>
                  {revisionsData.map((rev, idx) => (
                    <tr key={rev.mdr_id}>
                      <td className="text-muted small">{revisionsData.length - idx}</td>
                      <td className="small fw-semibold">{rev.mdr_title}</td>
                      <td className="small" style={{ whiteSpace: 'pre-wrap', maxWidth: '460px', wordBreak: 'break-word' }}>{rev.mdr_body}</td>
                      <td className="small">{rev.updated_by_name}</td>
                      <td className="small">{formatTimestampNoSeconds(rev.mdr_updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              <div className="px-3 py-2 border-top">
                <small className="text-muted fw-semibold">
                  {t('decisions.currentVersionLabel', 'Current version:')}{' '}{revisionDecision?.mdc_title}
                </small>
                <div className="text-muted small mt-1" style={{ whiteSpace: 'pre-wrap', maxWidth: '700px', wordBreak: 'break-word' }}>
                  {revisionDecision?.mdc_body}
                </div>
              </div>
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setRevisionDecision(null)}>
            {t('common.close', 'Close')}
          </Button>
        </Modal.Footer>
      </Modal>

      <Modal show={!!editingDecision} onHide={() => setEditingDecision(null)}>
        <Modal.Header closeButton>
          <Modal.Title>{t('decisions.editDecision', 'Edit Decision')}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {editMutation.isError && (
            <Alert variant="danger" className="mb-3 py-2">
              {((editMutation.error as any)?.response?.data?.error?.message) || t('common.error', 'Error')}
            </Alert>
          )}
          <Form.Group className="mb-3">
            <Form.Label>{t('common.title', 'Title')}</Form.Label>
            <Form.Control
              value={editTitle}
              onChange={(event) => setEditTitle(event.target.value)}
              maxLength={255}
            />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>{t('decisions.content', 'Content')}</Form.Label>
            <Form.Control
              as="textarea"
              rows={5}
              value={editBody}
              onChange={(event) => setEditBody(event.target.value)}
            />
          </Form.Group>
          <Form.Group>
            <Form.Label>{t('common.tags', 'Tags')}</Form.Label>
            <Form.Control
              value={editTags}
              onChange={(event) => setEditTags(event.target.value)}
              placeholder="tag1, tag2, tag3"
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setEditingDecision(null)}>
            {t('common.cancel', 'Cancel')}
          </Button>
          <Button variant="primary" onClick={saveDecisionEdit} disabled={editMutation.isPending || !editTitle.trim()}>
            {t('common.save', 'Save')}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default DecisionsList;
