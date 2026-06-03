import React from 'react';
import { Card, Badge, ListGroup, Row, Col } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { t } from '../../lib/i18n';
import api from '../../lib/api';

interface RecentDecision {
  mdc_id: number;
  mdc_title: string;
  mdc_status: string;
  mdc_created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  Published: 'primary',
  Expired: 'secondary',
};

const DecisionWidget: React.FC = () => {
  const navigate = useNavigate();

  // Fetch decision counts
  const { data: counts = {} } = useQuery<Record<string, number>>({
    queryKey: ['decisions', 'counts'],
    queryFn: async () => {
      const response = await api.get('/api/decisions/counts');
      return response.data;
    },
  });

  // Fetch recent decisions
  const { data: recentDecisions = [] } = useQuery<RecentDecision[]>({
    queryKey: ['decisions', 'recent'],
    queryFn: async () => {
      const response = await api.get('/api/decisions/', { params: { limit: 5 } });
      return response.data?.data || [];
    },
  });

  const totalCount = Object.values(counts).reduce((a, b) => a + b, 0) as number;

  return (
    <Card className="mb-4">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <span>{t('decisions.title', 'Decisions')}</span>
        <Badge bg="dark">{totalCount}</Badge>
      </Card.Header>
      <Card.Body className="p-0">
        {/* Status summary */}
        <Row className="g-0 px-3 py-2">
          {Object.entries(counts).map(([status, count]) => (
            <Col key={status} xs={4} className="text-center py-2">
              <div className="h5 mb-0">{count}</div>
              <small className="text-muted">{status}</small>
            </Col>
          ))}
          {Object.keys(counts).length === 0 && (
            <Col className="text-center py-2 text-muted">
              {t('decisions.no_decisions', 'No decisions')}
            </Col>
          )}
        </Row>
        
        <hr className="my-2" />
        
        {/* Recent decisions */}
        <ListGroup variant="flush">
          {recentDecisions.slice(0, 3).map((decision) => (
            <ListGroup.Item 
              key={decision.mdc_id} 
              action 
              onClick={() => navigate(`/decisions`)}
              className="d-flex justify-content-between align-items-center py-2"
            >
              <div className="text-truncate" style={{ maxWidth: '70%' }}>
                {decision.mdc_title}
              </div>
              <Badge bg={STATUS_COLORS[decision.mdc_status] || 'secondary'} className="ms-2">
                {decision.mdc_status}
              </Badge>
            </ListGroup.Item>
          ))}
          {recentDecisions.length === 0 && (
            <ListGroup.Item className="text-muted text-center py-3">
              {t('decisions.no_decisions', 'No decisions')}
            </ListGroup.Item>
          )}
        </ListGroup>
      </Card.Body>
      <Card.Footer className="text-center">
        <Card.Link 
          href="#" 
          onClick={(e) => { e.preventDefault(); navigate('/decisions'); }}
        >
          {t('common.all', 'View All')} →
        </Card.Link>
      </Card.Footer>
    </Card>
  );
};

export default DecisionWidget;
