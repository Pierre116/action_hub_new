import { useEffect, useState } from 'react'
import { Button, Col, Form, Modal, Row } from 'react-bootstrap'
import api from '../../lib/api'
import { t } from '../../lib/i18n'

interface UserOption {
  usr_id: number
  usr_display_name: string
  usr_role: string
}

interface FieldDefinition {
  key: string
  label_en: string
  type: string
  required?: boolean
  options?: string[]
}

const HUMAN_NODE_TYPES = new Set(['Task', 'Approval'])

function buildFieldKey(label: string, index: number) {
  const normalized = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')

  return normalized || `field_${index + 1}`
}

export default function NodeEditor({ show, node, onClose, onSave, availableStepKeys = [] }: any) {
  const [users, setUsers] = useState<UserOption[]>([])
  const [name, setName] = useState('')
  const [legacyRole, setLegacyRole] = useState('')
  const [assignmentMode, setAssignmentMode] = useState('legacy_role')
  const [staticUserId, setStaticUserId] = useState('')
  const [teamRole, setTeamRole] = useState('Member')
  const [priorStepKey, setPriorStepKey] = useState('')
  const [fields, setFields] = useState<FieldDefinition[]>([])

  useEffect(() => {
    if (!show) {
      return
    }

    api.get('/api/users')
      .then((response) => setUsers(response.data.data || []))
      .catch(() => setUsers([]))
  }, [show])

  useEffect(() => {
    const nextName = node?.data?.name || node?.name || ''
    const nextRole = node?.data?.role || ''
    const assignment = node?.data?.assignment
    const rule = assignment?.rules?.[0]

    setName(nextName)
    setLegacyRole(nextRole)
    setFields((node?.data?.fields || []).map((field: any, index: number) => ({
      key: field.key || buildFieldKey(field.label_en || field.key || '', index),
      label_en: field.label_en || field.key || `Field ${index + 1}`,
      type: field.type || 'text',
      required: Boolean(field.required),
      options: Array.isArray(field.options) ? field.options : [],
    })))

    if (!rule) {
      setAssignmentMode(nextRole ? 'legacy_role' : 'workflow_creator')
      setStaticUserId('')
      setTeamRole(nextRole || 'Member')
      setPriorStepKey('')
      return
    }

    setAssignmentMode(rule.type || 'workflow_creator')
    setStaticUserId(rule.user_id ? String(rule.user_id) : '')
    setTeamRole(rule.role || nextRole || 'Member')
    setPriorStepKey(rule.step_key || '')
  }, [node])

  if (!node) {
    return null
  }

  const nodeType = node?.data?.type || node?.name
  const supportsHumanConfig = HUMAN_NODE_TYPES.has(nodeType)

  const updateField = (index: number, patch: Partial<FieldDefinition>) => {
    setFields((currentFields) => currentFields.map((field, fieldIndex) => {
      if (fieldIndex !== index) {
        return field
      }
      return { ...field, ...patch }
    }))
  }

  const addField = () => {
    setFields((currentFields) => [
      ...currentFields,
      {
        key: `field_${currentFields.length + 1}`,
        label_en: `Field ${currentFields.length + 1}`,
        type: 'text',
        required: false,
        options: [],
      },
    ])
  }

  const removeField = (index: number) => {
    setFields((currentFields) => currentFields.filter((_, fieldIndex) => fieldIndex !== index))
  }

  const handleSave = () => {
    let assignment
    let nextRole = legacyRole || null

    if (supportsHumanConfig) {
      if (assignmentMode === 'workflow_creator') {
        assignment = { rules: [{ type: 'workflow_creator' }], fallback: 'workflow_creator' }
        nextRole = null
      } else if (assignmentMode === 'static_user' && staticUserId) {
        assignment = {
          rules: [{ type: 'static_user', user_id: Number(staticUserId) }],
          fallback: 'workflow_creator',
        }
        nextRole = null
      } else if (assignmentMode === 'role_in_team' && teamRole) {
        assignment = {
          rules: [{ type: 'role_in_team', role: teamRole, team_source: 'action_team' }],
          fallback: 'workflow_creator',
        }
        nextRole = null
      } else if (assignmentMode === 'prior_step_actor' && priorStepKey) {
        assignment = {
          rules: [{ type: 'prior_step_actor', step_key: priorStepKey }],
          fallback: 'workflow_creator',
        }
        nextRole = null
      } else if (assignmentMode === 'round_robin' && teamRole) {
        assignment = {
          rules: [{ type: 'round_robin', role: teamRole, team_source: 'action_team' }],
          fallback: 'workflow_creator',
        }
        nextRole = null
      } else {
        assignment = undefined
      }
    }

    const normalizedFields = fields.map((field, index) => ({
      key: field.key || buildFieldKey(field.label_en, index),
      label_en: field.label_en || `Field ${index + 1}`,
      label_cn: field.label_en || `Field ${index + 1}`,
      type: field.type,
      required: Boolean(field.required),
      ...(field.type === 'dropdown' || field.type === 'checklist'
        ? { options: (field.options || []).filter(Boolean) }
        : {}),
    }))

    onSave({
      ...node,
      name,
      data: {
        ...(node.data || {}),
        name,
        role: nextRole,
        assignment,
        fields: supportsHumanConfig ? normalizedFields : (node.data?.fields || []),
      },
    })
  }

  return (
    <Modal show={show} onHide={onClose} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>{t('workflow.node.edit', 'Edit Node')}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form>
          <Form.Group className="mb-3">
            <Form.Label>{t('workflow.node.name', 'Name')}</Form.Label>
            <Form.Control type="text" value={name} onChange={(event) => setName(event.target.value)} />
          </Form.Group>

          {supportsHumanConfig && (
            <>
              <hr />
              <h6>{t('workflow.assignment', 'Assignment')}</h6>
              <Form.Group className="mb-3">
                <Form.Label>{t('workflow.assignmentMode', 'Assignment Mode')}</Form.Label>
                <Form.Select value={assignmentMode} onChange={(event) => setAssignmentMode(event.target.value)}>
                  <option value="legacy_role">{t('workflow.assignment.legacyRole', 'Legacy Role')}</option>
                  <option value="workflow_creator">{t('workflow.assignment.workflowCreator', 'Workflow Creator')}</option>
                  <option value="static_user">{t('workflow.assignment.staticUser', 'Predefined User')}</option>
                  <option value="role_in_team">{t('workflow.assignment.roleInTeam', 'Role In Action Team')}</option>
                  <option value="prior_step_actor">{t('workflow.assignment.priorStepActor', 'Prior Step Actor')}</option>
                  <option value="round_robin">{t('workflow.assignment.roundRobin', 'Round Robin')}</option>
                </Form.Select>
              </Form.Group>

              {assignmentMode === 'legacy_role' && (
                <Form.Group className="mb-3">
                  <Form.Label>{t('workflow.role', 'Role')}</Form.Label>
                  <Form.Select value={legacyRole} onChange={(event) => setLegacyRole(event.target.value)}>
                    <option value="">{t('workflow.noRole', 'No predefined role')}</option>
                    <option value="Member">Member</option>
                    {/* <option value="TeamLead">TeamLead</option> */}
                    <option value="Admin">Admin</option>
                  </Form.Select>
                </Form.Group>
              )}

              {assignmentMode === 'static_user' && (
                <Form.Group className="mb-3">
                  <Form.Label>{t('workflow.assignment.user', 'Predefined User')}</Form.Label>
                  <Form.Select value={staticUserId} onChange={(event) => setStaticUserId(event.target.value)}>
                    <option value="">{t('workflow.assignment.selectUser', 'Select a user')}</option>
                    {users.map((user) => (
                      <option key={user.usr_id} value={user.usr_id}>
                        {user.usr_display_name} ({user.usr_role})
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
              )}

              {(assignmentMode === 'role_in_team' || assignmentMode === 'round_robin') && (
                <Form.Group className="mb-3">
                  <Form.Label>{t('workflow.assignment.teamRole', 'Role In Action Team')}</Form.Label>
                  <Form.Select value={teamRole} onChange={(event) => setTeamRole(event.target.value)}>
                    <option value="Member">Member</option>
                    {/* <option value="TeamLead">TeamLead</option> */}
                    <option value="Admin">Admin</option>
                  </Form.Select>
                </Form.Group>
              )}

              {assignmentMode === 'prior_step_actor' && (
                <Form.Group className="mb-3">
                  <Form.Label>{t('workflow.assignment.priorStep', 'Prior Step')}</Form.Label>
                  <Form.Select value={priorStepKey} onChange={(event) => setPriorStepKey(event.target.value)}>
                    <option value="">{t('workflow.assignment.selectStep', 'Select a prior step')}</option>
                    {availableStepKeys.filter((stepKey: string) => stepKey !== node?.data?.key).map((stepKey: string) => (
                      <option key={stepKey} value={stepKey}>{stepKey}</option>
                    ))}
                  </Form.Select>
                </Form.Group>
              )}

              <hr />
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h6 className="mb-0">{t('workflow.forms', 'Step Form Fields')}</h6>
                <Button variant="outline-primary" size="sm" onClick={addField}>
                  {t('workflow.addField', 'Add Field')}
                </Button>
              </div>

              {fields.length === 0 && (
                <div className="text-muted small mb-3">{t('workflow.noFields', 'No form fields configured for this step.')}</div>
              )}

              {fields.map((field, index) => (
                <div key={`${field.key}-${index}`} className="border rounded p-3 mb-3">
                  <Row className="g-2">
                    <Col md={5}>
                      <Form.Group>
                        <Form.Label>{t('workflow.fieldLabel', 'Field Label')}</Form.Label>
                        <Form.Control
                          type="text"
                          value={field.label_en}
                          onChange={(event) => {
                            const label = event.target.value
                            updateField(index, {
                              label_en: label,
                              key: buildFieldKey(label, index),
                            })
                          }}
                        />
                      </Form.Group>
                    </Col>
                    <Col md={3}>
                      <Form.Group>
                        <Form.Label>{t('workflow.fieldType', 'Type')}</Form.Label>
                        <Form.Select value={field.type} onChange={(event) => updateField(index, { type: event.target.value, options: [] })}>
                          <option value="text">Text</option>
                          <option value="number">Number</option>
                          <option value="date">Date</option>
                          <option value="dropdown">Dropdown</option>
                          <option value="checkbox">Checkbox</option>
                          <option value="checklist">Checklist</option>
                        </Form.Select>
                      </Form.Group>
                    </Col>
                    <Col md={2}>
                      <Form.Group>
                        <Form.Label>{t('workflow.required', 'Required')}</Form.Label>
                        <Form.Check
                          type="switch"
                          checked={Boolean(field.required)}
                          onChange={(event) => updateField(index, { required: event.target.checked })}
                        />
                      </Form.Group>
                    </Col>
                    <Col md={2} className="d-flex align-items-end">
                      <Button variant="outline-danger" size="sm" onClick={() => removeField(index)}>
                        {t('common.delete', 'Delete')}
                      </Button>
                    </Col>
                  </Row>

                  {(field.type === 'dropdown' || field.type === 'checklist') && (
                    <Form.Group className="mt-3">
                      <Form.Label>{t('workflow.options', 'Options')}</Form.Label>
                      <Form.Control
                        type="text"
                        value={(field.options || []).join(', ')}
                        onChange={(event) => updateField(index, {
                          options: event.target.value.split(',').map((item) => item.trim()).filter(Boolean),
                        })}
                        placeholder={t('workflow.optionsPlaceholder', 'Option A, Option B, Option C')}
                      />
                    </Form.Group>
                  )}
                </div>
              ))}
            </>
          )}
        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onClose}>{t('common.cancel', 'Cancel')}</Button>
        <Button variant="primary" onClick={handleSave}>{t('common.save', 'Save')}</Button>
      </Modal.Footer>
    </Modal>
  )
}