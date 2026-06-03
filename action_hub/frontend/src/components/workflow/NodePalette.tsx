import React from 'react'
import { t } from '../../lib/i18n'
import { NODE_TYPE_DEFINITIONS } from './WorkflowFlow'

export default function NodePalette() {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        gap: 10,
        marginBottom: 8,
      }}
    >
      {NODE_TYPE_DEFINITIONS.map((node) => (
        <div
          key={node.type}
          draggable
          onDragStart={e => {
            e.dataTransfer.setData('application/node-type', node.type)
            e.dataTransfer.setData('application/reactflow-step-type', node.type)
          }}
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 10,
            minHeight: 72,
            borderRadius: 12,
            background: '#ffffff',
            color: '#0f172a',
            fontWeight: 600,
            cursor: 'grab',
            boxShadow: '0 8px 20px rgba(15, 23, 42, 0.06)',
            userSelect: 'none',
            padding: '10px 12px',
            border: '1px solid rgba(148, 163, 184, 0.22)',
          }}
          title={`${t(`workflow.node.${node.type.toLowerCase()}`, node.label)} - ${node.description}`}
        >
          <span
            style={{
              width: 34,
              height: 34,
              borderRadius: 10,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: node.color,
              color: '#fff',
              fontSize: 18,
              flexShrink: 0,
            }}
          >
            {node.icon}
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, lineHeight: 1.2 }}>{t(`workflow.node.${node.type.toLowerCase()}`, node.label)}</div>
            <div style={{ fontSize: 11, lineHeight: 1.3, color: '#64748b', marginTop: 4, fontWeight: 400 }}>{node.description}</div>
          </div>
        </div>
      ))}
    </div>
  )
}