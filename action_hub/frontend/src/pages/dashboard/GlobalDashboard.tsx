import { useState } from 'react';
import { Tabs, Tab, Row, Col, Spinner, Table, Badge, Card, Alert } from 'react-bootstrap';
import { useQuery } from '@tanstack/react-query';
import api from '../../lib/api';
import KpiCard from '../../components/shared/KpiCard';
import { t } from '../../lib/i18n';

function CategoryTab() {
  const { data: topicsData = [], isLoading } = useQuery({
    queryKey: ['dashboard', 'topics', 'summary'],
    queryFn: async () => {
      const response = await api.get('/api/dashboard/topics/summary');
      return response.data.data || [];
    },
  });

  if (isLoading) return <Spinner animation="border" />;

  return (
    <Card>
      <Card.Header>{t('dashboard.allTopicsSummary', 'All Business Themes Summary')}</Card.Header>
      <Card.Body>
        {topicsData.length === 0 ? (
          <Alert variant="light" className="mb-0">{t('dashboard.noTopics', 'No business themes found.')}</Alert>
        ) : (
          <Table responsive hover className="mb-0">
            <thead>
              <tr>
                <th>{t('dashboard.topic', 'Business Theme')}</th>
                <th>{t('dashboard.open', 'Open')}</th>
                <th>{t('dashboard.overdue', 'Overdue')}</th>
                <th>{t('dashboard.overdueRate', 'Overdue Rate')}</th>
                <th>{t('dashboard.done', 'Completed')}</th>
                <th>{t('dashboard.decisionCount', 'Decisions')}</th>
                <th>{t('dashboard.total', 'Total')}</th>
              </tr>
            </thead>
            <tbody>
              {topicsData.map((topic: any) => {
                const overduePct = topic.total ? ((topic.overdue / topic.total) * 100).toFixed(1) : '0.0';
                return (
                  <tr key={topic.top_id}>
                    <td>{topic.top_name}</td>
                    <td className="fw-semibold">{topic.open}</td>
                    <td className={topic.overdue > 0 ? 'fw-semibold text-danger' : 'fw-semibold'}>{topic.overdue}</td>
                    <td>{overduePct}%</td>
                    <td className="fw-semibold text-success">{topic.done}</td>
                    <td className="fw-semibold">{topic.decision_count ?? 0}</td>
                    <td className="fw-semibold">{topic.total}</td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card.Body>
    </Card>
  );
}

function TeamTab() {
  const { data: teamsData = [], isLoading } = useQuery({
    queryKey: ['dashboard', 'teams', 'detail-summary'],
    queryFn: async () => {
      const response = await api.get('/api/dashboard/teams/detail-summary');
      return response.data.data || [];
    },
  });

  if (isLoading) return <Spinner animation="border" />;

  return (
    <Card>
      <Card.Header>{t('dashboard.allTeamsSummary', 'All Teams Summary')}</Card.Header>
      <Card.Body>
        {teamsData.length === 0 ? (
          <Alert variant="light" className="mb-0">{t('dashboard.noTeams', 'No teams found.')}</Alert>
        ) : (
          <Table responsive hover className="mb-0">
            <thead>
              <tr>
                <th>{t('dashboard.team', 'Team')}</th>
                <th>{t('dashboard.teamLeader', 'Team Leader')}</th>
                <th>{t('dashboard.teamMembers', 'Team Members')}</th>
                <th>{t('dashboard.open', 'Open')}</th>
                <th>{t('dashboard.overdue', 'Overdue')}</th>
                <th>{t('dashboard.overdueRate', 'Overdue Rate')}</th>
                <th>{t('dashboard.done', 'Completed')}</th>
                <th>{t('dashboard.decisionCount', 'Decisions')}</th>
                <th>{t('dashboard.total', 'Total')}</th>
              </tr>
            </thead>
            <tbody>
              {teamsData.map((team: any) => {
                const overduePct = team.total ? ((team.overdue / team.total) * 100).toFixed(1) : '0.0';
                return (
                  <tr key={team.team_id}>
                    <td>{team.team_name}</td>
                    <td><Badge bg="info" className="fw-normal">{team.leader_name}</Badge></td>
                    <td>
                      {team.member_names && team.member_names.length > 0
                        ? team.member_names.map((name: string, idx: number) => (
                            <Badge key={idx} bg="secondary" className="me-1 mb-1 fw-normal">{name}</Badge>
                          ))
                        : <span className="text-muted">—</span>}
                    </td>
                    <td className="fw-semibold">{team.open}</td>
                    <td className={team.overdue > 0 ? 'fw-semibold text-danger' : 'fw-semibold'}>{team.overdue}</td>
                    <td>{overduePct}%</td>
                    <td className="fw-semibold text-success">{team.done}</td>
                    <td className="fw-semibold">{team.decision_count ?? 0}</td>
                    <td className="fw-semibold">{team.total}</td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card.Body>
    </Card>
  );
}

function MeetingSeriesTab() {
  const { data: seriesData = [], isLoading } = useQuery({
    queryKey: ['dashboard', 'meeting-series', 'summary'],
    queryFn: async () => {
      const response = await api.get('/api/meetings/series/summary');
      return response.data.data || [];
    },
  });

  if (isLoading) return <Spinner animation="border" />;

  return (
    <Card>
      <Card.Header>{t('dashboard.meetingSeriesSummary', 'Meeting Series Summary')}</Card.Header>
      <Card.Body>
        {seriesData.length === 0 ? (
          <Alert variant="light" className="mb-0">{t('dashboard.noMeetingSeries', 'No meeting series found.')}</Alert>
        ) : (
          <Table responsive hover className="mb-0">
            <thead>
              <tr>
                <th>{t('dashboard.series', 'Series')}</th>
                <th>{t('dashboard.open', 'Open')}</th>
                <th>{t('dashboard.overdue', 'Overdue')}</th>
                <th>{t('dashboard.overdueRate', 'Overdue Rate')}</th>
                <th>{t('dashboard.done', 'Completed')}</th>
                <th>{t('dashboard.decisionCount', 'Decision Count')}</th>
                <th>{t('dashboard.decisionRate', 'Decision Rate')}</th>
                <th>{t('dashboard.total', 'Total')}</th>
                <th>{t('dashboard.participants', 'Participants')}</th>
              </tr>
            </thead>
            <tbody>
              {seriesData.map((series: any) => {
                const overduePct = series.total_actions ? ((series.overdue_actions / series.total_actions) * 100).toFixed(1) : '0.0';
                const decisionPct = series.total_actions ? ((series.decision_count / series.total_actions) * 100).toFixed(1) : '0.0';
                return (
                  <tr key={series.series_id}>
                    <td>{series.series_title}</td>
                    <td className="fw-semibold">{series.open_actions}</td>
                    <td className={series.overdue_actions > 0 ? 'fw-semibold text-danger' : 'fw-semibold'}>{series.overdue_actions}</td>
                    <td>{overduePct}%</td>
                    <td className="fw-semibold text-success">{series.done_actions}</td>
                    <td className="fw-semibold">{series.decision_count}</td>
                    <td>{decisionPct}%</td>
                    <td className="fw-semibold">{series.total_actions}</td>
                    <td className="fw-semibold">{series.participant_count}</td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card.Body>
    </Card>
  );
}

export default function GlobalDashboard() {
  const [tab, setTab] = useState('category');
  return (
    <div>
      <h2 className="mb-4">{t('dashboard.global', 'Global Dashboard')}</h2>
      <Tabs
        activeKey={tab}
        onSelect={eventKey => {
          if (eventKey) setTab(eventKey);
        }}
        className="mb-3"
      >
        <Tab eventKey="category" title={t('dashboard.byCategory', 'By Category')}><CategoryTab /></Tab>
        <Tab eventKey="team" title={t('dashboard.byTeam', 'By Team')}><TeamTab /></Tab>
        <Tab eventKey="series" title={t('dashboard.byMeetingSeries', 'By Meeting Series')}><MeetingSeriesTab /></Tab>
      </Tabs>
    </div>
  );
}
