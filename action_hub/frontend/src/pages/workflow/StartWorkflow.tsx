
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Form, Button, Card, Alert, Spinner } from 'react-bootstrap';
import api from '../../lib/api';
import { t } from '../../lib/i18n';

export default function StartWorkflow() {
  const navigate = useNavigate();
  const [templateId, setTemplateId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [error, setError] = useState('');

  // Fetch available workflow templates
  const { data: templates, isLoading: loadingTemplates } = useQuery({
    queryKey: ['workflow-templates'],
    queryFn: async () => {
      const res = await api.get('/api/workflow/templates');
      return res.data.data || [];
    },
  });

  // Fetch categories (stored in t_topic for now)
  const { data: topics = [], isLoading: loadingTopics } = useQuery({
    queryKey: ['topics'],
    queryFn: async () => {
      const res = await api.get('/api/topics');
      return res.data.data || [];
    },
  });

  // Mutation to start workflow instance
  const mutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post('/api/workflow/requests', payload);
      return res.data;
    },
    onSuccess: (data) => {
      navigate(`/workflow/instance/${data.instance_id}`);
    },
    onError: (err: any) => {
      setError(err?.response?.data?.error || t('An error occurred'));
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!templateId || !title) {
      setError(t('Template and title are required'));
      return;
    }
    mutation.mutate({
      template_id: templateId,
      title,
      description,
      category_id: categoryId || undefined,
    });
  };

  return (
    <Card className="mx-auto my-4" style={{ maxWidth: 500 }}>
      <Card.Body>
        <Card.Title>{t('Start Workflow')}</Card.Title>
        {error && <Alert variant="danger">{error}</Alert>}
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label htmlFor="workflow-template-select">{t('Workflow Template')}</Form.Label>
            <Form.Select id="workflow-template-select" value={templateId} onChange={e => setTemplateId(e.target.value)} required disabled={loadingTemplates}>
              <option value="">{t('Select a template')}</option>
              {templates && templates.map((tpl: any) => (
                <option key={tpl.wft_id} value={tpl.wft_id}>{tpl.wft_name_en}</option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>{t('Title')}</Form.Label>
            <Form.Control value={title} onChange={e => setTitle(e.target.value)} required minLength={5} />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>{t('Description')}</Form.Label>
            <Form.Control as="textarea" value={description} onChange={e => setDescription(e.target.value)} rows={2} />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>{t('common.category', 'Category')}</Form.Label>
            <Form.Select value={categoryId} onChange={e => setCategoryId(e.target.value)} disabled={loadingTopics}>
              <option value="">-- {t('common.none', 'None')} --</option>
              {topics.map((topic: any) => (
                <option key={topic.top_id} value={topic.top_id}>{topic.top_name}</option>
              ))}
            </Form.Select>
          </Form.Group>
          <Button type="submit" variant="primary" disabled={mutation.status === 'pending'}>
            {mutation.status === 'pending' ? <Spinner size="sm" animation="border" /> : t('Start Workflow')}
          </Button>
        </Form>
      </Card.Body>
    </Card>
  );
}
