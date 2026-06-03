import { Alert } from 'react-bootstrap'
import { useParams } from 'react-router-dom'
import WorkbenchPanel from '../../components/workflow/WorkbenchPanel'
import { t } from '../../lib/i18n'

export default function WorkflowWorkbenchPage() {
  const { instanceId } = useParams<{ instanceId: string }>()
  const parsedInstanceId = Number(instanceId)

  if (!parsedInstanceId || Number.isNaN(parsedInstanceId)) {
    return <Alert variant="danger">{t('workflow.invalidInstance', 'Invalid workflow instance.')}</Alert>
  }

  return (
    <div>
      <h2 className="mb-4">{t('workflow.workbench', 'Workflow Workbench')}</h2>
      <WorkbenchPanel instanceId={parsedInstanceId} />
    </div>
  )
}