import { Modal, Button } from 'react-bootstrap'
import { t } from '../../lib/i18n'

interface ConfirmModalProps {
  show: boolean
  title: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  confirmText?: string
  cancelText?: string
  variant?: 'primary' | 'danger' | 'warning'
  isDeleting?: boolean
}

export default function ConfirmModal({
  show,
  title,
  message,
  onConfirm,
  onCancel,
  confirmText,
  cancelText,
  variant = 'primary',
  isDeleting = false,
}: ConfirmModalProps) {
  return (
    <Modal show={show} onHide={onCancel} centered>
      <Modal.Header closeButton>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>{message}</Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onCancel} disabled={isDeleting}>
          {cancelText || t('common.cancel', 'Cancel')}
        </Button>
        <Button variant={variant} onClick={onConfirm} disabled={isDeleting}>
          {confirmText || t('common.confirm', 'Confirm')}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}
