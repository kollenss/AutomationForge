import { Handle, Position } from '@xyflow/react'
import './ComponentNode.css'

export default function ComponentNode({ data, selected }) {
  const inputs  = data.inputHandles  || []
  const outputs = data.outputHandles || []

  return (
    <div className={`cn-root ${selected ? 'cn-selected' : ''}`} style={{ '--node-color': data.color }}>
      <div className="cn-header">
        <span className="cn-icon">{data.icon}</span>
        <div className="cn-labels">
          <div className="cn-label">{data.label}</div>
          <div className="cn-subtitle">{data.subtitle}</div>
        </div>
      </div>

      {inputs.length > 0 && (
        <div className="cn-handles cn-inputs">
          {inputs.map(h => (
            <div key={h.key} className="cn-handle-row cn-handle-left">
              <Handle type="target" position={Position.Left} id={h.key} className="cn-handle" />
              <span className="cn-handle-label">{h.label}</span>
            </div>
          ))}
        </div>
      )}

      {outputs.length > 0 && (
        <div className="cn-handles cn-outputs">
          {outputs.map(h => (
            <div key={h.key} className="cn-handle-row cn-handle-right">
              <span className="cn-handle-label">{h.label}</span>
              <Handle type="source" position={Position.Right} id={h.key} className="cn-handle" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
